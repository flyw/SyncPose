#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Frame Interpolator
Handles video processing with RIFE interpolation for digital human videos
"""

import os
import cv2
import numpy as np
import torch
import subprocess
from .rife_model import RIFEModel


class FrameInterpolator:
    """
    Frame Interpolation Handler
    
    Processes video by interpolating frames using RIFE model,
    with reference frame matching for digital human consistency.
    """
    
    def __init__(self, ref_path, video_path, output_folder, job_id, 
                 interpolation_factor=2, status_callback=None):
        """
        Initialize frame interpolator
        
        Args:
            ref_path: Path to reference frame image
            video_path: Path to input video
            output_folder: Folder to save output video
            job_id: Unique job identifier
            interpolation_factor: Number of frames to interpolate (2-256)
            status_callback: Callback function for status updates
        """
        self.ref_path = ref_path
        self.video_path = video_path
        self.output_folder = output_folder
        self.job_id = job_id
        self.interpolation_factor = interpolation_factor
        self.status_callback = status_callback
        
        # Validate inputs
        if not os.path.exists(ref_path):
            raise FileNotFoundError(f"Reference frame not found: {ref_path}")
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video not found: {video_path}")
        
        # Output path
        self.output_path = os.path.join(output_folder, f"flowframe_{job_id}.mp4")
        
        # Initialize model
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = RIFEModel(device=self.device)
        
        # Load reference frame
        self.reference_frame = cv2.imread(ref_path)
        if self.reference_frame is None:
            raise ValueError(f"Failed to load reference frame: {ref_path}")
        
        self._update_status(5, "Model initialization complete")
    
    def _update_status(self, progress, message):
        """Update processing status"""
        if self.status_callback:
            self.status_callback(self.job_id, progress, message)
    
    def extract_frames(self, video_path):
        """Extract all frames from video"""
        frames = []
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise ValueError(f"Failed to open video: {video_path}")
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        self.video_info = {
            'total_frames': total_frames,
            'fps': fps,
            'width': width,
            'height': height
        }
        
        frame_count = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(frame)
            frame_count += 1
            
            # Update progress
            if frame_count % 10 == 0:
                progress = 10 + (frame_count / total_frames * 20)
                self._update_status(progress, f"Extracting frames: {frame_count}/{total_frames}")
        
        cap.release()
        return frames
    
    def match_reference_frame(self, frame, reference):
        """
        Soft color matching with brightness preservation
        """
        # Convert to float for processing
        frame_float = frame.astype(np.float32)
        ref_float = reference.astype(np.float32)

        matched = np.zeros_like(ref_float)
        
        # Calculate global brightness to check if we are darkening too much
        f_mean_global = frame_float.mean()
        r_mean_global = ref_float.mean()
        
        # Matching strength (0.0 to 1.0)
        # 0.8 means 80% video characteristic, 20% original photo
        strength = 0.8 
        
        # Process each channel (B, G, R) separately
        for i in range(3):
            f_mean, f_std = frame_float[:, :, i].mean(), frame_float[:, :, i].std()
            r_mean, r_std = ref_float[:, :, i].mean(), ref_float[:, :, i].std()
            
            # Transfer statistics
            channel = (ref_float[:, :, i] - r_mean) * (f_std / (r_std + 1e-5)) + f_mean
            matched[:, :, i] = channel

        # Soft blending to preserve some original "pop"
        result = matched * strength + ref_float * (1.0 - strength)
        
        # Brightness protection: if result is much darker than original ref, boost it slightly
        # but don't exceed the original ref brightness to avoid flashing
        res_mean = result.mean()
        if res_mean < r_mean_global * 0.8:
            boost = (r_mean_global * 0.8) / (res_mean + 1e-5)
            # Limit boost to 1.2x to prevent overexposure
            boost = min(1.2, boost)
            result = result * boost

        return np.clip(result, 0, 255).astype(np.uint8)
    
    def generate_transition_frames(self, start_frame, end_frame, num_frames):
        """
        Generate smooth transition frames using RIFE AI model
        
        Args:
            start_frame: Starting frame (numpy array)
            end_frame: Ending frame (numpy array)
            num_frames: Number of transition frames to generate
        
        Returns:
            List of transition frames
        """
        # Base progress for transitions could be 30 for start and 80 for end
        self._update_status(None, f"Using AI to generate {num_frames} transition frames...")
        
        try:
            # Use RIFE model for interpolation
            return self.model.interpolate_frames(start_frame, end_frame, num_frames)
        except Exception as e:
            raise RuntimeError(f"AI interpolation core error (RIFE-CUDA): {e}")
    
    def interpolate_video(self, frames):
        """
        Interpolate video frames using RIFE model
        Only interpolate: reference -> first frame -> video frames -> last frame -> reference
        
        Args:
            frames: List of input frames
        
        Returns:
            List of interpolated frames
        """
        if len(frames) < 2:
            raise ValueError("Need at least 2 frames for interpolation")
        
        # Get video dimensions
        video_height, video_width = frames[0].shape[:2]
        
        # Step 0: Pre-process reference frame to match video colors and size
        self._update_status(15, "Aligning standard frame colors...")
        if self.reference_frame.shape[:2] != (video_height, video_width):
            self.reference_frame = cv2.resize(self.reference_frame, (video_width, video_height))
        
        # Match colors of reference frame to the video
        self.reference_frame = self.match_reference_frame(frames[0], self.reference_frame)
        self._update_status(20, "Color alignment complete")
        
        interpolated_frames = []
        
        # Add the starting reference frame
        interpolated_frames.append(self.reference_frame.copy())
        
        # Step 1: Generate transition from reference frame to first video frame
        self._update_status(30, "Processing: Standard frame -> First video frame...")
        # interpolation_factor is the multiplier (e.g., 4x means insert 3 frames)
        num_transition = max(0, self.interpolation_factor - 1)
        
        if num_transition > 0:
            transition_start = self.generate_transition_frames(
                self.reference_frame, frames[0], num_transition
            )
            interpolated_frames.extend(transition_start)
        self._update_status(40, "First frame transition complete")
        
        # Step 2: Add all original video frames (NO interpolation in middle)
        self._update_status(50, "Adding original video frames...")
        for i, frame in enumerate(frames):
            interpolated_frames.append(frame.copy())
            
            if i % 30 == 0:
                progress = 50 + (i / len(frames) * 30)
                self._update_status(progress, f"Adding frame: {i}/{len(frames)}")
        
        # Step 3: Generate transition from last video frame back to reference frame
        self._update_status(80, "Processing: Last video frame -> Standard frame...")
        if num_transition > 0:
            transition_end = self.generate_transition_frames(
                frames[-1], self.reference_frame, num_transition
            )
            interpolated_frames.extend(transition_end)
        
        # Add the ending reference frame
        interpolated_frames.append(self.reference_frame.copy())
        self._update_status(90, "Last frame transition complete")
        
        return interpolated_frames
    
    def create_output_video(self, frames, output_path):
        """Create output video from frames with web-compatible encoding"""
        if not frames:
            raise ValueError("No frames to create video")

        height, width = frames[0].shape[:2]
        fps = self.video_info['fps']
        
        # 1. Create temporary video using OpenCV (fast but not web-compatible)
        temp_path = output_path.replace('.mp4', '_temp.mp4')
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(temp_path, fourcc, fps, (width, height))

        if not out.isOpened():
            raise ValueError(f"Failed to create temporary video: {temp_path}")

        for i, frame in enumerate(frames):
            out.write(frame)
            if i % 30 == 0:
                progress = 80 + (i / len(frames) * 10)
                self._update_status(progress, f"Generating temporary video: {i}/{len(frames)} frames")

        out.release()
        
        # 2. Use FFmpeg to re-encode to H.264 (libx264) for browser compatibility
        self._update_status(92, "Optimizing video format for browser preview...")
        try:
            cmd = [
                'ffmpeg', '-y',
                '-i', temp_path,
                '-c:v', 'libx264',
                '-pix_fmt', 'yuv420p',
                '-crf', '20',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                import shutil
                shutil.move(temp_path, output_path)
            else:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                
        except Exception as e:
            import shutil
            shutil.move(temp_path, output_path)
    
    def run(self):
        """
        Main processing pipeline
        
        Returns:
            Path to output video
        """
        try:
            # Step 1: Extract frames
            self._update_status(10, "Extracting video frames...")
            frames = self.extract_frames(self.video_path)
            
            if len(frames) < 2:
                raise ValueError("Insufficient video frames, at least 2 frames required")
            
            # Step 2: Interpolate frames
            self._update_status(30, "Starting AI interpolation...")
            interpolated_frames = self.interpolate_video(frames)
            
            # Step 3: Create output video
            self._update_status(80, "Generating output video...")
            self.create_output_video(interpolated_frames, self.output_path)
            
            # Step 4: Cleanup
            self._update_status(100, "Processing complete!")
            
            return self.output_path
            
        except Exception as e:
            self._update_status(0, f"Processing failed: {str(e)}")
            raise
    
    def cleanup(self):
        """Cleanup temporary files"""
        import gc
        if hasattr(self, 'model'):
            del self.model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect()
