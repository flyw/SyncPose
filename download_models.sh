#!/bin/bash

# SyncPose Model Downloader
# This script downloads the necessary MediaPipe models for both frontend and backend.

LIB_DIR="static/libs"
mkdir -p $LIB_DIR

echo "Downloading MediaPipe Pose Full Model..."
wget -O $LIB_DIR/pose_landmark_full.tflite https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task

echo "Creating backend task bundle..."
cp $LIB_DIR/pose_landmark_full.tflite $LIB_DIR/pose_landmarker.task

echo "Downloading MediaPipe WASM and Assets..."
# These are usually fetched by the library, but we can pre-download them for local serving
# URLs based on standard MediaPipe distribution
BASE_URL="https://cdn.jsdelivr.net/npm/@mediapipe/pose"

wget -O $LIB_DIR/pose_solution_packed_assets.data $BASE_URL/pose_solution_packed_assets.data
wget -O $LIB_DIR/pose_solution_simd_wasm_bin.wasm $BASE_URL/pose_solution_simd_wasm_bin.wasm
wget -O $LIB_DIR/pose_web.binarypb $BASE_URL/pose_web.binarypb

echo "Done! Models and assets are ready in $LIB_DIR"
