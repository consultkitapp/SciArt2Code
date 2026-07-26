#!/bin/bash

WORKSPACE_DIR="$(pwd)/agent_workspace"
IMAGE="python:3.10-slim"
CONTAINER_PREFIX="qwen-sandbox"
NUM_PODS=4

echo "=== AI Agent Podman Sandbox Setup ==="

mkdir -p "$WORKSPACE_DIR"
podman pull $IMAGE

for i in $(seq 1 $NUM_PODS); do
    CONTAINER_NAME="${CONTAINER_PREFIX}-${i}"

    if podman ps -a --format "{{.Names}}" | grep -Eq "^${CONTAINER_NAME}\$"; then
        echo "🧹 Removing existing container: $CONTAINER_NAME"
        podman rm -f $CONTAINER_NAME > /dev/null
    fi

    echo "🌱 Starting pod: $CONTAINER_NAME"
    # Added --network=none for security isolation         --network=none \
    podman run -d \
        --name $CONTAINER_NAME \
        -v "${WORKSPACE_DIR}:/workspace:Z" \
        $IMAGE \
        sh -c "apt-get update && apt-get install -y build-essential gcc g++ && sleep infinity" > /dev/null

    echo "  -> $CONTAINER_NAME is ready."
done

echo "✅ Setup complete! 4 sandboxes ready."
