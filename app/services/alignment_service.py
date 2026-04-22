import numpy as np
import cv2
import os
import asyncio
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from app.core.config import settings

class AlignmentService:
    def __init__(self):
        # Initialize MediaPipe Tasks Pose Landmarker for backend
        base_options = python.BaseOptions(model_asset_path=settings.MODEL_PATH)
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
            output_segmentation_masks=False
        )
        self.pose_landmarker = vision.PoseLandmarker.create_from_options(options)

    def get_landmarks(self, frame):
        """Extract landmarks from a single frame using MediaPipe Tasks API."""
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        results = self.pose_landmarker.detect(mp_image)
        
        if results.pose_landmarks:
            return np.array([[lm.x, lm.y] for lm in results.pose_landmarks[0]])
        return None

    def mls_warp_image(self, image, src_pts, dst_pts, alpha=1.0, grid_size=20, draw_grid=False):
        """
        Moving Least Squares (MLS) Affine Image Warping.
        Vectorized implementation for high performance.
        """
        height, width = image.shape[:2]
        
        # 1. Create coarse grid for calculation (faster than pixel-wise)
        grid_y, grid_x = np.mgrid[0:height:grid_size, 0:width:grid_size]
        grid_shape = grid_x.shape
        v = np.column_stack((grid_x.ravel(), grid_y.ravel())).astype(np.float32) # (V, 2)
        
        # 2. Setup points (q: target/dst, p: source/src for inverse mapping)
        q = dst_pts.astype(np.float32) # (N, 2)
        p = src_pts.astype(np.float32) # (N, 2)
        
        # 3. Compute weights w_i = 1 / |q_i - v|^(2*alpha)
        diff = v[:, np.newaxis, :] - q[np.newaxis, :, :] # (V, N, 2)
        dist_sq = np.sum(diff**2, axis=2) # (V, N)
        dist_sq = np.clip(dist_sq, 1e-6, None)
        w = 1.0 / (dist_sq ** alpha) # (V, N)
        
        sum_w = np.sum(w, axis=1, keepdims=True) # (V, 1)
        w_norm = w / sum_w # (V, N)
        
        # 4. Centroids
        q_star = np.sum(w_norm[:, :, np.newaxis] * q[np.newaxis, :, :], axis=1) # (V, 2)
        p_star = np.sum(w_norm[:, :, np.newaxis] * p[np.newaxis, :, :], axis=1) # (V, 2)
        
        # 5. Shifted points
        q_hat = q[np.newaxis, :, :] - q_star[:, np.newaxis, :] # (V, N, 2)
        p_hat = p[np.newaxis, :, :] - p_star[:, np.newaxis, :] # (V, N, 2)
        
        # 6. Compute Affine transformation matrix M for each grid point
        A = np.einsum('vn,vni,vnj->vij', w, q_hat, q_hat) # (V, 2, 2)
        B = np.einsum('vn,vni,vnj->vij', w, q_hat, p_hat) # (V, 2, 2)
        
        # Fast 2x2 inversion
        det_A = A[:, 0, 0] * A[:, 1, 1] - A[:, 0, 1] * A[:, 1, 0]
        det_A = np.where(np.abs(det_A) < 1e-8, 1e-8, det_A)
        
        inv_A = np.empty_like(A)
        inv_A[:, 0, 0] = A[:, 1, 1] / det_A
        inv_A[:, 1, 1] = A[:, 0, 0] / det_A
        inv_A[:, 0, 1] = -A[:, 0, 1] / det_A
        inv_A[:, 1, 0] = -A[:, 1, 0] / det_A
        
        M = np.einsum('vij,vjk->vik', inv_A, B) # (V, 2, 2)
        
        # 7. Map points: u = (v - q_star) M + p_star
        u = np.einsum('vi,vij->vj', v - q_star, M) + p_star # (V, 2)
        
        # NEW: Knee-Down & Background Protection
        # Calculate displacement: how much each pixel wants to move
        displacement = u - v # (V, 2)
        
        # Identify knee level if landmarks are provided (indices 25, 26 are knees)
        # We use dst_pts because v is in the target coordinate space
        if len(dst_pts) > 26:
            knee_y = np.mean(dst_pts[25:27, 1])
            # Create a smooth but rapid falloff at the knee line
            # Pixels below knee_y will have displacement scaled to 0
            falloff_width = 40 # px
            mask = 1.0 - (1.0 / (1.0 + np.exp(-(v[:, 1] - (knee_y - 20)) / 10)))
            # Above knee (~0 displacement), we want mask=1. Below knee, mask=0.
            # Wait, the logistic function above: if y > knee_y, exp is positive, mask goes to 1-1=0. Correct.
            displacement *= mask[:, np.newaxis]

        # Apply displacement to get final mapping
        u_final = v + displacement

        # 8. Remap image
        map_x = u_final[:, 0].reshape(grid_shape)
        map_y = u_final[:, 1].reshape(grid_shape)
        
        map_x_full = cv2.resize(map_x, (width, height), interpolation=cv2.INTER_LINEAR)
        map_y_full = cv2.resize(map_y, (width, height), interpolation=cv2.INTER_LINEAR)
        
        warped = cv2.remap(image, map_x_full, map_y_full, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        
        if draw_grid:
            grid_img = np.zeros((height, width, 3), dtype=np.uint8)
            interval = 40
            for x in range(0, width, interval):
                cv2.line(grid_img, (x, 0), (x, height), (0, 255, 255), 1)
            for y in range(0, height, interval):
                cv2.line(grid_img, (0, y), (width, y), (0, 255, 255), 1)
            
            warped_grid = cv2.remap(grid_img, map_x_full, map_y_full, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
            mask = np.any(warped_grid > 0, axis=2)
            warped[mask] = cv2.addWeighted(warped[mask], 0.5, warped_grid[mask], 0.5, 0)
            
        return warped

    async def process_mls(self, video_id, source_path, output_path, params):
        """Process a video clip with Symmetrical MLS spatial alignment."""
        from app.db.storage import storage
        storage.update_video(video_id, {"refine_status": "starting", "refine_progress": 0})
        
        video = storage.get_video(video_id)
        if not video: return False

        cap = cv2.VideoCapture(source_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        if total_frames < 2: return False
        frames = []
        while True:
            ret, frame = cap.read()
            if not ret: break
            frames.append(frame)
        cap.release()
        
        # 1. Get Landmarks
        target_lms = None # Global Keyframe or Manual
        if params.get('manual_target_lms'):
            target_lms = np.array(params['manual_target_lms'])[:, :2]
            print("Using User-Provided manual landmarks for full clip processing")
        elif video.get("keyframes") and len(video["keyframes"]) > 0:
            try:
                pose_data = np.load(video["pose_cache"])
                target_lms = pose_data[video["keyframes"][0]["frame"]][:, :2]
            except: pass
        if target_lms is None: target_lms = self.get_landmarks(frames[0])
            
        first_lms = self.get_landmarks(frames[0])
        last_lms = self.get_landmarks(frames[-1])
        
        if first_lms is None or last_lms is None:
            storage.update_video(video_id, {"refine_status": "idle", "refine_progress": 100})
            return False

        # 2. Parameters
        strategy = params.get('strategy', 'progressive')
        fade_out_frames = int(params.get('fade_out_frames', 15))
        fade_in_frames = int(params.get('fade_in_frames', 15)) # Default to same as fade out
        alpha = float(params.get('alpha', 1.0))
        
        # 3. Setup Warp Points with Foot Anchors
        def get_anchored_dst(src, target):
            dst = target.copy() * [width, height]
            s_px = src.copy() * [width, height]
            # Lock everything from knees (25) down to feet (32)
            if len(dst) > 25: dst[25:] = s_px[25:] 
            return s_px, dst

        first_src_px, first_dst_px = get_anchored_dst(first_lms, target_lms)
        last_src_px, last_dst_px = get_anchored_dst(last_lms, target_lms)

        output_frames = []
        for i, frame in enumerate(frames):
            # Yield control back to the event loop to allow progress polling requests to be handled
            await asyncio.sleep(0)

            storage.update_video(video_id, {
                "refine_status": "warping",
                "refine_progress": int((i + 1) / total_frames * 90)
            })


            # Fade In (Start of video)
            if i < fade_in_frames:
                weight = 1.0 - (i / fade_in_frames)
                curr_dst = first_src_px * (1 - weight) + first_dst_px * weight
                warped = self.mls_warp_image(frame, first_src_px, curr_dst, alpha=alpha)
                output_frames.append(warped)
            
            # Fade Out (End of video)
            elif i >= (total_frames - fade_out_frames):
                dist_from_end = total_frames - 1 - i
                # weight is 1.0 at last frame, 0.0 at start of window
                weight = 1.0 - (dist_from_end / (fade_out_frames - 1))
                curr_dst = last_src_px * (1 - weight) + last_dst_px * weight
                warped = self.mls_warp_image(frame, last_src_px, curr_dst, alpha=alpha)
                output_frames.append(warped)
            
            # Static Middle
            else:
                output_frames.append(frame)

        # 4. Write Output
        temp_out = output_path + ".tmp.mp4"
        out = cv2.VideoWriter(temp_out, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))
        for f in output_frames: out.write(f)
        out.release()
        
        import subprocess
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-i", temp_out, "-i", source_path, 
            "-map", "0:v", "-map", "1:a?", 
            "-c:v", "libx264", 
            "-crf", "0",            # Lossless
            "-preset", "veryslow", 
            "-g", "1",              # All-Intra (Keyframes only)
            "-bf", "0",             # No B-frames
            "-c:a", "copy", 
            output_path
        ]
        subprocess.run(ffmpeg_cmd, capture_output=True)
        if os.path.exists(temp_out): os.remove(temp_out)
        storage.update_video(video_id, {"refine_status": "idle", "refine_progress": 100})
        return True

    async def process_rife(self, video_id, source_path, output_path, params):
        import shutil
        shutil.copy2(source_path, output_path)
        return True

alignment_service = AlignmentService()
