import os
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.core import base_options
import threading
from queue import Queue
from app.core.config import settings
from app.db.storage import storage

class PoseService:
    def __init__(self):
        self.active_tasks = {} 
        self.model_buffer = None
        if os.path.exists(settings.MODEL_PATH):
            with open(settings.MODEL_PATH, "rb") as f:
                self.model_buffer = f.read()

    def calculate_multi_point_score(self, current_lms, target_lms):
        if current_lms is None or target_lms is None: return 0
        weights = np.zeros(33)
        weights[0:11] = 0.40 / 11      # Head
        weights[15:23] = 0.30 / 8      # Hands
        weights[[13, 14]] = 0.20 / 2   # Arms
        others_idx = [11, 12] + list(range(23, 33))
        weights[others_idx] = 0.10 / len(others_idx)
        
        mask = (current_lms[:, 3] > 0.5) & (target_lms[:, 3] > 0.5)
        if not np.any(mask): return 0
        dists = np.sqrt(np.sum((current_lms[mask, :2] - target_lms[mask, :2])**2, axis=1))
        scale = np.linalg.norm(target_lms[11, :2] - target_lms[24, :2])
        if scale == 0: scale = 1.0
        scores = 100 * np.exp(-(dists**2) / (2 * (0.015 * scale)**2))
        return float(np.average(scores, weights=weights[mask]))

    def get_analysis_results(self, video_id, ref_lms=None, threshold=92.0):
        video = storage.get_video(video_id)
        if not video or "pose_cache" not in video:
            return None
            
        landmarks_data = np.load(video["pose_cache"])
        total_frames = len(landmarks_data)
        fps = video.get("fps", 30.0)

        # 1. Try to get cached candidates first
        if video.get("analysis_cache") and ref_lms is None:
            cache = video["analysis_cache"]
            return {
                "average_pose": cache["average_pose"],
                "candidates": cache["candidates"],
                "similar_frames": cache.get("similar_frames", self.find_similar_frames(landmarks_data, np.array(cache["average_pose"]), threshold, fps))
            }

        # 2. Compute if not cached
        if ref_lms is None:
            ref_lms = self.compute_robust_average_pose(landmarks_data, fps)
        
        candidates = self.compute_candidates(landmarks_data, ref_lms, fps)
        similar_frames = self.find_similar_frames(landmarks_data, ref_lms, threshold, fps)

        # Save to video metadata for next time
        storage.update_video(video_id, {
            "analysis_cache": {
                "average_pose": ref_lms.tolist(),
                "candidates": candidates,
                "similar_frames": similar_frames
            }
        })
        
        return {
            "average_pose": ref_lms.tolist(),
            "candidates": candidates,
            "similar_frames": similar_frames
        }

    def compute_robust_average_pose(self, landmarks_data, fps):
        total_frames = len(landmarks_data)
        # Search within first 10 seconds for initial baseline
        initial_frames = []
        for i in range(min(total_frames, int(fps * 10))):
            if landmarks_data[i, 0, 3] > 0.5:
                initial_frames.append(landmarks_data[i])
            if len(initial_frames) >= 10: break
        
        if not initial_frames: return landmarks_data[0]
        initial_baseline = np.median(initial_frames, axis=0)
        
        # 1. Calculate MAX deviation per frame (关注单点最大偏差)
        max_deviations = np.full(total_frames, float('inf'))
        valid_indices = []

        for i in range(total_frames):
            lms = landmarks_data[i]
            if lms[0, 3] < 0.5: continue
            
            # Calculate distance for all 33 points
            # Only compare points visible in both frame and baseline
            mask = (lms[:, 3] > 0.5) & (initial_baseline[:, 3] > 0.5)
            if not np.any(mask): continue
            
            dists = np.sqrt(np.sum((lms[mask, :2] - initial_baseline[mask, :2])**2, axis=1))
            max_deviations[i] = np.max(dists)
            valid_indices.append(i)
            
        valid_indices = np.array(valid_indices)
        valid_max_devs = max_deviations[valid_indices]
        
        if len(valid_max_devs) == 0: return initial_baseline

        # 2. Stage 1: Discard top 30% frames with largest MAX deviation
        thresh_70 = np.percentile(valid_max_devs, 70)
        stage1_indices = valid_indices[max_deviations[valid_indices] <= thresh_70]
        
        if len(stage1_indices) == 0: return initial_baseline

        # 3. Stage 2: From remaining 70%, filter the most stable 50%
        remaining_devs = max_deviations[stage1_indices]
        thresh_50 = np.percentile(remaining_devs, 50)
        final_indices = stage1_indices[max_deviations[stage1_indices] <= thresh_50]
        
        if len(final_indices) < 5: final_indices = stage1_indices
        
        # 4. Synthesize the final average pose using median of best frames
        return np.median(landmarks_data[final_indices], axis=0)

    def compute_candidates(self, landmarks_data, average_pose, fps):
        total_frames = len(landmarks_data)
        scores = np.zeros(total_frames)
        for i in range(total_frames):
            if landmarks_data[i, 0, 3] > 0.5:
                scores[i] = self.calculate_multi_point_score(landmarks_data[i], average_pose)
                
        candidates = []
        sorted_indices = np.argsort(scores)[::-1]
        for idx in sorted_indices:
            if scores[idx] == 0 or len(candidates) >= 20: break
            if any(abs(idx - c['idx']) < fps * 1.0 for c in candidates): continue
            candidates.append({"idx": int(idx), "timestamp": float(idx / fps), "score": float(scores[idx])})
        return candidates

    def find_similar_frames(self, landmarks_data, target, threshold, fps):
        total_frames = len(landmarks_data)
        weights = np.zeros(33)
        weights[0:11] = 0.40 / 11
        weights[15:23] = 0.30 / 8
        weights[[13, 14]] = 0.20 / 2
        others_idx = [11, 12] + list(range(23, 33))
        weights[others_idx] = 0.10 / len(others_idx)

        mask = (landmarks_data[:, :, 3] > 0.5) & (target[None, :, 3] > 0.5)
        diff = landmarks_data[:, :, :2] - target[None, :, :2]
        dists_sq = np.sum(diff**2, axis=2)
        scale = np.linalg.norm(target[11, :2] - target[24, :2]) or 1.0
        scores = 100 * np.exp(-dists_sq / (2 * (0.015 * scale)**2))
        
        weighted_scores = scores * weights[None, :] * mask
        sum_weights = np.sum(weights[None, :] * mask, axis=1)
        
        final_scores = np.zeros(total_frames)
        valid_idx = sum_weights > 0
        final_scores[valid_idx] = np.sum(weighted_scores[valid_idx], axis=1) / sum_weights[valid_idx]
        
        matches_idx = np.where(final_scores >= threshold)[0]
        return [
            {"frame_index": int(i), "timestamp": float(i / fps), "score": float(final_scores[i])}
            for i in matches_idx if landmarks_data[i, 0, 3] > 0.5
        ]

    def _worker_thread(self, task_queue, result_list):
        options = vision.PoseLandmarkerOptions(
            base_options=base_options.BaseOptions(model_asset_buffer=self.model_buffer, delegate=base_options.BaseOptions.Delegate.GPU),
            running_mode=vision.RunningMode.IMAGE,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
            # Force model complexity to 1 to match frontend
            output_segmentation_masks=False
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
        except Exception as e:
            print(f"Worker Error: {e}")
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
        except Exception as e:
            print(f"Worker Error: {e}")

    def analyze_video_task(self, video_id, video_path):
        try:
            video = storage.get_video(video_id)
            project_dir = video.get('project_dir', settings.UPLOAD_DIR)
            storage.update_video(video_id, {"status": "analyzing", "progress": 0})
            
            # Use OpenCV with correct orientation handling if possible
            cap = cv2.VideoCapture(video_path)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if fps <= 0: fps = 30.0
            
            print(f"Analyzing video: {width}x{height} @ {fps}fps")

            cache_path = os.path.join(project_dir, "pose_data.npy")
            if os.path.exists(cache_path):
                landmarks_data = np.load(cache_path)
                if len(landmarks_data) == total_frames:
                    storage.update_video(video_id, {
                        "status": "completed",
                        "progress": 100,
                        "fps": fps,
                        "total_frames": total_frames,
                        "pose_cache": cache_path
                    })
                    return
                else:
                    os.remove(cache_path)

            landmarks_raw = [None] * total_frames
            num_workers = 8
            task_queue = Queue(maxsize=16)
            threads = [threading.Thread(target=self._worker_thread, args=(task_queue, landmarks_raw)) for _ in range(num_workers)]
            for t in threads: t.start()

            cap = cv2.VideoCapture(video_path)
            for i in range(0, total_frames, 32):
                batch = []
                for j in range(i, min(i + 32, total_frames)):
                    ret, frame = cap.read()
                    if not ret: break
                    batch.append((j, cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
                if batch:
                    task_queue.put(batch)
                
                progress = int(i / total_frames * 100)
                storage.update_video(video_id, {"progress": progress})
            
            cap.release()
            for _ in range(num_workers): task_queue.put(None)
            for t in threads: t.join()

            landmarks_data = np.zeros((total_frames, 33, 4), dtype=np.float32)
            for i, data in enumerate(landmarks_raw):
                if data is not None: landmarks_data[i] = data
            
            # 3. Save to temporary name first, then rename
            # np.save adds .npy if it's not present. 
            # If we pass "path/to/file.tmp", it saves as "path/to/file.tmp.npy"
            tmp_base = cache_path.replace(".npy", "") + ".tmp"
            np.save(tmp_base, landmarks_data)
            os.rename(tmp_base + ".npy", cache_path)
            
            storage.update_video(video_id, {
                "status": "completed",
                "progress": 100,
                "fps": float(fps),
                "total_frames": int(total_frames),
                "pose_cache": cache_path
            })
        except Exception as e:
            import traceback
            print(f"Analysis Error: {traceback.format_exc()}")
            storage.update_video(video_id, {"status": "failed", "error": str(e)})

    def start_analysis(self, video_id):
        video = storage.get_video(video_id)
        if not video: return False
        
        thread = threading.Thread(target=self.analyze_video_task, args=(video_id, video['path']))
        thread.start()
        return True

pose_service = PoseService()
