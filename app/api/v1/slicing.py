from fastapi import APIRouter, HTTPException, Request
from app.db.storage import storage
import os
import subprocess
from app.core.config import settings

from typing import List
from pydantic import BaseModel

router = APIRouter()

class SliceItem(BaseModel):
    name: str
    start_frame: int
    end_frame: int

@router.post("/{video_id}/slices")
async def save_slices(video_id: str, slices: List[SliceItem]):
    video = storage.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    slices_dict = [s.dict() for s in slices]
    storage.update_video(video_id, {"slices": slices_dict})
    return {"message": "Slices saved"}

@router.get("/{video_id}/slices")
async def get_slices(video_id: str):
    video = storage.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return video.get("slices", [])

@router.post("/{video_id}/export")
async def export_slice(video_id: str, request: Request):
    data = await request.json()
    video = storage.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    start_frame = data.get('start_frame', 0)
    end_frame = data.get('end_frame', 0)
    action_name = data.get('name', 'unnamed')
    fps = video['fps']
    
    if end_frame <= start_frame:
        raise HTTPException(status_code=400, detail="End frame must be greater than start frame")

    # Clean filename (Allow Unicode/Chinese, but remove path separators and illegal chars)
    import re
    # Remove characters that are illegal in most filesystems: \/:*?"<>|
    safe_name = re.sub(r'[\x00-\x1f\\/:*?"<>|]', '_', action_name)
    # Strip leading/trailing dots and spaces
    safe_name = safe_name.strip('. ')
    if not safe_name:
        safe_name = "unnamed"
        
    output_filename = f"{safe_name}_{start_frame}_{end_frame}.mp4"
    output_path = os.path.join(video["clips_dir"], output_filename)
    
    start_time = start_frame / fps
    duration = (end_frame - start_frame) / fps
    
    # Pass 1: Web Optimized Preview (Fast, Small, Browser-friendly)
    cmd_web = [
        "ffmpeg", "-y", 
        "-ss", f"{start_time:.4f}", 
        "-t", f"{duration:.4f}",
        "-i", video['path'],
        "-c:v", "libx264", 
        "-preset", "faster", 
        "-crf", "23", 
        "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        output_path
    ]
    
    # Pass 2: High-Quality Master (Lossless, All Keyframes for Production)
    output_hq = output_path.replace(".mp4", "_hq.mp4")
    cmd_hq = [
        "ffmpeg", "-y", 
        "-ss", f"{start_time:.4f}", 
        "-t", f"{duration:.4f}",
        "-i", video['path'],
        "-c:v", "libx264", 
        "-preset", "medium", 
        "-crf", "0",              # 0 means Lossless
        "-g", "1",                # Every frame is an Intra-frame (Keyframe)
        "-bf", "0",               # No B-frames
        "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        output_hq
    ]
    
    # Run Web export
    process_web = subprocess.run(cmd_web, capture_output=True, text=True)
    if process_web.returncode != 0:
        print(f"FFmpeg Web Error: {process_web.stderr}")
        raise HTTPException(status_code=500, detail="FFmpeg web processing failed")

    # Run HQ export
    process_hq = subprocess.run(cmd_hq, capture_output=True, text=True)
    if process_hq.returncode != 0:
        print(f"FFmpeg HQ Error: {process_hq.stderr}")
        # Not raising here as web version was successful, but logging it
    
    return {
        "filename": output_filename,
        "url": f"/uploads/{video_id}/clips/{output_filename}"
    }
