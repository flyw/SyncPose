# SyncPose 🕺

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.95+-009688.svg)](https://fastapi.tiangolo.com/)

**SyncPose** is a high-precision pose alignment and similarity analysis system designed for AI digital human video production. It leverages MediaPipe's pose estimation to automatically find, align, and extract matching motion segments across video frames, ensuring seamless transitions and visual consistency.

## ✨ Key Features

- **🔄 Iterative Refinement Pipeline**: A node-based workflow where you can stack Spatial (MLS) and Temporal (RIFE) optimizations.
- **🎯 Real-time Frontend Calibration**: Uses MediaPipe in the browser to ensure the skeleton overlay is 100% perfectly aligned with the video pixels.
- **🧬 MLS Warp (Moving Least Squares)**: Mathematically rigorous pose alignment (via TPS) to fix "jumpy" transitions in loops.
- **🚀 RIFE Interpolation**: Local AI-powered frame interpolation for buttery smooth motion.
- **⚡ Pro Slicing Editor**: Frame-accurate slicing tool with "📌 Pin current frame" and precision adjustment buttons.
- **🖥️ Modern Dashboard**: A dark-themed SPA for managing multiple video projects and clip iterations.
- **📦 Fully Localized**: All AI models and JS libraries run locally for high performance and privacy.

## 🚀 Quick Start

### Prerequisites

- **Conda** (Miniconda or Anaconda)
- **NVIDIA GPU** (RTX 30/40/50 series recommended for RIFE inference)
- **FFmpeg** (system-wide installation for video processing)

### Installation & Environment Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/SyncPose.git
   cd SyncPose
   ```

2. **Create and activate Conda environment:**
   ```bash
   conda create -n syncpose python=3.10 -y
   conda activate syncpose
   ```

3. **Install PyTorch (CUDA 12.1+ compatible):**
   *Recommended for high-end GPUs like RTX 5080:*
   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
   ```

4. **Install other dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Download AI Models & Libraries:**
   Run the included script to download MediaPipe models and assets:
   ```bash
   ./download_models.sh
   ```

### Usage

1. **Launch the server:**
   ```bash
   python -m app.main
   ```

2. **Access the UI:**
   Open `http://localhost:8000` in Chrome/Edge.

3. **Refinement Workflow (Iterative):**
   - **Slicing**: Select action segments and click `✂️ Export Slice Video`.
   - **Refinement**: Select an exported clip from the "Project Clips" list.
   - **Apply MLS**: Choose "Spatial Alignment", set "Progressive Fade-out" (e.g., 15 frames) to align the end pose to the start pose.
   - **Apply RIFE**: Select the MLS-processed version and apply "Temporal Smoothing" for a seamless loop transition.

## 🛠️ Tech Stack

- **Backend**: FastAPI (Python 3.10+)
- **AI Engine**: MediaPipe Pose & Practical-RIFE (PyTorch)
- **Frontend**: Vanilla JS SPA + HTML5 Canvas
- **Video Processing**: OpenCV & FFmpeg
- **Data**: NumPy (Vector similarity & MLS calculations)

## 📁 Project Structure

```text
SyncPose/
├── app/                  # Python Backend (FastAPI)
│   ├── api/              # REST Endpoints (Resources, Slicing, Refinement)
│   ├── services/         # AI Logic (AlignmentService, PoseService)
│   └── main.py           # Server Entry Point
├── static/               # Frontend Assets
│   ├── js/pages/         # SPA Page Components (RefinementPage, etc.)
│   └── index.html        # Main Entry UI
├── download_models.sh    # Model setup script
├── requirements.txt      # Python dependencies
└── uploads/              # Project data storage (Videos, Keyframes, Clips)
```

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---
*Created with ❤️ for the Digital Human community.*
