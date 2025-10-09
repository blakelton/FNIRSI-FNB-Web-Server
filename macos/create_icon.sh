#!/bin/bash
# Create macOS .icns icon from SVG

cd "$(dirname "$0")"

# Check if we have rsvg-convert (from librsvg)
if ! command -v rsvg-convert &> /dev/null; then
    echo "Installing librsvg for SVG conversion..."
    brew install librsvg
fi

echo "🎨 Creating app icon..."

# Create iconset directory
mkdir -p icon.iconset

# Generate all required icon sizes
sizes=(16 32 128 256 512)
for size in "${sizes[@]}"; do
    echo "  Creating ${size}x${size} icon..."
    rsvg-convert -w $size -h $size icon.svg > "icon.iconset/icon_${size}x${size}.png"

    # Create @2x versions
    size2x=$((size * 2))
    rsvg-convert -w $size2x -h $size2x icon.svg > "icon.iconset/icon_${size}x${size}@2x.png"
done

# Create 1024x1024 for Retina
echo "  Creating 1024x1024 icon..."
rsvg-convert -w 1024 -h 1024 icon.svg > "icon.iconset/icon_512x512@2x.png"

# Convert iconset to icns
echo "  Converting to .icns format..."
iconutil -c icns icon.iconset -o icon.icns

echo "✅ Icon created: icon.icns"
ls -lh icon.icns
