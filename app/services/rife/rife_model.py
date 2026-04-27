#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RIFE Model Wrapper for PyTorch/CUDA Implementation
"""

import os
import torch
import cv2
import numpy as np
import torch.nn.functional as F
from .rife_hdv3 import IFNet
from app.core.config import settings

class RIFEModel:
    """
    Wrapper for RIFE-CUDA (PyTorch) model
    """
    def __init__(self, device=None):
        if device is None:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = device
            
        print(f"Initializing RIFE-CUDA on device: {self.device}")
        
        # Paths
        self.model_path = settings.RIFE_MODEL_PATH
        
        # Load Model
        self.flownet = IFNet()
        if os.path.exists(self.model_path):
            state_dict = torch.load(self.model_path, map_location='cpu')
            # Remove 'module.' prefix if present (from DDP)
            new_state_dict = {}
            for k, v in state_dict.items():
                if k.startswith('module.'):
                    new_state_dict[k[7:]] = v
                else:
                    new_state_dict[k] = v
            self.flownet.load_state_dict(new_state_dict)
        else:
            print(f"Warning: Model weights not found at {self.model_path}")
            
        self.flownet.to(self.device)
        self.flownet.eval()

    def _preprocess(self, frame):
        """Convert numpy BGR to torch RGB tensor"""
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = torch.from_numpy(frame.transpose(2, 0, 1)).unsqueeze(0).float() / 255.0
        return img.to(self.device)

    def _postprocess(self, tensor):
        """Convert torch RGB tensor to numpy BGR image"""
        img = tensor.squeeze(0).cpu().numpy().transpose(1, 2, 0)
        img = (img * 255.0).clip(0, 255).astype(np.uint8)
        return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    def interpolate_frames(self, frame0, frame1, num_frames=1):
        """
        Recursive interpolation for higher quality and true multi-frame support
        """
        if num_frames <= 0:
            return []

        # Convert to tensor
        img0 = self._preprocess(frame0)
        img1 = self._preprocess(frame1)

        # Padding to 32
        n, c, h, w = img0.shape
        ph = ((h - 1) // 32 + 1) * 32
        pw = ((w - 1) // 32 + 1) * 32
        padding = (0, pw - w, 0, ph - h)
        img0 = F.pad(img0, padding)
        img1 = F.pad(img1, padding)

        results = []
        
        with torch.no_grad():
            # Standard recursive RIFE logic
            # This is much faster and higher quality than linear blending
            def execute_recursive(i0, i1, n):
                if n == 0:
                    return []
                
                # Middle frame (0.5)
                flow_list, mask, mid_merged = self.flownet(torch.cat((i0, i1), 1), scale_list=[4, 2, 1])
                mid = mid_merged[2]
                
                # Free unused tensors to prevent OOM during deep recursion
                del flow_list, mask, mid_merged
                
                if n == 1:
                    return [self._postprocess(mid[:, :, :h, :w])]
                
                # To generate exactly 'n' frames:
                # We generate n // 2 frames on the left, 1 in the middle, and the rest on the right.
                left_n = n // 2
                right_n = n - left_n - 1
                
                # Recursive split
                res_left = execute_recursive(i0, mid, left_n)
                res_right = execute_recursive(mid, i1, right_n)
                
                mid_img = self._postprocess(mid[:, :, :h, :w])
                
                return res_left + [mid_img] + res_right

            # Get all intermediate frames directly as numpy arrays
            results = execute_recursive(img0, img1, num_frames)

        return results
