from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from app.db.storage import storage
from app.services.alignment_service import alignment_service
import os
import numpy as np
import cv2
import re
from datetime import datetime
import asyncio

router = APIRouter()

async def run_refinement_task(video_id, operation, source_path, output_path, params, remarks, clips_dir, output_filename):
    try:
        rife_data = None
        if operation == 'mls':
            success = await alignment_service.process_mls(video_id, source_path, output_path, params)
        elif operation == 'holistic':
            success = await alignment_service.process_holistic_mls(video_id, source_path, output_path, params)
        elif operation == 'contour':
            success = await alignment_service.process_contour_mls(video_id, source_path, output_path, params)
        elif operation == 'rife':
            result = await alignment_service.process_rife(video_id, source_path, output_path, params)
            success = result.get("success", False)
            if success:
                rife_data = result
        else:
            success = False
        
        if success:
            if operation == 'rife' and rife_data:
                mode_map = {'both': 'Front & Back', 'front': 'Front Only', 'back': 'Back Only'}
                display_mode = mode_map.get(rife_data.get('mode'), rife_data.get('mode'))
                final_remarks = f"RIFE ({display_mode}, +{rife_data.get('added_frames')}f)"
                storage._save_clip_metadata(clips_dir, output_filename, {"remarks": final_remarks})
            else:
                storage._save_clip_metadata(clips_dir, output_filename, {"remarks": remarks})
    except Exception as e:
        print(f"Background Task Error: {e}")
    finally:
        storage.update_video(video_id, {"refine_status": "idle", "refine_progress": 100})

@router.get("/{video_id}/clips")
async def get_clips(video_id: str):
    clips = storage.get_project_clips(video_id)
    return clips

