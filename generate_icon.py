#!/usr/bin/env python3
"""
Generate NEXUS app icon in Windows .ico format.

Creates:
- LeadExtractorPro.ico (multi-size Windows icon)
- LeadExtractorPro_icon.png (preview)

The icon features the NEXUS ◉ glyph (circle) with modern gradient styling.
"""
from PIL import Image, ImageDraw
import os

def create_nexus_icon(size: int) -> Image.Image:
    """Create NEXUS ◉ icon at given size."""
    # Create image with transparent background
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Margins
    margin = int(size * 0.1)
    
    # Outer circle (main)
    bbox = [margin, margin, size - margin, size - margin]
    
    # Color scheme: Modern purple/blue gradient
    # Center: bright cyan/blue (#00D9FF)
    # Outer: deeper purple (#7C3AED)
    center_color = (0, 217, 255, 255)      # Bright cyan
    outer_color = (124, 58, 237, 255)      # Purple
    
    # Draw outer circle (solid purple base)
    draw.ellipse(bbox, fill=outer_color, outline=outer_color)
    
    # Draw inner circle (bright center)
    inner_margin = int(size * 0.25)
    inner_bbox = [
        margin + inner_margin,
        margin + inner_margin,
        size - margin - inner_margin,
        size - margin - inner_margin
    ]
    draw.ellipse(inner_bbox, fill=center_color, outline=center_color)
    
    # Draw accent ring (creates depth)
    ring_margin = int(size * 0.18)
    ring_bbox = [
        margin + ring_margin,
        margin + ring_margin,
        size - margin - ring_margin,
        size - margin - ring_margin
    ]
    ring_width = int(size * 0.03)
    draw.ellipse(ring_bbox, outline=outer_color, width=ring_width)
    
    return img

def main():
    """Generate icon files."""
    print("🎨 Generating NEXUS icon...")
    
    # Windows .ico requires multiple sizes
    sizes = [256, 128, 64, 32, 16]
    
    # Create images for each size
    images = []
    for size in sizes:
        print(f"   Creating {size}x{size}...", end=" ")
        img = create_nexus_icon(size)
        images.append(img)
        print("✓")
    
    # Save as .ico (Windows format - stores all sizes)
    ico_path = "LeadExtractorPro.ico"
    print(f"\n📦 Saving {ico_path}...", end=" ")
    images[0].save(
        ico_path,
        format="ICO",
        sizes=[(img.size[0], img.size[1]) for img in images]
    )
    print("✓")
    
    # Also save preview PNG at 256x256
    png_path = "LeadExtractorPro_icon.png"
    print(f"📸 Saving preview {png_path}...", end=" ")
    images[0].save(png_path, format="PNG")
    print("✓")
    
    print(f"\n✅ Done!")
    print(f"   {ico_path} - Use this in LeadExtractorPro_windows.spec")
    print(f"   {png_path} - Preview (for documentation, etc.)")
    print(f"\nNext: Update LeadExtractorPro_windows.spec:")
    print(f"   icon='LeadExtractorPro.ico'")
    print(f"And rebuild:")
    print(f"   python -m PyInstaller --clean --noconfirm LeadExtractorPro_windows.spec")

if __name__ == "__main__":
    main()
