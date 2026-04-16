# SyncPose 🕺

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.95+-009688.svg)](https://fastapi.tiangolo.com/)

**SyncPose** is a high-precision pose alignment and similarity analysis system designed for AI digital human video production. It leverages MediaPipe's pose estimation to automatically find, align, and extract matching motion segments across video frames, ensuring seamless transitions and visual consistency.

![Preview](https://via.placeholder.com/800x450.png?text=SyncPose+Interface+Preview)

## ✨ Key Features

- **🎯 High-Precision Scoring**: Intelligent similarity algorithm with custom weights (Head: 40%, Hands: 30%, Arms: 20%) to ensure core posture alignment.
- **⚡ GPU Acceleration**: Powered by MediaPipe Tasks API for ultra-fast feature extraction (optimized for modern GPUs like RTX 40/50 series).
- **🖥️ Pro Web Interface**: A modern, dark-themed dashboard for real-time video preview, skeletal overlay, and manual baseline adjustment.
- **🔍 Robust Average Pose**: Automatically calculates an "Ideal Pose" from stable frames to serve as a digital human benchmark.
- **🎬 One-Click Clipping**: Integrated FFmpeg support to instantly export perfectly aligned video segments.
- **💾 Smart Caching**: Automatically saves pose data to `.npy` files for lightning-fast reloading of previously analyzed videos.

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- FFmpeg (for video clipping)
- A modern GPU (optional, but highly recommended)

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
   *Note: Ensure you have `mediapipe`, `fastapi`, `uvicorn`, `opencv-python`, and `numpy` installed.*

3. **Download the AI Model:**
   SyncPose requires the MediaPipe Pose Landmarker model. Download the "Full" version (recommended) and place it in the project root:
   ```bash
   # Use wget to download the model
   wget -O pose_landmarker.task https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task
   ```
   *Note: You can also use the [Lite](https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task) version for speed or the [Heavy](https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/1/pose_landmarker_heavy.task) version for maximum precision.*

### Usage

1. **Launch the server:**
   ```bash
   python server.py --video your_video_path.mp4 --port 8000
   ```

2. **Access the UI:**
   Open your browser and navigate to `http://localhost:8000`.

3. **Workflow:**
   - **Analyze**: Wait for the system to complete feature extraction.
   - **Select Base**: Choose a recommended standard frame or manually capture a reference pose.
   - **Align**: Adjust the matching threshold and browse through similar frames in the timeline.
   - **Export**: Set the duration and export your aligned clips.

## 🛠️ Tech Stack

- **Backend**: FastAPI (Python)
- **AI Engine**: MediaPipe Pose Landmarker
- **Frontend**: Vanilla JS + CSS (High-performance Canvas rendering)
- **Video Processing**: OpenCV & FFmpeg
- **Data**: NumPy (for high-speed vector similarity calculations)

## 📁 Project Structure

```text
SyncPose/
├── server.py              # FastAPI backend & Analysis engine
├── pose_landmarker.task   # MediaPipe model file
├── static/                # Web interface assets
│   ├── index.html         # Main dashboard
│   └── clips/             # Exported video segments
├── resources/             # Static resources
└── optimize_4k.sh         # Optional processing scripts
```

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---
*Created with ❤️ for the Digital Human community.*
