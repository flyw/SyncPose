# SyncPose 🕺

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.95+-009688.svg)](https://fastapi.tiangolo.com/)

**SyncPose** is a professional-grade pose alignment and motion refinement system tailored for high-end AI digital human video production. By combining **MediaPipe's** precision with advanced mathematical warping (**MLS**) and temporal smoothing (**RIFE**), it transforms "jumpy" video loops into seamless, production-ready motion assets.

---

## ✨ Core Innovations

### 🔄 Iterative Refinement Pipeline
A non-destructive workflow allowing multiple optimization passes. Each "refined" clip can be used as the input for the next stage, enabling a "Slicing -> MLS Warp -> RIFE Smoothing" iterative chain.

### 🧬 Enhanced MLS Warp (Moving Least Squares)
Uses advanced mathematical algorithms to spatially deform video frames. This allows motion segments to perfectly match a global "Keyframe" pose.
- **Progressive Mode**: Configurable fade-in/out windows for surgical transition control.
- **Global Bridge Mode**: Smooth linear interpolation across the entire video. Anchors both start and end frames to the target pose for perfect seamless loops.
- **Rigid Hand Stabilization**: Specialized logic for Holistic-543 that treats hands as rigid bodies. Prevents "spaghetti" distortions while maintaining pixel-perfect facial and pose alignment.

### 👁️ Pro Visualization Tools
- **Live Warp Preview**: Instantly generate and overlay a warped frame to compare against target poses.
- **MLS Grid Overlay**: Toggleable deformation grid to visualize the spatial warping intensity.
- **Dual-Layer Opacity**: Independent opacity controls for Keyframe references and Warp previews.

### 🌀 Temporal Smoothing (RIFE)
Integrates the RIFE (Real-Time Intermediate Flow Estimation) AI model to eliminate velocity "jumps" in motion loops.
- **AI Interpolation**: Generates smooth transition frames between the video and the anchor pose.
- **Configurable Smoothing**: Adjustable interpolation factor (up to 32x) for ultra-fluid motion.
- **English-First Monitoring**: Standardized English status messages for clear cross-platform progress tracking.
- **Auto-Alignment**: Automatic color and spatial alignment of reference frames before interpolation.

### 🚀 Dual-Stream Export System
- **Web-Optimized Preview**: Fast, lightweight H.264 exports for instant browser playback and iteration.
- **HQ Production Master**: Lossless, all-intra (GOP=1) "All-Keyframe" masters (suffix `_hq.mp4`) for professional post-production grade quality.

### ⚡ Smart UI & Monitoring
- **Real-time Progress**: Frame-by-frame progress tracking with percentage and status updates.
- **Unified Controls**: Integrated Playback, Skeleton, and Loop controls across all pages.

---

## 🛠️ Architecture & Workflow

### How it works:
1.  **Analyze**: Extract 33 (Pose) or 543 (Holistic) landmarks from your source.
2.  **Keyframe**: Set a global "anchor pose" that every action should return to.
3.  **Slice**: Identify specific motion segments with frame-accurate precision.
4.  **Align (MLS)**: Use Bridge or Progressive warping to force alignment with the anchor.
5.  **Smooth (RIFE)**: Interpolate frames to eliminate any remaining velocity gaps.

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
├── download_models.sh    # Unified downloader for MediaPipe & RIFE models
└── uploads/              # Project persistence layer
```

## 📜 License
MIT License. Created for the Digital Human community.
