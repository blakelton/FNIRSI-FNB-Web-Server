#!/bin/bash
# Quick build script for FNIRSI FNB58 Monitor Docker image

set -e

echo "🐳 Building FNIRSI FNB58 Monitor Docker image..."
echo ""

# Get version from git tag or use 'latest'
VERSION=$(git describe --tags --abbrev=0 2>/dev/null || echo "latest")
IMAGE_NAME="fnb58-monitor"

echo "📦 Version: $VERSION"
echo "🏷️  Image: $IMAGE_NAME:$VERSION"
echo ""

# Build the image
docker build \
  -t $IMAGE_NAME:$VERSION \
  -t $IMAGE_NAME:latest \
  ..

echo ""
echo "✅ Build complete!"
echo ""
echo "Run with:"
echo "  docker-compose up -d"
echo ""
echo "Or:"
echo "  docker run -d -p 5000:5000 \\"
echo "    --device=/dev/bus/usb:/dev/bus/usb \\"
echo "    --privileged \\"
echo "    $IMAGE_NAME:latest"
