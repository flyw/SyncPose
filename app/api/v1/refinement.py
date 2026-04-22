from fastapi import APIRouter, HTTPException, Request
from app.db.storage import storage
from app.services.alignment_service import alignment_service
import os
import numpy as np
import cv2
import re
from datetime import datetime

router = APIRouter()

@router.get("/{video_id}/clips")
async def get_clips(video_id: str):
    clips = storage.get_project_clips(video_id)
    return clips

@router.post("/{video_id}/process")
async def process_clip(video_id: str, request: Request):
    data = await request.json()
    video = storage.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    source_filename = data.get('source_filename')
    operation = data.get('operation') # 'mls' or 'rife'
    params = data.get('params', {})
    remarks = data.get('remarks', '')
    manual_lms = data.get('manual_target_lms')
    
    source_path = os.path.join(video["clips_dir"], source_filename)
    if not os.path.exists(source_path):
        raise HTTPException(status_code=404, detail="Source clip not found")
    
    # Generate output filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name_base, ext = os.path.splitext(source_filename)
    
    # Remove previous timestamps if they exist
    name_base = re.sub(r'_\d{8}_\d{6}$', '', name_base)
    
    suffix = f"_{operation}"
    if operation == 'mls':
        strategy = params.get('strategy', 'prog')
        suffix = f"_mls_{strategy}"
    elif operation == 'rife':
        suffix = f"_rife"
        
    output_filename = f"{name_base}{suffix}_{timestamp}{ext}"
    output_path = os.path.join(video["clips_dir"], output_filename)
    
    # Call the service
    try:
        if operation == 'mls':
            if manual_lms: params['manual_target_lms'] = manual_lms
            success = await alignment_service.process_mls(video_id, source_path, output_path, params)
        elif operation == 'rife':
            success = await alignment_service.process_rife(video_id, source_path, output_path, params)
        else:
            raise HTTPException(status_code=400, detail="Invalid operation")
            
        if not success:
            raise HTTPException(status_code=500, detail="Processing failed")
        
        # Save remarks to metadata
        storage._save_clip_metadata(video["clips_dir"], output_filename, {"remarks": remarks})
            
    except Exception as e:
        print(f"Refinement Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
        
    return {
        "filename": output_filename, 
        "url": f"/uploads/{video_id}/clips/{output_filename}"
    }

@router.delete("/{video_id}/clips/{filename}")
async def delete_clip(video_id: str, filename: str):
    video = storage.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    clip_path = os.path.join(video["clips_dir"], filename)
    if not os.path.exists(clip_path):
        raise HTTPException(status_code=404, detail="Clip not found")
    
    try:
        os.remove(clip_path)
        return {"message": "Clip deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete clip: {str(e)}")

@router.post("/{video_id}/preview_mls")
async def preview_mls(video_id: str, request: Request):
    data = await request.json()
    video = storage.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
        
    source_filename = data.get('source_filename')
    params = data.get('params', {})
    alpha = float(params.get('alpha', 1.0))
    show_grid = params.get('show_grid', False)
    frame_idx = data.get('frame_index')
    manual_lms = data.get('manual_target_lms')
    
    source_path = os.path.join(video["clips_dir"], source_filename)
    if not os.path.exists(source_path):
        raise HTTPException(status_code=404, detail="Source clip not found")
        
    cap = cv2.VideoCapture(source_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    ret, first_frame = cap.read()
    
    target_idx = frame_idx if frame_idx is not None else (total_frames - 1)
    target_idx = max(0, min(target_idx, total_frames - 1))
    
    cap.set(cv2.CAP_PROP_POS_FRAMES, target_idx)
    ret2, warp_frame = cap.read()
    cap.release()
    
    if not ret or not ret2:
        raise HTTPException(status_code=500, detail="Failed to read frames from clip")
        
    warp_lms = alignment_service.get_landmarks(warp_frame)

    # 2. Get target landmarks (Priority: Manual > Project Global Keyframe > Clip First Frame)
    target_lms = None
    if manual_lms:
        target_lms = np.array(manual_lms)[:, :2] # Ensure only x, y
    elif video.get("keyframes") and len(video["keyframes"]) > 0:
        try:
            pose_data = np.load(video["pose_cache"])
            ref_idx = video["keyframes"][0]["frame"]
            target_lms = pose_data[ref_idx][:, :2]
        except: pass

    if target_lms is None:
        target_lms = alignment_service.get_landmarks(first_frame)
    
    if target_lms is None or warp_lms is None:
        raise HTTPException(status_code=400, detail="Could not detect pose for alignment")
        
    h, w = warp_frame.shape[:2]
    src_px = warp_lms * [w, h]
    dst_px = target_lms * [w, h]
    
    if len(dst_px) > 25:
        dst_px[25:] = src_px[25:]
    
    warped = alignment_service.mls_warp_image(warp_frame, src_px, dst_px, alpha=alpha, draw_grid=show_grid)
    
    preview_filename = f"preview_{video_id}.jpg"
    preview_path = os.path.join(video["clips_dir"], preview_filename)
    cv2.imwrite(preview_path, warped)
    
    return {
        "url": f"/uploads/{video_id}/clips/{preview_filename}?t={os.urandom(4).hex()}"
    }
