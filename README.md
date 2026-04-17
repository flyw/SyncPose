# SyncPose 🕺

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.95+-009688.svg)](https://fastapi.tiangolo.com/)

**SyncPose** is a high-precision pose alignment and similarity analysis system designed for AI digital human video production. It leverages MediaPipe's pose estimation to automatically find, align, and extract matching motion segments across video frames, ensuring seamless transitions and visual consistency.

## ✨ Key Features

- **🎯 Real-time Frontend Calibration**: Uses MediaPipe in the browser to ensure the skeleton overlay is 100% perfectly aligned with the video pixels.
- **🧬 Intelligent Similarity Scoring**: Two-stage filtering logic that discards erratic frames (top 30% max deviation) and selects the most stable poses.
- **⚡ Pro Slicing Editor**: Frame-accurate slicing tool with "📌 Pin current frame" and precision adjustment buttons.
- **🖥️ Modern Dashboard**: A dark-themed SPA (Single Page Application) for managing multiple video projects.
- **💾 Smart Caching**: Automatically saves pose data to `.npy` files for lightning-fast reloading.
- **📦 Fully Localized**: All AI models and JS libraries are hosted locally for high performance and offline capability.

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- FFmpeg (for video clipping)
- Modern Browser (Chrome/Edge recommended)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/SyncPose.git
   cd SyncPose
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Download AI Models & Libraries:**
   Run the included script to download all necessary MediaPipe models and assets into the `static/libs` folder:
   ```bash
   ./download_models.sh
   ```

### Usage

1. **Launch the server:**
   ```bash
   python -m app.main
   ```

2. **Access the UI:**
   Open your browser and navigate to `http://localhost:8000`.

3. **Workflow:**
   - **Upload**: Add your digital human video clips.
   - **Analyze**: Extract pose features (GPU accelerated).
   - **Keyframe**: Select a standard baseline pose (Single selection mode).
   - **Slicing**: Define action segments with frame-by-frame precision.

## 🛠️ Tech Stack

- **Backend**: FastAPI (Python 3.9+)
- **AI Engine**: MediaPipe Pose (Tasks API & JS API)
- **Frontend**: Vanilla JS SPA + HTML5 Canvas
- **Video Processing**: OpenCV & FFmpeg
- **Data**: NumPy (Vector similarity calculations)

## 📁 Project Structure

```text
SyncPose/
├── app/                  # Python Backend (FastAPI)
│   ├── api/              # REST Endpoints
│   ├── services/         # Pose Analysis Logic
│   └── main.py           # Server Entry Point
├── static/               # Frontend Assets
│   ├── libs/             # MediaPipe & Model Files (Local)
│   ├── js/pages/         # SPA Page Components
│   └── index.html        # Main Entry UI
├── download_models.sh    # Model setup script
├── requirements.txt      # Python dependencies
└── uploads/              # Project data storage
```

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---
*Created with ❤️ for the Digital Human community.*
