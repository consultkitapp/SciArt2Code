#!/bin/bash

# 1. Configuration
bash setup_sandboxes.sh

# 2. Start the Orchestrator/Coder Model (Port 8080)
# Uses ~30GB VRAM, offloads automatically across GPUs
echo "Starting Orchestrator Model Server on port 8080..."
./llama-server \
  -m ./agent_workspace/models/Qwen3.6-35B-A3B-GGUF/Qwen3.6-35B-A3B-Q6_K.gguf \
  -c 200000 \
  -ngl 99 \
  --port 8080 > orchestrator.log 2>&1 &

# 3. Start the Child Agent Model (Port 8081)
# Uses ~10GB VRAM, fits in remaining GPU space
echo "Starting Child Agent Model Server on port 8081..."
./llama-server \
  -m ./agent_workspace/models/Qwen3.5-9B-GGUF/Qwen3.5-9B-Q8_0.gguf \
  -c 65736 \
  -ngl 99 \
  --port 8081 > agents.log 2>&1 &

echo "Servers are booting. Check orchestrator.log and agents.log for status."
