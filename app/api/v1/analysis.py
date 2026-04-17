from fastapi import APIRouter, HTTPException, Request
from app.services.pose_service import pose_service
from app.db.storage import storage
import numpy as np

router = APIRouter()

@router.get("/{video_id}")
async def get_analysis(video_id: str, threshold: float = 92.0):
    results = pose_service.get_analysis_results(video_id, threshold=threshold)
    if not results:
        raise HTTPException(status_code=404, detail="Analysis results not found. Make sure pose extraction is complete.")
    return results

@router.post("/{video_id}/re-sync")
async def re_sync(video_id: str, request: Request):
    data = await request.json()
    frame_idx = data.get('frame_index')
    threshold = float(data.get('threshold', 92.0))
    
    video = storage.get_video(video_id)
    if not video or "pose_cache" not in video:
        raise HTTPException(status_code=404, detail="Video or pose data not found")
        
    landmarks_data = np.load(video["pose_cache"])
    if frame_idx < 0 or frame_idx >= len(landmarks_data):
        raise HTTPException(status_code=400, detail="Invalid frame index")
        
    ref_lms = landmarks_data[frame_idx]
    results = pose_service.get_analysis_results(video_id, ref_lms=ref_lms, threshold=threshold)
    return results
