#!/usr/bin/env python3
"""
PWA Icon Generator for MW Design Studio
Generates all required PWA icon sizes from the main logo
"""

import os
from PIL import Image, ImageDraw

def create_icons():
    """Generate all PWA icon sizes from the main logo"""
    
    # Define required icon sizes for PWA
    icon_sizes = [72, 96, 128, 144, 152, 192, 384, 512]
    
    # Input and output paths
    input_logo = "static/mw_logo.png"
    output_dir = "static/icons"
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    print("MW Design Studio PWA Icon Generator")
    print("=" * 50)
    
    try:
        # Open the original logo
        with Image.open(input_logo) as original:
            print(f"Original logo loaded: {original.size}")
            
            # Convert to RGBA if not already
            if original.mode != 'RGBA':
                original = original.convert('RGBA')
            
            # Generate each required size
            for size in icon_sizes:
                # Create a square canvas with transparent background
                icon = Image.new('RGBA', (size, size), (0, 0, 0, 0))
                
                # Resize the logo maintaining aspect ratio
                logo_resized = original.copy()
                logo_resized.thumbnail((size - 20, size - 20), Image.Resampling.LANCZOS)
                
                # Center the logo on the canvas
                x = (size - logo_resized.width) // 2
                y = (size - logo_resized.height) // 2
                icon.paste(logo_resized, (x, y), logo_resized)
                
                # Save the icon
                filename = f"icon-{size}x{size}.png"
                filepath = os.path.join(output_dir, filename)
                icon.save(filepath, "PNG", optimize=True)
                
                print(f"  Generated {filename} ({size}x{size})")
            
            # Create special maskable icon (for Android)
            print("\nCreating maskable icon...")
            maskable_size = 512
            maskable = Image.new('RGBA', (maskable_size, maskable_size), (30, 58, 138, 255))  # MW brand color
            
            # Add logo to center with padding for safe area
            logo_masked = original.copy()
            safe_area = int(maskable_size * 0.6)  # 60% of the icon for safe area
            logo_masked.thumbnail((safe_area, safe_area), Image.Resampling.LANCZOS)
            
            x = (maskable_size - logo_masked.width) // 2
            y = (maskable_size - logo_masked.height) // 2
            maskable.paste(logo_masked, (x, y), logo_masked)
            
            # Save maskable icon
            maskable_path = os.path.join(output_dir, "icon-maskable-512x512.png")
            maskable.save(maskable_path, "PNG", optimize=True)
            print(f"  Generated icon-maskable-512x512.png")
            
            # Create Apple touch icon (180x180)
            apple_icon = Image.new('RGBA', (180, 180), (0, 0, 0, 0))
            logo_apple = original.copy()
            logo_apple.thumbnail((160, 160), Image.Resampling.LANCZOS)
            
            x = (180 - logo_apple.width) // 2
            y = (180 - logo_apple.height) // 2
            apple_icon.paste(logo_apple, (x, y), logo_apple)
            
            apple_path = os.path.join(output_dir, "apple-touch-icon-180x180.png")
            apple_icon.save(apple_path, "PNG", optimize=True)
            print(f"  Generated apple-touch-icon-180x180.png")
            
            print("\nAll PWA icons generated successfully!")
            print(f"Icons saved to: {output_dir}/")
            print(f"Total icons created: {len(icon_sizes) + 2}")
            
            return True
            
    except FileNotFoundError:
        print(f"ERROR: Could not find logo file: {input_logo}")
        return False
    except Exception as e:
        print(f"ERROR generating icons: {e}")
        return False

if __name__ == "__main__":
    success = create_icons()
    if success:
        print("\nYour PWA is now ready for installation on all devices!")
    else:
        print("\nIcon generation failed. Please check the error above.")