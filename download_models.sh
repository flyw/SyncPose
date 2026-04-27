#!/bin/bash

# SyncPose Model Downloader
# This script downloads necessary AI models for MediaPipe (Pose/Holistic) and RIFE.

set -e

PROJECT_ROOT=$(pwd)
LIB_DIR="$PROJECT_ROOT/static/libs"
RIFE_DIR="$PROJECT_ROOT/static/models/rife"

mkdir -p "$LIB_DIR"
mkdir -p "$RIFE_DIR"

echo "=========================================="
echo "Step 1: Downloading MediaPipe Models"
echo "=========================================="

# 1. Backend Task Models (MediaPipe Tasks API)
wget -q --show-progress -O "$LIB_DIR/pose_landmarker.task" https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task
wget -q --show-progress -O "$LIB_DIR/holistic_landmarker.task" https://storage.googleapis.com/mediapipe-models/holistic_landmarker/holistic_landmarker/float16/1/holistic_landmarker.task

# 2. Frontend Legacy Models (MediaPipe Solutions JS - Raw TFLite format)
GCS_URL="https://storage.googleapis.com/mediapipe-assets"
wget -q --show-progress -O "$LIB_DIR/pose_landmark_full.tflite" "$GCS_URL/pose_landmark_full.tflite"
wget -q --show-progress -O "$LIB_DIR/face_detection_short_range.tflite" "$GCS_URL/face_detection_short_range.tflite"
wget -q --show-progress -O "$LIB_DIR/face_landmark.tflite" "$GCS_URL/face_landmark.tflite"
wget -q --show-progress -O "$LIB_DIR/hand_landmark_full.tflite" "$GCS_URL/hand_landmark_full.tflite"
wget -q --show-progress -O "$LIB_DIR/iris_landmark.tflite" "$GCS_URL/iris_landmark.tflite"

# 3. JS/WASM Runtime Assets
BASE_URL="https://cdn.jsdelivr.net/npm/@mediapipe/pose"
HOLISTIC_BASE_URL="https://cdn.jsdelivr.net/npm/@mediapipe/holistic"

wget -q --show-progress -O "$LIB_DIR/pose.js" "$BASE_URL/pose.js"
wget -q --show-progress -O "$LIB_DIR/holistic.js" "$HOLISTIC_BASE_URL/holistic.js"
wget -q --show-progress -O "$LIB_DIR/holistic_solution_packed_assets_loader.js" "$HOLISTIC_BASE_URL/holistic_solution_packed_assets_loader.js"
wget -q --show-progress -O "$LIB_DIR/holistic_solution_simd_wasm_bin.js" "$HOLISTIC_BASE_URL/holistic_solution_simd_wasm_bin.js"

wget -q --show-progress -O "$LIB_DIR/pose_solution_packed_assets.data" "$BASE_URL/pose_solution_packed_assets.data"
wget -q --show-progress -O "$LIB_DIR/pose_solution_simd_wasm_bin.wasm" "$BASE_URL/pose_solution_simd_wasm_bin.wasm"
wget -q --show-progress -O "$LIB_DIR/pose_web.binarypb" "$BASE_URL/pose_web.binarypb"

wget -q --show-progress -O "$LIB_DIR/holistic_solution_packed_assets.data" "$HOLISTIC_BASE_URL/holistic_solution_packed_assets.data"
wget -q --show-progress -O "$LIB_DIR/holistic_solution_simd_wasm_bin.wasm" "$HOLISTIC_BASE_URL/holistic_solution_simd_wasm_bin.wasm"

echo ""
echo "=========================================="
echo "Step 2: Downloading RIFE HDv3 Model"
echo "=========================================="

if [ -f "$RIFE_DIR/flownet.pkl" ]; then
    echo "✓ RIFE model already exists at $RIFE_DIR/flownet.pkl"
else
    echo "Downloading RIFE HDv3 model (~11MB)..."
    echo "Source: https://huggingface.co/aka7774/ECCV2022-RIFE"
    
    # Download the zip file
    wget -q --show-progress -O /tmp/RIFE_trained_model_v3.6.zip \
        "https://huggingface.co/aka7774/ECCV2022-RIFE/resolve/main/RIFE_trained_model_v3.6.zip"

    echo "Extracting RIFE model..."
    
    # Create temp extraction dir
    EXTRACT_DIR="/tmp/rife_extracted_$(date +%s)"
    mkdir -p "$EXTRACT_DIR"
    
    unzip -q -o /tmp/RIFE_trained_model_v3.6.zip -d "$EXTRACT_DIR"
    
    # Locate and copy pkl files (usually in train_log or root of zip)
    if [ -d "$EXTRACT_DIR/train_log" ]; then
        cp -r "$EXTRACT_DIR/train_log/"* "$RIFE_DIR/" 2>/dev/null || true
    else
        cp -r "$EXTRACT_DIR/"* "$RIFE_DIR/" 2>/dev/null || true
    fi
    
    # Cleanup
    rm -f /tmp/RIFE_trained_model_v3.6.zip
    rm -rf "$EXTRACT_DIR"
    
    echo "✓ RIFE model extraction completed."
fi

echo ""
echo "=========================================="
echo "✓ All models and assets are ready!"
echo "=========================================="
