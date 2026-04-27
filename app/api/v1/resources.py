from fastapi import APIRouter, UploadFile, File, HTTPException, Response, Form
from fastapi.responses import FileResponse
import os
import uuid
import shutil
import cv2
import numpy as np
from app.core.config import settings
from app.db.storage import storage
from app.services.pose_service import pose_service
from app.services.alignment_service import alignment_service

router = APIRouter()

@router.post("/upload")
async def upload_video(name: str = Form(...), file: UploadFile = File(...)):
    if not file.filename.endswith((".mp4", ".avi", ".mov", ".mkv")):
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    project_dir = os.path.join(settings.UPLOAD_DIR, name)
    os.makedirs(project_dir, exist_ok=True)
    
    video_id = str(uuid.uuid4())
    filename = f"original_{file.filename}"
    file_path = os.path.join(project_dir, filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Generate a thumbnail for preview
    thumb_path = os.path.join(project_dir, "thumbnail.jpg")
    cap = cv2.VideoCapture(file_path)
    ret, frame = cap.read()
    if ret:
        cv2.imwrite(thumb_path, frame)
    cap.release()

    video_info = {
        "id": video_id,
        "name": name,
        "filename": file.filename,
        "path": file_path,
        "project_dir": project_dir,
        "thumbnail": thumb_path,
        "status": "uploaded",
        "progress": 0,
        "created_at": str(uuid.uuid1())
    }
    storage.add_video(video_id, video_info)
    
    return video_info

@router.get("/")
async def list_videos():
    return storage.list_videos()

@router.get("/{video_id}")
async def get_video(video_id: str):
    video = storage.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return video

@router.delete("/{video_id}")
async def delete_video(video_id: str):
    success = storage.delete_video(video_id)
    if not success:
        raise HTTPException(status_code=404, detail="Video not found")
    return {"message": "Video project deleted"}

@router.post("/{video_id}/analyze")
async def analyze_video(video_id: str):
    success = pose_service.start_analysis(video_id)
    if not success:
        raise HTTPException(status_code=404, detail="Video not found")
    return {"message": "Analysis started"}

@router.delete("/{video_id}/pose")
async def delete_pose_data(video_id: str):
    video = storage.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    pose_cache = video.get("pose_cache")
    if pose_cache and os.path.exists(pose_cache):
        os.remove(pose_cache)
        # Update in-memory state to reflect the change
        storage.update_video(video_id, {"status": "uploaded", "progress": 0, "pose_cache": None})
        return {"message": "Pose data deleted"}
    
    raise HTTPException(status_code=404, detail="Pose data not found")

@router.get("/{video_id}/frame_data/{idx}")
async def get_frame_data(video_id: str, idx: int):
    video = storage.get_video(video_id)
    if not video or "pose_cache" not in video:
        raise HTTPException(status_code=404, detail="Video or pose data not found")
    
    landmarks_data = np.load(video["pose_cache"])
    if idx < 0 or idx >= len(landmarks_data):
        raise HTTPException(status_code=400, detail="Invalid frame index")
        
    return {
        "landmarks": landmarks_data[idx].tolist()
    }

@router.get("/{video_id}/holistic_frame_data/{idx}")
async def get_holistic_frame_data(video_id: str, idx: int):
    video = storage.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
        
    cap = cv2.VideoCapture(video["path"])
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        raise HTTPException(status_code=404, detail="Frame not found")
        
    lms = alignment_service.get_holistic_landmarks(frame)
    return {
        "landmarks": lms.tolist()
    }

@router.get("/{video_id}/frame_image/{idx}")
async def get_frame_image(video_id: str, idx: int):
    video = storage.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Check cache first
    project_dir = video.get("project_dir")
    keyframes_dir = os.path.join(project_dir, "keyframes")
    os.makedirs(keyframes_dir, exist_ok=True)
    cache_path = os.path.join(keyframes_dir, f"frame_{idx}.jpg")
    
    if os.path.exists(cache_path):
        return FileResponse(
            cache_path, 
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=31536000"}
        )
        
    cap = cv2.VideoCapture(video["path"])
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        raise HTTPException(status_code=404, detail="Frame not found")
        
    # Save to cache as high-quality JPG and return
    cv2.imwrite(cache_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
    return FileResponse(
        cache_path, 
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=31536000"}
    )
