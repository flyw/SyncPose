from fastapi import APIRouter, UploadFile, File, HTTPException, Response, Form
import os
import uuid
import shutil
import cv2
import numpy as np
from app.core.config import settings
from app.db.storage import storage
from app.services.pose_service import pose_service

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

@router.get("/{video_id}/frame_image/{idx}")
async def get_frame_image(video_id: str, idx: int):
    video = storage.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
        
    cap = cv2.VideoCapture(video["path"])
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        raise HTTPException(status_code=404, detail="Frame not found")
        
    _, img_encoded = cv2.imencode('.jpg', frame)
    return Response(content=img_encoded.tobytes(), media_type="image/jpeg")
