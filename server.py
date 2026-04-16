import os
import cv2
import argparse
import mediapipe as mp
import numpy as np
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
import json
import subprocess
import time
import threading
from queue import Queue

app = FastAPI()

# MediaPipe Tasks API
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.core import base_options

# Globals for state tracking
video_path = ""
landmarks_data = None 
fps = 0
total_frames = 0
analysis_progress = 0
current_step = 0 
step_desc = "Initializing system..."
best_frame_idx = -1
similar_frames = []
average_pose = None 
candidate_frames = []

MODEL_PATH = "pose_landmarker.task"
if os.path.exists(MODEL_PATH):
    with open(MODEL_PATH, "rb") as f:
        MODEL_BUFFER = f.read()
else:
    MODEL_BUFFER = None

def calculate_multi_point_score(current_lms, target_lms):
    if current_lms is None or target_lms is None: return 0
    
    # --- Custom weights: Head 40%, Hands 30%, Arms 20%, Others 10% ---
    weights = np.zeros(33)
    weights[0:11] = 0.40 / 11      # Head
    weights[15:23] = 0.30 / 8      # Hands (wrists + fingers)
    weights[[13, 14]] = 0.20 / 2   # Arm joints (elbows)
    
    others_idx = [11, 12] + list(range(23, 33))
    weights[others_idx] = 0.10 / len(others_idx) # Others (shoulders, torso, legs)
    
    mask = (current_lms[:, 3] > 0.5) & (target_lms[:, 3] > 0.5)
    if not np.any(mask): return 0
    
    # Euclidean distance
    dists = np.sqrt(np.sum((current_lms[mask, :2] - target_lms[mask, :2])**2, axis=1))
    
    # Dynamic scale factor (torso span)
    scale = np.linalg.norm(target_lms[11, :2] - target_lms[24, :2])
    if scale == 0: scale = 1.0
    
    # Gaussian similarity score
    scores = 100 * np.exp(-(dists**2) / (2 * (0.015 * scale)**2))
    
    return float(np.average(scores, weights=weights[mask]))

# Temporary storage for filtered standing frame indices
_standing_indices = []

def compute_robust_average_pose():
    global landmarks_data, average_pose, total_frames, current_step, step_desc, fps, _standing_indices
    current_step = 2
    step_desc = "Building digital human ideal pose baseline from frames..."
    if landmarks_data is None: return
    
    # 1. Select the first few frames (top 10 valid frames) to fit an estimated node position
    initial_frames = []
    for i in range(min(total_frames, int(fps * 10))): # Search within first 10 seconds
        if landmarks_data[i, 0, 3] > 0.5:
            initial_frames.append(landmarks_data[i])
        if len(initial_frames) >= 10: break
    
    if not initial_frames:
        valid_indices = np.where(landmarks_data[:, 0, 3] > 0.5)[0]
        if len(valid_indices) == 0: return
        initial_frames = [landmarks_data[valid_indices[0]]]
        
    initial_baseline = np.median(initial_frames, axis=0) # (33, 4)
    
    # 2. Iterate through all content to calculate deviations from the estimated baseline
    deviations = np.zeros(total_frames)
    for i in range(total_frames):
        lms = landmarks_data[i]
        if lms[0, 3] < 0.5: 
            deviations[i] = float('inf') # Nose invisible, max deviation
            continue
        
        # Only compare torso and limb offsets, ignore head micro-movements
        core_idx = [11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28]
        mask = (lms[core_idx, 3] > 0.5) & (initial_baseline[core_idx, 3] > 0.5)
        if not np.any(mask):
            deviations[i] = float('inf')
            continue
            
        dist = np.sqrt(np.sum((lms[core_idx][mask, :2] - initial_baseline[core_idx][mask, :2])**2, axis=1))
        deviations[i] = np.mean(dist)
        
    # 3. Filter out the top 50% deviations (e.g., waving, bowing, or active movement frames)
    valid_devs = deviations[deviations != float('inf')]
    if len(valid_devs) == 0: return
    
    threshold_50 = np.percentile(valid_devs, 50)
    standing_indices = np.where(deviations <= threshold_50)[0]
    
    # 4. Use the remaining 50% frames to find the median as the standard reference points
    if len(standing_indices) < 5: standing_indices = np.where(landmarks_data[:, 0, 3] > 0.5)[0]
    average_pose = np.median(landmarks_data[standing_indices], axis=0)
    
    _standing_indices = standing_indices
    print(f"Computed Ideal Pose from top 50% stable frames ({len(standing_indices)} frames).")

