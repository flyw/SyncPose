import os

class Settings:
    PROJECT_NAME: str = "SyncPose"
    UPLOAD_DIR: str = "uploads"
    STATIC_DIR: str = "static"
    CLIPS_DIR: str = os.path.join(STATIC_DIR, "clips")
    MODEL_PATH: str = os.path.join(STATIC_DIR, "libs", "pose_landmarker.task")

settings = Settings()

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.CLIPS_DIR, exist_ok=True)
