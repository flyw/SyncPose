#!/bin/bash
# Download RIFE HDv3 pre-trained model
# Model source: https://huggingface.co/aka7774/ECCV2022-RIFE

set -e

echo "=========================================="
echo "Downloading RIFE HDv3 Pre-trained Model"
echo "=========================================="
echo ""

# Create model directory
MODEL_DIR="static/models/rife"
mkdir -p "$MODEL_DIR"

# Check if model already exists
if [ -f "$MODEL_DIR/flownet.pkl" ]; then
    echo "✓ Model already exists at $MODEL_DIR/flownet.pkl"
    echo "  Skipping download."
    exit 0
fi

# Download from HuggingFace
echo "Downloading RIFE HDv3 model (~11MB)..."
echo "Source: https://huggingface.co/aka7774/ECCV2022-RIFE"
echo ""

# Download the zip file
wget -q --show-progress -O /tmp/RIFE_trained_model_v3.6.zip \
    "https://huggingface.co/aka7774/ECCV2022-RIFE/resolve/main/RIFE_trained_model_v3.6.zip"

echo ""
echo "Extracting model..."

# Extract
cd /tmp
unzip -q -o RIFE_trained_model_v3.6.zip

# Copy model files to our directory
if [ -d "train_log" ]; then
    cp -r train_log/* "$MODEL_DIR/" 2>/dev/null || true
    echo "✓ Model files extracted to $MODEL_DIR/"
else
    # Try alternative extraction
    unzip -q -o /tmp/RIFE_trained_model_v3.6.zip -d /tmp/rife_extracted/
    if [ -d "/tmp/rife_extracted/train_log" ]; then
        cp -r /tmp/rife_extracted/train_log/* "$MODEL_DIR/" 2>/dev/null || true
        echo "✓ Model files extracted to $MODEL_DIR/"
    else
        echo "❌ Failed to extract model files"
        exit 1
    fi
fi

# Cleanup
rm -f /tmp/RIFE_trained_model_v3.6.zip
rm -rf /tmp/train_log
rm -rf /tmp/rife_extracted

echo ""
echo "=========================================="
echo "✓ Model download completed!"
echo "=========================================="
echo ""
echo "Model location: $MODEL_DIR/"
ls -lh "$MODEL_DIR/" 2>/dev/null || true
