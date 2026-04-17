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

@router.post("/{video_id}/export_slice")
async def export_slice(video_id: str, request: Request):
    data = await request.json()
    video = storage.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    start_frame = data['start_frame']
    end_frame = data['end_frame']
    action_name = data['name']
    fps = video['fps']
    
    start_time = start_frame / fps
    duration = (end_frame - start_frame) / fps
    
    output_filename = f"{video_id}_{action_name}.mp4"
    output_path = os.path.join(settings.CLIPS_DIR, output_filename)
    
    cmd = [
        "ffmpeg", "-y", "-ss", str(start_time), "-t", str(duration),
        "-i", video['path'], "-c:v", "libx264", "-c:a", "aac",
        "-preset", "ultrafast", output_path
    ]
    subprocess.run(cmd, capture_output=True)
    
    return {"url": f"/static/clips/{output_filename}"}