def compute_candidates():
    global landmarks_data, total_frames, fps, candidate_frames, current_step, step_desc, average_pose, _standing_indices
    current_step = 3
    step_desc = "Listing top 10 real frames closest to the ideal pose..."
    if landmarks_data is None or average_pose is None: return
    
    # 5. List 10 real frames that best match this standard baseline
    scores = np.zeros(total_frames)
    for i in _standing_indices: # Only search within filtered stable frames
        scores[i] = calculate_multi_point_score(landmarks_data[i], average_pose)
        
    candidates = []
    sorted_indices = np.argsort(scores)[::-1]
    
    for idx in sorted_indices:
        if scores[idx] == 0: break
        if len(candidates) >= 10: break
        # Prevent 10 candidate frames from being clustered in the same time period (min 1s gap)
        if any(abs(idx - c['idx']) < fps * 1.0 for c in candidates): continue
        
        candidates.append({
            "idx": int(idx),
            "timestamp": float(idx / fps),
            "score": float(scores[idx])
        })
        
    candidate_frames = candidates

def update_all_similarities(ref_lms=None, threshold=92.0, is_initial=False):
    global landmarks_data, average_pose, similar_frames, total_frames, fps, current_step, step_desc
    
    if is_initial:
        current_step = 4
        step_desc = "Completing high-precision alignment mapping..."
        
    target = ref_lms if ref_lms is not None else average_pose
    if target is None or landmarks_data is None: return 0

    # --- Prepare weight vector ---
    weights = np.zeros(33)
    weights[0:11] = 0.40 / 11      # Head
    weights[15:23] = 0.30 / 8      # Hands
    weights[[13, 14]] = 0.20 / 2   # Arm joints
    others_idx = [11, 12] + list(range(23, 33))
    weights[others_idx] = 0.10 / len(others_idx)

    # --- Vectorized score calculation ---
    # landmarks_data: (N, 33, 4), target: (33, 4)
    # 1. Mask calculation (visibility > 0.5)
    mask = (landmarks_data[:, :, 3] > 0.5) & (target[None, :, 3] > 0.5) # (N, 33)
    
    # 2. Distance calculation
    diff = landmarks_data[:, :, :2] - target[None, :, :2] # (N, 33, 2)
    dists_sq = np.sum(diff**2, axis=2) # (N, 33)
    
    # 3. Dynamic scale
    scale = np.linalg.norm(target[11, :2] - target[24, :2])
    if scale == 0: scale = 1.0
    
    # 4. Gaussian similarity
    scores = 100 * np.exp(-dists_sq / (2 * (0.015 * scale)**2)) # (N, 33)
    
    # 5. Weighted average
    weighted_scores = scores * weights[None, :] * mask
    sum_weights = np.sum(weights[None, :] * mask, axis=1)
    
    final_scores = np.zeros(total_frames)
    valid_idx = sum_weights > 0
    final_scores[valid_idx] = np.sum(weighted_scores[valid_idx], axis=1) / sum_weights[valid_idx]
    
    # --- Extract matched frames ---
    matches_idx = np.where(final_scores >= threshold)[0]
    similar_frames = [
        {"frame_index": int(i), "timestamp": float(i / fps), "score": float(final_scores[i])}
        for i in matches_idx if landmarks_data[i, 0, 3] > 0.5
    ]
    similar_frames = sorted(similar_frames, key=lambda x: x['frame_index'])
    
    if is_initial:
        current_step = 5
        step_desc = "Analysis Ready"
        
    return len(similar_frames)

def worker_thread(task_queue, result_list, worker_id):
    options = vision.PoseLandmarkerOptions(
        base_options=base_options.BaseOptions(model_asset_buffer=MODEL_BUFFER, delegate=base_options.BaseOptions.Delegate.GPU),
        running_mode=vision.RunningMode.IMAGE
    )
    try:
        with vision.PoseLandmarker.create_from_options(options) as landmarker:
            while True:
                batch = task_queue.get()
                if batch is None: break
                for idx, frame_rgb in batch:
                    try:
                        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
                        res = landmarker.detect(mp_img)
                        if res and res.pose_landmarks and len(res.pose_landmarks) > 0:
                            result_list[idx] = np.array([[lm.x, lm.y, lm.z, lm.visibility] for lm in res.pose_landmarks[0]], dtype=np.float32)
                    except: pass
                task_queue.task_done()
    except Exception as e: print(f"Worker Error: {e}")

