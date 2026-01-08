#!/bin/bash

# Configuration - Change these if paths move
MODEL_PATH="/home/aharon/.lmstudio/models/Qwen/Qwen2.5-Coder-32B-Instruct-GGUF/qwen2.5-coder-32b-instruct-q4_0.gguf"
ENV_NAME="muscular_env"
PORT=1234

echo "--- Harmony AI Engine Startup ---"

# 1. Kill existing sessions
echo "[1/4] Cleaning VRAM..."
pkill -9 -f vllm || true

# 2. Verify Environment
echo "[2/4] Checking environment: $ENV_NAME"
if ! mamba env list | grep -q "$ENV_NAME"; then
    echo "ERROR: $ENV_NAME not found. Please run your install script first."
    exit 1
fi

# 3. Launch Server
echo "[3/4] Starting vLLM Server on Port $PORT..."
echo "Using Model: $MODEL_PATH"

mamba run -n $ENV_NAME vllm serve "$MODEL_PATH" \
    --tokenizer Qwen/Qwen2.5-Coder-32B-Instruct \
    --host 0.0.0.0 \
    --port $PORT \
    --max-model-len 16384 \
    --gpu-memory-utilization 0.9 \
    --enforce-eager \
    --served-model-name "harmony-qwen-32b"