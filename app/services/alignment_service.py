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
        self.pose_landmarker = None
        self.holistic_landmarker = None
        self._init_pose()

    def _init_pose(self, enable_segmentation=False):
        # Re-initialize if segmentation setting changed
        if self.pose_landmarker and getattr(self, '_seg_enabled', False) == enable_segmentation:
            return
            
        base_options = python.BaseOptions(model_asset_path=settings.MODEL_PATH)
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
            output_segmentation_masks=enable_segmentation
        )
        self.pose_landmarker = vision.PoseLandmarker.create_from_options(options)
        self._seg_enabled = enable_segmentation

    def get_landmarks(self, frame):
        """Extract landmarks from a single frame using MediaPipe Tasks API (33 pts)."""
        self._init_pose(enable_segmentation=False)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        results = self.pose_landmarker.detect(mp_image)
        
        if results.pose_landmarks:
            # Return x, y, z, visibility (4 values)
            return np.array([[lm.x, lm.y, lm.z, getattr(lm, 'visibility', 1.0)] for lm in results.pose_landmarks[0]])
        return None

    def get_contour_landmarks(self, frame, num_points=100):
        """Extract 33 pose landmarks + 100 silhouette contour points."""
        self._init_pose(enable_segmentation=True)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        results = self.pose_landmarker.detect(mp_image)
        
        if not results.pose_landmarks or not results.segmentation_masks:
            return self.get_landmarks(frame) # Fallback
            
        # Pose landmarks with 4 values
        lms = np.array([[lm.x, lm.y, lm.z, getattr(lm, 'visibility', 1.0)] for lm in results.pose_landmarks[0]])
        # Binary mask
        mask = results.segmentation_masks[0].numpy_view()
        h, w = mask.shape[:2]
        mask = (mask.reshape(h, w) > 0.5).astype(np.uint8) * 255
        
        # Torso centroid for radial sampling
        center_x = (lms[11,0] + lms[12,0] + lms[23,0] + lms[24,0]) / 4
        center_y = (lms[11,1] + lms[12,1] + lms[23,1] + lms[24,1]) / 4
        
        cx, cy = center_x * w, center_y * h
        contour_pts = []
        
        for angle in np.linspace(0, 2*np.pi, num_points, endpoint=False):
            dx, dy = np.cos(angle), np.sin(angle)
            max_dist = max(w, h)
            hit_pt = [center_x, center_y, 0, 1.0] # [x, y, z, vis]
            
            for d in range(int(max_dist), 0, -3):
                tx, ty = int(cx + dx * d), int(cy + dy * d)
                if 0 <= tx < w and 0 <= ty < h:
                    if mask[ty, tx] > 0:
                        hit_pt = [tx / w, ty / h, 0, 1.0]
                        break
            contour_pts.append(hit_pt)
            
        return np.concatenate([lms, np.array(contour_pts)])

    def _init_holistic(self):
        if self.holistic_landmarker: return
        holistic_path = os.path.join(os.path.dirname(settings.MODEL_PATH), "holistic_landmarker.task")
        base_options = python.BaseOptions(model_asset_path=holistic_path)
        options = vision.HolisticLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            min_face_detection_confidence=0.5,
            min_face_landmarks_confidence=0.5,
            min_pose_detection_confidence=0.5,
            min_pose_landmarks_confidence=0.5,
            min_hand_landmarks_confidence=0.5
        )
        self.holistic_landmarker = vision.HolisticLandmarker.create_from_options(options)

    def get_landmarks(self, frame):
        """Extract landmarks from a single frame using MediaPipe Tasks API (33 pts)."""
        self._init_pose()
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        results = self.pose_landmarker.detect(mp_image)
        
        if results.pose_landmarks:
            return np.array([[lm.x, lm.y] for lm in results.pose_landmarks[0]])
        return None

    def get_holistic_landmarks(self, frame):
        """Extract 543 landmarks (Pose, Face, Hands) from a single frame."""
        self._init_holistic()
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        results = self.holistic_landmarker.detect(mp_image)
        
        all_lms = []
        # Pose (33)
        if results.pose_landmarks:
            all_lms.extend([[lm.x, lm.y] for lm in results.pose_landmarks])
        else:
            all_lms.extend([[0.0, 0.0]] * 33)
        
        # Face (468) - MediaPipe Holistic usually returns 468 face points
        if results.face_landmarks:
            all_lms.extend([[lm.x, lm.y] for lm in results.face_landmarks])
            # Ensure we have exactly 468 or 478 depending on model, but common is 468
            # If the user expects 543 total: 33 + 468 + 21 + 21 = 543
            if len(results.face_landmarks) < 468:
                all_lms.extend([[0.0, 0.0]] * (468 - len(results.face_landmarks)))
            elif len(results.face_landmarks) > 468:
                all_lms = all_lms[:33+468] # Truncate to 468
        else:
            all_lms.extend([[0.0, 0.0]] * 468)
            
        # Left Hand (21)
        if results.left_hand_landmarks:
            all_lms.extend([[lm.x, lm.y] for lm in results.left_hand_landmarks])
        else:
            all_lms.extend([[0.0, 0.0]] * 21)
            
        # Right Hand (21)
        if results.right_hand_landmarks:
            all_lms.extend([[lm.x, lm.y] for lm in results.right_hand_landmarks])
        else:
            all_lms.extend([[0.0, 0.0]] * 21)
            
        # Ensure total is exactly 543
        if len(all_lms) > 543:
            all_lms = all_lms[:543]
        elif len(all_lms) < 543:
            all_lms.extend([[0.0, 0.0]] * (543 - len(all_lms)))

        print(f"DEBUG: Holistic extracted {len(all_lms)} landmarks")
        return np.array(all_lms)

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

    async def _process_mls_core(self, video_id, source_path, output_path, params, lm_func):
        """Generic MLS core that handles different landmark sets."""
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
        
        # Get first and last frame landmarks for alignment
        ret, first_frame = cap.read()
        if not ret: 
            cap.release()
            return False
        first_lms = lm_func(first_frame)
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames - 1)
        ret, last_frame = cap.read()
        if not ret:
            # Fallback to current frame if last is not readable
            last_frame = first_frame
        last_lms = lm_func(last_frame)
        
        if first_lms is None or last_lms is None:
            cap.release()
            storage.update_video(video_id, {"refine_status": "idle", "refine_progress": 100})
            return False

        # 1. Get Landmarks (Target)
        target_lms = None 
        if params.get('manual_target_lms'):
            target_lms = np.array(params['manual_target_lms'])
        elif video.get("keyframes") and len(video["keyframes"]) > 0:
            try:
                kf = video["keyframes"][0]
                if lm_func == self.get_landmarks: # Standard 33 pts
                    pose_data = np.load(video["pose_cache"])
                    target_lms = pose_data[kf["frame"]]
                else: # Holistic (543) or Contour (133)
                    kf_path = os.path.join(os.path.dirname(video["clips_dir"]), "keyframes", f"frame_{kf['frame']}.jpg")
                    if os.path.exists(kf_path):
                        kf_img = cv2.imread(kf_path)
                        target_lms = lm_func(kf_img)
            except Exception as e:
                print(f"Error loading target lms: {e}")
                pass
        
        if target_lms is None: target_lms = first_lms
            
        # 2. Parameters
        strategy = params.get('strategy', 'progressive')
        fade_out_frames = int(params.get('fade_out_frames', 15))
        fade_in_frames = int(params.get('fade_in_frames', 15))
        alpha = float(params.get('alpha', 1.0))
        
        # 3. Setup Warp Points
        def get_anchored_dst(src, target):
            s_xy = src[:, :2]
            t_xy = target[:, :2]
            dst = t_xy.copy() * [width, height]
            s_px = s_xy.copy() * [width, height]
            if len(dst) >= 33: dst[25:33] = s_px[25:33] 
            if len(dst) == 543:
                for wrist_idx, h_start, h_end in [(501, 501, 522), (522, 522, 543)]:
                    wrist_src = s_px[wrist_idx]; wrist_dst = dst[wrist_idx]
                    disp = wrist_dst - wrist_src
                    for i in range(h_start, h_end): dst[i] = s_px[i] + disp
            return s_px, dst

        first_src_px, first_dst_px = get_anchored_dst(first_lms, target_lms)
        last_src_px, last_dst_px = get_anchored_dst(last_lms, target_lms)

        # 4. Process and Write Output
        temp_out = output_path + ".tmp.mp4"
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(temp_out, fourcc, fps, (width, height))
        
        if not out.isOpened():
            print(f"Error: Could not open VideoWriter for {temp_out}")
            cap.release()
            storage.update_video(video_id, {"refine_status": "error: writer fail", "refine_progress": 0})
            return False

        # Reset to beginning for processing
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        
        for i in range(total_frames):
            ret, frame = cap.read()
            if not ret: break
            
            await asyncio.sleep(0)
            storage.update_video(video_id, {
                "refine_status": "warping",
                "refine_progress": int((i + 1) / total_frames * 90)
            })

            warped = None
            if strategy == 'global':
                weight = i / (total_frames - 1)
                curr_src = first_src_px * (1 - weight) + last_src_px * weight
                curr_dst = first_dst_px * (1 - weight) + last_dst_px * weight
                warped = self.mls_warp_image(frame, curr_src, curr_dst, alpha=alpha)
            else:
                if i < fade_in_frames:
                    weight = 1.0 - (i / fade_in_frames)
                    curr_dst = first_src_px * (1 - weight) + first_dst_px * weight
                    warped = self.mls_warp_image(frame, first_src_px, curr_dst, alpha=alpha)
                elif i >= (total_frames - fade_out_frames):
                    dist_from_end = total_frames - 1 - i
                    weight = 1.0 - (dist_from_end / max(1, fade_out_frames - 1))
                    curr_dst = last_src_px * (1 - weight) + last_dst_px * weight
                    warped = self.mls_warp_image(frame, last_src_px, curr_dst, alpha=alpha)
                else:
                    warped = frame
            
            out.write(warped)
            
        out.release()
        cap.release()
        
        if not os.path.exists(temp_out) or os.path.getsize(temp_out) < 100:
            print(f"Error: Temp video file {temp_out} is missing or too small.")
            storage.update_video(video_id, {"refine_status": "error: temp file fail", "refine_progress": 0})
            return False

        import subprocess
        # Pass 1: Web Optimized Preview (Fast, Small, Browser-friendly)
        ffmpeg_web = [
            "ffmpeg", "-y", "-i", temp_out, "-i", source_path, 
            "-map", "0:v", "-map", "1:a?", 
            "-c:v", "libx264", 
            "-crf", "23", 
            "-preset", "faster", 
            "-pix_fmt", "yuv420p",
            "-c:a", "copy", 
            output_path
        ]
        res_web = subprocess.run(ffmpeg_web, capture_output=True, text=True)
        if res_web.returncode != 0:
            print(f"FFmpeg Web Error: {res_web.stderr}")

        # Pass 2: High-Quality Master (Lossless, All Keyframes for Production)
        output_hq = output_path.replace(".mp4", "_hq.mp4")
        ffmpeg_hq = [
            "ffmpeg", "-y", "-i", temp_out, "-i", source_path, 
            "-map", "0:v", "-map", "1:a?", 
            "-c:v", "libx264", 
            "-crf", "0", 
            "-preset", "medium", 
            "-g", "1", 
            "-bf", "0", 
            "-pix_fmt", "yuv420p",
            "-c:a", "copy", 
            output_hq
        ]
        res_hq = subprocess.run(ffmpeg_hq, capture_output=True, text=True)
        if res_hq.returncode != 0:
            print(f"FFmpeg HQ Error: {res_hq.stderr}")

        if os.path.exists(temp_out): os.remove(temp_out)
        
        # Verify final output exists
        if not os.path.exists(output_path):
            storage.update_video(video_id, {"refine_status": "error: ffmpeg fail", "refine_progress": 0})
            return False

        storage.update_video(video_id, {"refine_status": "idle", "refine_progress": 100})
        return True

    async def process_mls(self, video_id, source_path, output_path, params):
        """Standard 33-point MLS alignment."""
        return await self._process_mls_core(video_id, source_path, output_path, params, self.get_landmarks)

    async def process_holistic_mls(self, video_id, source_path, output_path, params):
        """High-precision 543-point Holistic MLS alignment."""
        return await self._process_mls_core(video_id, source_path, output_path, params, self.get_holistic_landmarks)

    async def process_contour_mls(self, video_id, source_path, output_path, params):
        """High-precision 133-point Silhouette/Contour MLS alignment."""
        return await self._process_mls_core(video_id, source_path, output_path, params, self.get_contour_landmarks)

    async def process_rife(self, video_id, source_path, output_path, params):
        from app.db.storage import storage
        from app.services.rife.interpolator import FrameInterpolator
        
        storage.update_video(video_id, {"refine_status": "starting rife", "refine_progress": 0})
        video = storage.get_video(video_id)
        if not video: return {"success": False}
        
        # 1. Get Reference Frame Path
        ref_path = None
        if video.get("keyframes") and len(video["keyframes"]) > 0:
            kf = video["keyframes"][0]
            ref_path = os.path.join(os.path.dirname(video["clips_dir"]), "keyframes", f"frame_{kf['frame']}.jpg")
        
        # Fallback to first frame of video if no keyframes or file missing
        temp_ref_path = None
        if not ref_path or not os.path.exists(ref_path):
            cap = cv2.VideoCapture(source_path)
            ret, frame = cap.read()
            cap.release()
            if ret:
                temp_ref_path = os.path.join(video["clips_dir"], f"temp_ref_{video_id}.jpg")
                cv2.imwrite(temp_ref_path, frame)
                ref_path = temp_ref_path
            else:
                return {"success": False}

        # 2. Parameters
        interpolation_factor = int(params.get('interpolation_factor', 4))
        interpolation_mode = params.get('interpolation_mode', 'both')
        
        # 3. Define Callback
        def status_callback(job_id, progress, message):
            if progress is not None:
                storage.update_video(video_id, {
                    "refine_status": f"RIFE: {message}",
                    "refine_progress": int(progress)
                })
            else:
                storage.update_video(video_id, {
                    "refine_status": f"RIFE: {message}"
                })

        # 4. Run Interpolator
        try:
            output_folder = video["clips_dir"]
            job_id = f"job_{os.urandom(4).hex()}"
            
            interpolator = FrameInterpolator(
                ref_path=ref_path,
                video_path=source_path,
                output_folder=output_folder,
                job_id=job_id,
                interpolation_factor=interpolation_factor,
                interpolation_mode=interpolation_mode,
                status_callback=status_callback
            )
            
            # interpolator.run() returns the path to the generated video
            result_path = await asyncio.to_thread(interpolator.run)
            added_frames = getattr(interpolator, 'added_frames_count', 0)
            
            # Move result to output_path
            import shutil
            if os.path.exists(output_path): os.remove(output_path)
            shutil.move(result_path, output_path)
            
            # Also create HQ version
            output_hq = output_path.replace(".mp4", "_hq.mp4")
            shutil.copy2(output_path, output_hq)
            
            # Cleanup
            if temp_ref_path and os.path.exists(temp_ref_path):
                os.remove(temp_ref_path)
            
            return {"success": True, "added_frames": added_frames, "mode": interpolation_mode}
        except Exception as e:
            print(f"RIFE Error: {e}")
            return {"success": False, "error": str(e)}
        finally:
            storage.update_video(video_id, {"refine_status": "idle", "refine_progress": 100})

alignment_service = AlignmentService()