def analyze_video(path):
    global landmarks_data, fps, total_frames, analysis_progress, similar_frames, best_frame_idx, current_step, step_desc
    try:
        cap = cv2.VideoCapture(path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if fps <= 0: fps = 30.0 # Fallback
        cap.release()

        cache_path = path + ".pose.npy"
        if os.path.exists(cache_path):
            current_step = 1
            step_desc = "Loading cached pose data..."
            landmarks_data = np.load(cache_path)
            # Validate cache length
            if len(landmarks_data) != total_frames:
                print("Cache length mismatch. Re-analyzing...")
                os.remove(cache_path)
                return analyze_video(path)
            analysis_progress = 100
        else:
            current_step = 1
            step_desc = "Extracting features (Hardware Accelerated)..."
            landmarks_raw = [None] * total_frames
            num_workers = 8
            task_queue = Queue(maxsize=16)
            threads = [threading.Thread(target=worker_thread, args=(task_queue, landmarks_raw, i)) for i in range(num_workers)]
            for t in threads: t.start()
            cap = cv2.VideoCapture(path)
            for i in range(0, total_frames, 32):
                batch = []
                for j in range(i, min(i + 32, total_frames)):
                    ret, frame = cap.read()
                    if not ret: break
                    batch.append((j, cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
                if batch: task_queue.put(batch)
                analysis_progress = int(i / total_frames * 100)
            cap.release()
            for _ in range(num_workers): task_queue.put(None)
            for t in threads: t.join()
            landmarks_data = np.zeros((total_frames, 33, 4), dtype=np.float32)
            for i, data in enumerate(landmarks_raw):
                if data is not None: landmarks_data[i] = data
            np.save(cache_path, landmarks_data)
            analysis_progress = 100

        compute_robust_average_pose()
        compute_candidates()
        update_all_similarities(is_initial=True)
        best_frame_idx = candidate_frames[0]['idx'] if candidate_frames else -1
    except Exception as e:
        step_desc = f"Analysis Failed: {str(e)}"
        current_step = 0

@app.get("/")
async def get_index(): return FileResponse("static/index.html")

@app.get("/video")
async def get_video(): return FileResponse(video_path)

@app.get("/api/status")
async def get_status():
    return {
        "step": current_step, "step_desc": step_desc, "progress": analysis_progress, 
        "total_frames": total_frames, "fps": fps, # Must return high-precision FPS
        "best_frame_idx": int(best_frame_idx), "similar_frames": similar_frames,
        "average_pose": average_pose.tolist() if average_pose is not None else None,
        "candidates": candidate_frames
    }

@app.get("/api/frame_data/{idx}")
async def get_frame_data(idx: int):
    if landmarks_data is None or idx < 0 or idx >= len(landmarks_data): 
        return {"landmarks": None, "score": 0}
    
    current_lms = landmarks_data[idx]
    score = 0
    if average_pose is not None:
        score = calculate_multi_point_score(current_lms, average_pose)
        
    return {
        "landmarks": current_lms.tolist(),
        "score": float(score)
    }

@app.get("/api/frame_image/{idx}")
async def get_frame_image(idx: int):
    """Diagnostic tool: Get the actual video frame read by the backend"""
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    ret, frame = cap.read()
    cap.release()
    if not ret: raise HTTPException(status_code=404)
    _, img_encoded = cv2.imencode('.jpg', frame)
    return Response(content=img_encoded.tobytes(), media_type="image/jpeg")

@app.post("/api/re-sync")
async def re_sync(request: Request):
    data = await request.json()
    idx = data.get('frame_index')
    threshold = float(data.get('threshold', 92.0))
    global average_pose, best_frame_idx
    average_pose = landmarks_data[idx]
    best_frame_idx = idx
    count = update_all_similarities(average_pose, threshold)
    return {"matched_count": count, "similar_frames": similar_frames, "average_pose": average_pose.tolist()}


@app.post("/api/clip")
async def clip_video(request: Request):
    data = await request.json()
    output_path = os.path.join("static/clips", data['name'] + ".mp4")
    cmd = ["ffmpeg", "-y", "-ss", str(data['start_time']), "-t", str(data['duration']), "-i", video_path, "-c:v", "libx264", "-c:a", "aac", "-preset", "ultrafast", output_path]
    subprocess.run(cmd, capture_output=True)
    return {"download_url": f"/api/download/{data['name']}.mp4"}

@app.get("/api/download/{filename}")
async def download_clip(filename: str):
    return FileResponse(os.path.join("static/clips", filename), filename=filename)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    video_path = args.video
    os.makedirs("static/clips", exist_ok=True)
    threading.Thread(target=analyze_video, args=(video_path,), daemon=True).start()
    app.mount("/static", StaticFiles(directory="static"), name="static")
    uvicorn.run(app, host="0.0.0.0", port=args.port)
