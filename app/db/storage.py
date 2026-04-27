import os
import cv2
import shutil
import json
from app.core.config import settings

class Storage:
    def __init__(self):
        self._transient_state = {} 
    
    def _get_project_data_path(self, project_dir):
        return os.path.join(project_dir, "project_data.json")

    def _load_project_data(self, project_dir):
        path = self._get_project_data_path(project_dir)
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_project_data(self, project_dir, data):
        path = self._get_project_data_path(project_dir)
        with open(path, 'w') as f:
            json.dump(data, f, indent=4)

    def list_videos(self):
        projects = []
        if not os.path.exists(settings.UPLOAD_DIR):
            return []

        for entry in os.scandir(settings.UPLOAD_DIR):
            if entry.is_dir() and not entry.name.startswith('.'):
                project_name = entry.name
                project_dir = entry.path
                
                all_files = os.listdir(project_dir)
                video_files = [f for f in all_files if f.lower().endswith((".mp4", ".avi", ".mov", ".mkv"))]
                if not video_files:
                    continue
                
                video_filename = [f for f in video_files if f.startswith("original_")][0] if any(f.startswith("original_") for f in video_files) else video_files[0]
                video_path = os.path.join(project_dir, video_filename)
                
                # Metadata persistence
                project_data = self._load_project_data(project_dir)
                
                thumb_path = os.path.join(project_dir, "thumbnail.jpg")
                if not os.path.exists(thumb_path):
                    jpg_files = [f for f in all_files if f.lower().endswith(".jpg") and "thumb" not in f.lower()]
                    if jpg_files:
                        shutil.copy2(os.path.join(project_dir, jpg_files[0]), thumb_path)
                    else:
                        cap = cv2.VideoCapture(video_path)
                        ret, frame = cap.read()
                        if ret:
                            cv2.imwrite(thumb_path, frame)
                        cap.release()
                
                pose_cache = os.path.join(project_dir, "pose_data.npy")
                if not os.path.exists(pose_cache):
                    legacy_pose = os.path.join(project_dir, video_filename + ".pose.npy")
                    if os.path.exists(legacy_pose):
                        pose_cache = legacy_pose
                
                disk_status = "completed" if os.path.exists(pose_cache) else "uploaded"
                t_state = self._transient_state.get(project_name, {})
                
                status = "completed" if disk_status == "completed" else t_state.get("status", disk_status)
                progress = 100 if disk_status == "completed" else t_state.get("progress", 0)
                fps = t_state.get("fps", project_data.get("fps", 30.0))
                total_frames = t_state.get("total_frames", project_data.get("total_frames", 0))

                # File size
                try:
                    size = os.path.getsize(video_path)
                    if size < 1024*1024: size_str = f"{size/1024:.2f} KB"
                    elif size < 1024*1024*1024: size_str = f"{size/(1024*1024):.2f} MB"
                    else: size_str = f"{size/(1024*1024*1024):.2f} GB"
                except: size_str = "Unknown"

                # Actual disk paths for backend (OpenCV, etc.)
                video_path = os.path.join(project_dir, video_filename)
                thumb_path = os.path.join(project_dir, "thumbnail.jpg")
                clips_dir = os.path.join(project_dir, "clips")
                
                # Ensure clips directory exists
                if not os.path.exists(clips_dir):
                    os.makedirs(clips_dir)

                # Web URLs for frontend (mapped via FastAPI mount)
                video_url = f"/uploads/{project_name}/{video_filename}"
                thumbnail_url = f"/uploads/{project_name}/thumbnail.jpg"

                video_info = {
                    "id": project_name, 
                    "name": project_name,
                    "filename": video_filename,
                    "file_size": size_str,
                    "path": video_path,
                    "url": video_url,
                    "project_dir": project_dir,
                    "clips_dir": clips_dir,
                    "thumbnail": thumb_path,
                    "thumbnail_url": thumbnail_url,
                    "status": status,
                    "progress": progress,
                    "refine_status": t_state.get("refine_status", "idle"),
                    "refine_progress": t_state.get("refine_progress", 0),
                    "fps": fps,
                    "total_frames": total_frames,
                    "pose_cache": pose_cache if disk_status == "completed" else None,
                    "keyframes": project_data.get("keyframes", []),
                    "slices": project_data.get("slices", []),
                    "analysis_cache": project_data.get("analysis_cache", None)
                }
                projects.append(video_info)
        
        projects.sort(key=lambda x: x['name'].lower())
        return projects

    def _get_clips_metadata_path(self, clips_dir):
        return os.path.join(clips_dir, "metadata.json")

    def _load_clips_metadata(self, clips_dir):
        path = self._get_clips_metadata_path(clips_dir)
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except: return {}
        return {}

    def _save_clip_metadata(self, clips_dir, filename, data):
        meta = self._load_clips_metadata(clips_dir)
        meta[filename] = data
        path = self._get_clips_metadata_path(clips_dir)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(meta, f, indent=4, ensure_ascii=False)

    def get_project_clips(self, video_id):
        video = self.get_video(video_id)
        if not video:
            return []
        
        clips_dir = video["clips_dir"]
        if not os.path.exists(clips_dir):
            return []
            
        metadata = self._load_clips_metadata(clips_dir)
        clips = []
        for filename in os.listdir(clips_dir):
            if filename.lower().endswith((".mp4", ".avi", ".mov", ".mkv")):
                path = os.path.join(clips_dir, filename)
                url = f"/uploads/{video_id}/clips/{filename}"
                size = os.path.getsize(path)
                clips.append({
                    "filename": filename,
                    "path": path,
                    "url": url,
                    "size": size,
                    "remarks": metadata.get(filename, {}).get("remarks", "")
                })
        
        # Sort clips by creation time (newest first)
        clips.sort(key=lambda x: os.path.getmtime(x["path"]), reverse=True)
        return clips
            
    def get_video(self, video_id):
        videos = self.list_videos()
        for v in videos:
            if v['id'] == video_id:
                return v
        return None
    
    def delete_video(self, video_id):
        project_dir = os.path.join(settings.UPLOAD_DIR, video_id)
        if os.path.exists(project_dir):
            shutil.rmtree(project_dir)
        
        if video_id in self._transient_state:
            del self._transient_state[video_id]
        return True
        
    def update_video(self, video_id, updates):
        # Update transient state for progress
        if video_id not in self._transient_state:
            self._transient_state[video_id] = {}
        self._transient_state[video_id].update(updates)

        # Update persistent project_data.json if needed
        # We only persist metadata like keyframes and slices here
        persist_fields = ["keyframes", "slices", "fps", "total_frames", "analysis_cache"]
        if any(f in updates for f in persist_fields):
            project_dir = os.path.join(settings.UPLOAD_DIR, video_id)
            if os.path.exists(project_dir):
                data = self._load_project_data(project_dir)
                for f in persist_fields:
                    if f in updates:
                        data[f] = updates[f]
                self._save_project_data(project_dir, data)

storage = Storage()
