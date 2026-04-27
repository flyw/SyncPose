import os
import cv2
from fastapi import APIRouter, HTTPException
from app.db.storage import storage
from app.core.config import settings

from typing import List
from pydantic import BaseModel

router = APIRouter()

class KeyframeItem(BaseModel):
    frame: int
    timestamp: float
    image_url: str = None

@router.post("/{video_id}/keyframes")
async def save_keyframes(video_id: str, keyframes: List[KeyframeItem]):
    video = storage.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Convert Pydantic models back to dict for storage
    keyframes_dict = [k.dict() for k in keyframes]
    storage.update_video(video_id, {"keyframes": keyframes_dict})
    return {"message": "Keyframes metadata saved"}

@router.post("/{video_id}/save_frame/{idx}")
async def save_keyframe_image(video_id: str, idx: int):
    video = storage.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    project_dir = video.get("project_dir")
    keyframes_dir = os.path.join(project_dir, "keyframes")
    os.makedirs(keyframes_dir, exist_ok=True)
    
    image_path = os.path.join(keyframes_dir, f"frame_{idx}.jpg")
    
    # If already cached, just return the path
    if os.path.exists(image_path):
        return {"url": f"/{image_path}", "filename": f"frame_{idx}.jpg"}
    
    # Extract frame using OpenCV
    cap = cv2.VideoCapture(video["path"])
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        raise HTTPException(status_code=500, detail="Failed to extract frame")
        
    # Save as high-quality JPG
    cv2.imwrite(image_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
    
    return {"url": f"/{image_path}", "filename": f"frame_{idx}.jpg"}

@router.get("/{video_id}/keyframes")
async def get_keyframes(video_id: str):
    video = storage.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return video.get("keyframes", [])
