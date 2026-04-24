# SyncPose 🕺

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.95+-009688.svg)](https://fastapi.tiangolo.com/)

**SyncPose** is a professional-grade pose alignment and motion refinement system tailored for high-end AI digital human video production. By combining **MediaPipe's** precision with advanced mathematical warping (**MLS**) and temporal smoothing (**RIFE**), it transforms "jumpy" video loops into seamless, production-ready motion assets.

---

## ✨ Core Innovations

### 🔄 Iterative Refinement Pipeline
A non-destructive workflow allowing multiple optimization passes. Each "refined" clip can be used as the input for the next stage, enabling a "Slicing -> MLS Warp -> RIFE Smoothing" iterative chain.

### 🧬 MLS Warp (Moving Least Squares)
Uses thin-plate spline (TPS) and MLS algorithms to spatially deform video frames. This allows the end of a clip to perfectly match the starting "Keyframe" pose, fixing joint misalignments that cause visual pops in loops.
- **MLS-33**: Standard pose alignment using 33 body landmarks.
- **Holistic-543**: Ultra-high precision alignment covering face (468 pts), pose (33 pts), and hands (42 pts) for seamless digital human facial expressions and gestures.

### 🚀 Local AI Engine
- **MediaPipe Tasks API**: Real-time browser-side calibration.
- **Holistic Integration**: Native support for 543-point holistic tracking in both UI and backend.
- **Practical-RIFE**: High-performance frame interpolation for buttery-smooth transitions.
- **Lossless Extraction**: Frame-level precision with PNG-0 compression to preserve every pixel.

### ⚡ Pro Slicing Editor
Frame-accurate timeline with "Pin current frame" functionality and instant slice exporting for rapid iteration.

---

## 🛠️ Architecture & Workflow

### How it works:
1.  **Analyze**: Extract 33 3D landmarks from your source video.
2.  **Keyframe**: Set a global "anchor pose" that every action should return to.
3.  **Slice**: Identify specific motion segments (e.g., a wave, a nod).
4.  **Align (MLS)**: Force the last few frames to "warp" towards the anchor pose.
5.  **Smooth (RIFE)**: Interpolate transition frames to eliminate velocity gaps.

---

## 🚀 Quick Start

### Prerequisites
- **OS**: Linux (Ubuntu 22.04+ recommended) or Windows 11.
- **GPU**: NVIDIA RTX 30/40/50 series (8GB+ VRAM required for RIFE).
- **Env**: Conda (Miniconda/Anaconda).

### Installation & Environment Setup

1.  **Clone & Enter:**
    ```bash
    git clone https://github.com/yourusername/SyncPose.git
    cd SyncPose
    ```

2.  **Conda Environment:**
    ```bash
    conda create -n syncpose python=3.10 -y
    conda activate syncpose
    ```

3.  **High-Performance PyTorch (CUDA 12.1+):**
    *Recommended for RTX 4090/5080 users:*
    ```bash
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
    ```

4.  **Dependencies & Assets:**
    ```bash
    pip install -r requirements.txt
    ./download_models.sh
    ```

### Usage

1.  **Start Backend:** `python -m app.main`
2.  **Open UI:** `http://localhost:8000` (Chrome/Edge highly recommended).

---

## 📁 Project Structure

```text
SyncPose/
├── app/                  # FastAPI Backend
│   ├── api/              # Refinement, Slicing, Keyframes logic
│   ├── services/         # Alignment (MLS/RIFE) & Pose logic
│   └── db/               # Local JSON/NumPy storage
├── static/               # Vanilla JS SPA
│   ├── js/pages/         # RefinementPage (Manual Tweak UI)
│   └── libs/             # Local MediaPipe binaries
├── download_models.sh    # Auto-downloader for AI models
└── uploads/              # Project persistence layer
```

## 📜 License
MIT License. Created for the Digital Human community.
