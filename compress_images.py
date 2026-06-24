# compress_images.py
import os
from PIL import Image
import sys

def compress_image(input_path, output_path, max_size_kb=300):
    """Compress image to be under max_size_kb"""
    try:
        # Open image
        img = Image.open(input_path)
        
        # Convert RGBA to RGB if necessary
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        
        # Initial quality
        quality = 95
        step = 5
        min_quality = 10
        
        # Get original size
        original_size = os.path.getsize(input_path) / 1024  # KB
        
        # If already under limit, just copy
        if original_size <= max_size_kb:
            if input_path != output_path:
                import shutil
                shutil.copy2(input_path, output_path)
            print(f"✓ {os.path.basename(input_path)}: Already {original_size:.1f}KB")
            return True
        
        # Try different quality settings
        while quality >= min_quality:
            # Save with current quality
            img.save(output_path, 'JPEG', quality=quality, optimize=True)
            
            # Check file size
            current_size = os.path.getsize(output_path) / 1024  # KB
            
            if current_size <= max_size_kb:
                print(f"✓ {os.path.basename(input_path)}: {original_size:.1f}KB → {current_size:.1f}KB (quality {quality})")
                return True
            
            # Reduce quality for next attempt
            quality -= step
        
        # If still too large, resize image
        print(f"⚠ {os.path.basename(input_path)}: Still {current_size:.1f}KB after quality reduction, resizing...")
        
        # Calculate scale factor
        scale_factor = (max_size_kb / current_size) ** 0.5
        new_width = int(img.width * scale_factor)
        new_height = int(img.height * scale_factor)
        
        # Resize and save with minimum quality
        resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        resized_img.save(output_path, 'JPEG', quality=min_quality, optimize=True)
        
        final_size = os.path.getsize(output_path) / 1024
        print(f"✓ {os.path.basename(input_path)}: {original_size:.1f}KB → {final_size:.1f}KB (resized + compressed)")
        return True
        
    except Exception as e:
        print(f"✗ Error processing {input_path}: {str(e)}")
        return False

def process_directory(directory, max_size_kb=300):
    """Process all images in directory"""
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
    
    # Get all image files
    image_files = []
    for file in os.listdir(directory):
        file_path = os.path.join(directory, file)
        if os.path.isfile(file_path):
            ext = os.path.splitext(file)[1].lower()
            if ext in image_extensions:
                image_files.append(file_path)
    
    if not image_files:
        print("No image files found!")
        return
    
    print(f"Found {len(image_files)} images to process\n")
    
    # Process each image
    processed = 0
    for img_path in image_files:
        # Create backup filename
        dir_name = os.path.dirname(img_path)
        base_name = os.path.basename(img_path)
        name, ext = os.path.splitext(base_name)
        
        # Save as compressed version (overwrite original)
        if compress_image(img_path, img_path, max_size_kb):
            processed += 1
    
    print(f"\n✓ Processed {processed}/{len(image_files)} images")

if __name__ == "__main__":
    # Set your media/posts directory
    media_dir = "/app/media/posts"
    
    if not os.path.exists(media_dir):
        print(f"Directory {media_dir} not found!")
        sys.exit(1)
    
    process_directory(media_dir, max_size_kb=300)