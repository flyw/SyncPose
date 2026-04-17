from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import resources, keyframes, slicing, analysis
from app.core.config import settings

from fastapi.responses import FileResponse
import os

app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(resources.router, prefix="/api/v1/resources", tags=["resources"])
app.include_router(keyframes.router, prefix="/api/v1/keyframes", tags=["keyframes"])
app.include_router(slicing.router, prefix="/api/v1/slicing", tags=["slicing"])
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["analysis"])

app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

@app.get("/")
async def root():
    return FileResponse(os.path.join(settings.STATIC_DIR, "index.html"))

if __name__ == "__main__":
    import uvicorn
    # The server now starts without a pre-defined video. 
    # Users upload and manage videos through the web interface.
    uvicorn.run(app, host="0.0.0.0", port=8000)
