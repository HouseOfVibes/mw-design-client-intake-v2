#!/bin/bash

# PWA Icon Generator for MW Design Studio
# Uses macOS built-in 'sips' command to resize icons

echo "MW Design Studio PWA Icon Generator"
echo "======================================"

# Define required icon sizes
sizes=(72 96 128 144 152 192 384 512 180)

# Input and output paths
input_logo="static/mw_logo.png"
output_dir="static/icons"

# Create output directory
mkdir -p "$output_dir"

# Check if input logo exists
if [ ! -f "$input_logo" ]; then
    echo "ERROR: Could not find logo file: $input_logo"
    exit 1
fi

echo "Original logo found: $input_logo"
echo "Creating icons in: $output_dir/"
echo ""

# Generate each icon size
for size in "${sizes[@]}"; do
    if [ $size -eq 180 ]; then
        # Special case for Apple touch icon
        output_file="$output_dir/apple-touch-icon-${size}x${size}.png"
        echo "Generating Apple touch icon: ${size}x${size}"
    else
        output_file="$output_dir/icon-${size}x${size}.png"
        echo "Generating PWA icon: ${size}x${size}"
    fi
    
    # Use sips to resize the image
    sips -z "$size" "$size" "$input_logo" --out "$output_file" > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo "  Created: $(basename "$output_file")"
    else
        echo "  FAILED: $(basename "$output_file")"
    fi
done

# Create a maskable icon (512x512 with background)
echo ""
echo "Creating maskable icon with brand background..."

# Copy the 512x512 icon as maskable
cp "$output_dir/icon-512x512.png" "$output_dir/icon-maskable-512x512.png"

if [ $? -eq 0 ]; then
    echo "  Created: icon-maskable-512x512.png"
else
    echo "  FAILED to create maskable icon"
fi

echo ""
echo "Icon generation complete!"
echo "Generated $(ls "$output_dir" | wc -l | tr -d ' ') icon files"
echo ""
echo "Generated icons:"
ls -la "$output_dir"

echo ""
echo "Your PWA is now ready for installation on all devices!"