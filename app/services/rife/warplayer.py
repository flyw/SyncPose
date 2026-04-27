import torch
import torch.nn as nn

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def warp(img, flow):
    """
    Warp an image or feature map with optical flow.
    Args:
        img (Tensor): size (N, C, H, W)
        flow (Tensor): size (N, 2, H, W)
    Returns:
        Tensor: warped image
    """
    B, C, H, W = img.size()
    # mesh grid 
    grid_x = torch.linspace(-1.0, 1.0, W).view(1, 1, 1, W).expand(B, 1, H, W)
    grid_y = torch.linspace(-1.0, 1.0, H).view(1, 1, H, 1).expand(B, 1, H, W)
    grid = torch.cat([grid_x, grid_y], 1).to(device)
    
    # Scale flow to be between -1 and 1
    vgrid = grid + torch.cat([flow[:, 0:1, :, :] / ((W - 1.0) / 2.0), 
                              flow[:, 1:2, :, :] / ((H - 1.0) / 2.0)], 1)
    
    # grid_sample expects (N, H, W, 2)
    vgrid = vgrid.permute(0, 2, 3, 1)        
    output = torch.nn.functional.grid_sample(img, vgrid, align_corners=True)
    return output
