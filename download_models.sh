#!/bin/bash

# SyncPose Model Downloader
# This script downloads the necessary MediaPipe models for both frontend and backend.

LIB_DIR="static/libs"
mkdir -p $LIB_DIR

echo "Downloading MediaPipe Models..."
# 1. Backend Task Models (MediaPipe Tasks API - ZIP/Bundle format)
# These are for the Python AlignmentService
wget -O $LIB_DIR/pose_landmarker.task https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task
wget -O $LIB_DIR/holistic_landmarker.task https://storage.googleapis.com/mediapipe-models/holistic_landmarker/holistic_landmarker/float16/1/holistic_landmarker.task

# 2. Frontend Legacy Models (MediaPipe Solutions JS - Raw TFLite format)
# These are for pose.js and holistic.js in the browser. 
# We use dedicated URLs to ensure we get the UNBUNDLED .tflite files.
GCS_URL="https://storage.googleapis.com/mediapipe-assets"

wget -O $LIB_DIR/pose_landmark_full.tflite $GCS_URL/pose_landmark_full.tflite
wget -O $LIB_DIR/face_detection_short_range.tflite $GCS_URL/face_detection_short_range.tflite
wget -O $LIB_DIR/face_landmark.tflite $GCS_URL/face_landmark.tflite
wget -O $LIB_DIR/hand_landmark_full.tflite $GCS_URL/hand_landmark_full.tflite
wget -O $LIB_DIR/iris_landmark.tflite $GCS_URL/iris_landmark.tflite

echo "Downloading MediaPipe WASM and Assets..."
# 3. JS/WASM Runtime Assets
BASE_URL="https://cdn.jsdelivr.net/npm/@mediapipe/pose"
HOLISTIC_BASE_URL="https://cdn.jsdelivr.net/npm/@mediapipe/holistic"

wget -O $LIB_DIR/pose.js $BASE_URL/pose.js
wget -O $LIB_DIR/holistic.js $HOLISTIC_BASE_URL/holistic.js
wget -O $LIB_DIR/holistic_solution_packed_assets_loader.js $HOLISTIC_BASE_URL/holistic_solution_packed_assets_loader.js
wget -O $LIB_DIR/holistic_solution_simd_wasm_bin.js $HOLISTIC_BASE_URL/holistic_solution_simd_wasm_bin.js

wget -O $LIB_DIR/pose_solution_packed_assets.data $BASE_URL/pose_solution_packed_assets.data
wget -O $LIB_DIR/pose_solution_simd_wasm_bin.wasm $BASE_URL/pose_solution_simd_wasm_bin.wasm
wget -O $LIB_DIR/pose_web.binarypb $BASE_URL/pose_web.binarypb

# Use the packed assets data which contains the graphs internally
wget -O $LIB_DIR/holistic_solution_packed_assets.data $HOLISTIC_BASE_URL/holistic_solution_packed_assets.data
wget -O $LIB_DIR/holistic_solution_simd_wasm_bin.wasm $HOLISTIC_BASE_URL/holistic_solution_simd_wasm_bin.wasm

echo "Done! Models and assets are ready in $LIB_DIR"