@router.post("/{video_id}/process")
async def process_clip(video_id: str, request: Request, background_tasks: BackgroundTasks):
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
    name_base = re.sub(r'_\d{8}_\d{6}$', '', name_base)
    
    strategy = params.get('strategy', 'prog')
    suffix = f"_{operation}"
    if operation == 'mls':
        suffix = f"_mls_{strategy}"
    elif operation == 'holistic':
        suffix = f"_holistic_{strategy}"
    elif operation == 'contour':
        suffix = f"_contour_{strategy}"
    elif operation == 'rife':
        suffix = f"_rife"
        
    output_filename = f"{name_base}{suffix}_{timestamp}{ext}"
    output_path = os.path.join(video["clips_dir"], output_filename)
    
    if manual_lms: 
        params['manual_target_lms'] = manual_lms

    if not remarks:
        remarks = f"{operation.upper()} ({strategy})"

    background_tasks.add_task(
        run_refinement_task,
        video_id, operation, source_path, output_path, params, remarks, video["clips_dir"], output_filename
    )
    
    return {
        "status": "started",
        "filename": output_filename
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
        # Also try to remove the HQ version if it exists
        hq_path = clip_path.replace(".mp4", "_hq.mp4")
        if os.path.exists(hq_path):
            os.remove(hq_path)
        return {"message": "Clip deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete clip: {str(e)}")

@router.post("/{video_id}/clips/{filename}/remarks")
async def update_clip_remarks(video_id: str, filename: str, request: Request):
    data = await request.json()
    video = storage.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    remarks = data.get('remarks', '')
    storage._save_clip_metadata(video["clips_dir"], filename, {"remarks": remarks})
    return {"message": "Remarks updated"}

@router.post("/{video_id}/preview_mls")
async def preview_mls(video_id: str, request: Request):
    data = await request.json()
    video = storage.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
        
    source_filename = data.get('source_filename')
    params = data.get('params', {})
    method = data.get('method', 'mls')
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
        
    if method == 'holistic':
        lm_func = alignment_service.get_holistic_landmarks
    elif method == 'contour':
        lm_func = alignment_service.get_contour_landmarks
    else:
        lm_func = alignment_service.get_landmarks
        
    warp_lms = lm_func(warp_frame)

    # 2. Get target landmarks (Priority: Manual > Project Global Keyframe > Clip First Frame)
    target_lms = None
    if manual_lms:
        target_lms = np.array(manual_lms)[:, :2] # Ensure only x, y
    elif video.get("keyframes") and len(video["keyframes"]) > 0:
        try:
            # For holistic/contour, we need to extract from keyframe if not cached (cache is usually 33 pts)
            if method in ['holistic', 'contour']:
                # Load the frame image to extract landmarks
                kf = video["keyframes"][0]
                kf_path = os.path.join(os.path.dirname(video["clips_dir"]), "keyframes", f"frame_{kf['frame']}.jpg")
                if os.path.exists(kf_path):
                    kf_img = cv2.imread(kf_path)
                    target_lms = lm_func(kf_img)
            else:
                pose_data = np.load(video["pose_cache"])
                ref_idx = video["keyframes"][0]["frame"]
                target_lms = pose_data[ref_idx][:, :2]
        except Exception as e: 
            print(f"Target landmarks error: {e}")
            pass

    if target_lms is None:
        target_lms = lm_func(first_frame)
    
    if target_lms is None or warp_lms is None:
        raise HTTPException(status_code=400, detail="Could not detect landmarks for alignment")
        
    h, w = warp_frame.shape[:2]
    src_px = warp_lms[:, :2] * [w, h]
    dst_px = target_lms[:, :2] * [w, h]
    
    # Strategy-based weight
    strategy = params.get('strategy', 'progressive')
    
    if strategy == 'global':
        # In global mode, we interpolate between first and last frame's alignment state
        weight = target_idx / max(1, total_frames - 1)
        
        # We need landmarks for first and last frames to compute the bridge
        cap = cv2.VideoCapture(source_path)
        ret_f, first_f = cap.read()
        cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames - 1)
        ret_l, last_f = cap.read()
        cap.release()
        
        first_lms = lm_func(first_f)
        last_lms = lm_func(last_f)
        
        if first_lms is not None and last_lms is not None:
            f_src = first_lms[:, :2] * [w, h]
            l_src = last_lms[:, :2] * [w, h]
            target_px = target_lms[:, :2] * [w, h]
            
            # Create anchored targets for both ends
            f_dst = target_px.copy(); l_dst = target_px.copy()
            if len(target_px) >= 33:
                f_dst[25:33] = f_src[25:33]
                l_dst[25:33] = l_src[25:33]
            
            # Rigid Hand Translation for Holistic Preview
            if len(target_px) == 543:
                # Left Hand: 501, Right Hand: 522
                for w_idx, h_start, h_end in [(501, 501, 522), (522, 522, 543)]:
                    # For first frame bridge
                    f_disp = f_dst[w_idx] - f_src[w_idx]
                    for i in range(h_start, h_end):
                        f_dst[i] = f_src[i] + f_disp
                    # For last frame bridge
                    l_disp = l_dst[w_idx] - l_src[w_idx]
                    for i in range(h_start, h_end):
                        l_dst[i] = l_src[i] + l_disp
            
            # Interpolated source and destination for the current frame
            curr_src_px = f_src * (1 - weight) + l_src * weight
            curr_dst_px = f_dst * (1 - weight) + l_dst * weight
            
            warped = alignment_service.mls_warp_image(warp_frame, curr_src_px, curr_dst_px, alpha=alpha, draw_grid=show_grid)
        else:
            # Fallback if detection fails
            warped = alignment_service.mls_warp_image(warp_frame, src_px, dst_px, alpha=alpha, draw_grid=show_grid)
    else:
        # Progressive mode weight (remains as before but uses weight variable)
        weight = 1.0
        fade_in = int(params.get('fade_in_frames', 15))
        fade_out = int(params.get('fade_out_frames', 15))
        
        if target_idx < fade_in:
            weight = 1.0 - (target_idx / max(1, fade_in))
        elif target_idx >= (total_frames - fade_out):
            dist_from_end = total_frames - 1 - target_idx
            weight = 1.0 - (dist_from_end / max(1, fade_out - 1))
        else:
            weight = 0.0
            
        # Anchor feet for progressive
        if len(dst_px) >= 33:
            dst_px[25:33] = src_px[25:33]
        
        curr_dst = src_px * (1 - weight) + dst_px * weight
        warped = alignment_service.mls_warp_image(warp_frame, src_px, curr_dst, alpha=alpha, draw_grid=show_grid)
    
    preview_filename = f"preview_{video_id}.jpg"
    preview_path = os.path.join(video["clips_dir"], preview_filename)
    cv2.imwrite(preview_path, warped)
    
    return {
        "url": f"/uploads/{video_id}/clips/{preview_filename}?t={os.urandom(4).hex()}"
    }
