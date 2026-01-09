#!/bin/bash
# 1. Install Ollama if not present
if ! command -v ollama &> /dev/null; then
    curl -fsSL https://ollama.com/install.sh | sh
fi

# 2. Point to your existing LM Studio file
MODEL_PATH="/home/aharon/.lmstudio/models/Qwen/Qwen2.5-Coder-32B-Instruct-GGUF/qwen2.5-coder-32b-instruct-q4_0.gguf"

# 3. Create a 'Modelfile' for Git tracking
echo "FROM $MODEL_PATH" > Modelfile
echo "PARAMETER num_ctx 16384" >> Modelfile
echo "PARAMETER num_gpu 99" >> Modelfile

# 4. Register the model in Ollama
ollama create harmony-coder -f Modelfile
rm Modelfile
echo "Prototype model 'harmony-coder' is ready."