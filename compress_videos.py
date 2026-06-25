# compress_videos.py
import os
import subprocess
import sys
from pathlib import Path
import json
import tempfile

def get_video_info(file_path):
    """Get video file information using ffprobe"""
    try:
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data
        return None
    except Exception as e:
        print(f"Error getting video info: {e}")
        return None

def get_video_duration(file_path):
    """Get video duration in seconds"""
    info = get_video_info(file_path)
    if info and 'format' in info and 'duration' in info['format']:
        return float(info['format']['duration'])
    return None

def compress_video(input_path, output_path, max_size_mb=600, target_quality=23):
    """
    Compress video to be under max_size_mb
    Uses H.264 encoding with CRF (Constant Rate Factor)
    """
    try:
        # Get original file size
        original_size_mb = os.path.getsize(input_path) / (1024 * 1024)
        
        # If already under limit, just copy
        if original_size_mb <= max_size_mb:
            import shutil
            shutil.copy2(input_path, output_path)
            print(f"✓ {os.path.basename(input_path)}: Already {original_size_mb:.1f}MB")
            return True
        
        # Get video duration
        duration = get_video_duration(input_path)
        if not duration:
            print(f"⚠ Could not get duration for {os.path.basename(input_path)}")
            return False
        
        # Calculate target bitrate
        # Target size in bits, leaving 5% margin
        target_size_bits = (max_size_mb * 0.95) * 1024 * 1024 * 8
        target_bitrate = int(target_size_bits / duration)
        
        # Ensure minimum bitrate (for quality)
        min_bitrate = 500000  # 500 kbps
        max_bitrate = 5000000  # 5 Mbps
        
        if target_bitrate < min_bitrate:
            target_bitrate = min_bitrate
            print(f"⚠ {os.path.basename(input_path)}: Very long video, using minimum bitrate")
        elif target_bitrate > max_bitrate:
            target_bitrate = max_bitrate
        
        # Try multiple compression strategies
        strategies = [
            # Strategy 1: Two-pass encoding with calculated bitrate
            {
                'name': 'Two-pass VBR',
                'cmd': [
                    'ffmpeg',
                    '-i', input_path,
                    '-c:v', 'libx264',
                    '-b:v', f'{target_bitrate}',
                    '-maxrate', f'{int(target_bitrate * 1.5)}',
                    '-bufsize', f'{int(target_bitrate * 2)}',
                    '-preset', 'medium',
                    '-profile:v', 'high',
                    '-level', '4.1',
                    '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac',
                    '-b:a', '128k',
                    '-movflags', '+faststart',
                    '-y',
                    output_path
                ]
            },
            # Strategy 2: CRF encoding
            {
                'name': 'CRF',
                'cmd': [
                    'ffmpeg',
                    '-i', input_path,
                    '-c:v', 'libx264',
                    '-crf', str(target_quality),
                    '-preset', 'medium',
                    '-profile:v', 'high',
                    '-level', '4.1',
                    '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac',
                    '-b:a', '128k',
                    '-movflags', '+faststart',
                    '-y',
                    output_path
                ]
            },
            # Strategy 3: More aggressive compression
            {
                'name': 'Aggressive',
                'cmd': [
                    'ffmpeg',
                    '-i', input_path,
                    '-c:v', 'libx264',
                    '-crf', str(target_quality + 5),
                    '-preset', 'slow',
                    '-profile:v', 'high',
                    '-level', '4.1',
                    '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac',
                    '-b:a', '96k',
                    '-movflags', '+faststart',
                    '-y',
                    output_path
                ]
            }
        ]
        
        # Try each strategy
        for strategy in strategies:
            print(f"  Trying {strategy['name']}...")
            
            # Run FFmpeg
            result = subprocess.run(
                strategy['cmd'],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"  ✗ {strategy['name']} failed: {result.stderr[-200:]}")
                continue
            
            # Check if output exists and is under limit
            if os.path.exists(output_path):
                compressed_size_mb = os.path.getsize(output_path) / (1024 * 1024)
                if compressed_size_mb <= max_size_mb:
                    reduction = (original_size_mb - compressed_size_mb) / original_size_mb * 100
                    print(f"✓ {os.path.basename(input_path)}: {original_size_mb:.1f}MB → {compressed_size_mb:.1f}MB ({reduction:.1f}% reduction) [{strategy['name']}]")
                    return True
                else:
                    print(f"  ✗ {strategy['name']} result: {compressed_size_mb:.1f}MB (still too large)")
                    # Keep the file for next strategy
                    os.remove(output_path)
        
        # If all strategies fail, try resizing
        print(f"⚠ {os.path.basename(input_path)}: All compression strategies failed, trying resize...")
        
        # Get video dimensions
        info = get_video_info(input_path)
        if info and 'streams' in info:
            for stream in info['streams']:
                if stream['codec_type'] == 'video':
                    width = int(stream['width'])
                    height = int(stream['height'])
                    
                    # Calculate scale factor to reduce size
                    scale_factor = (max_size_mb / (original_size_mb * 1.2)) ** 0.5
                    new_width = int(width * scale_factor)
                    new_height = int(height * scale_factor)
                    
                    # Ensure minimum dimensions
                    if new_width < 320:
                        new_width = 320
                        new_height = int(320 * height / width)
                    
                    # Ensure width is even
                    new_width = new_width if new_width % 2 == 0 else new_width - 1
                    new_height = new_height if new_height % 2 == 0 else new_height - 1
                    
                    resize_cmd = [
                        'ffmpeg',
                        '-i', input_path,
                        '-c:v', 'libx264',
                        '-crf', str(target_quality + 3),
                        '-preset', 'medium',
                        '-vf', f'scale={new_width}:{new_height}',
                        '-profile:v', 'high',
                        '-level', '4.1',
                        '-pix_fmt', 'yuv420p',
                        '-c:a', 'aac',
                        '-b:a', '96k',
                        '-movflags', '+faststart',
                        '-y',
                        output_path
                    ]
                    
                    result = subprocess.run(resize_cmd, capture_output=True, text=True)
                    if result.returncode == 0 and os.path.exists(output_path):
                        compressed_size_mb = os.path.getsize(output_path) / (1024 * 1024)
                        if compressed_size_mb <= max_size_mb:
                            reduction = (original_size_mb - compressed_size_mb) / original_size_mb * 100
                            print(f"✓ {os.path.basename(input_path)}: {original_size_mb:.1f}MB → {compressed_size_mb:.1f}MB ({reduction:.1f}% reduction) [Resized]")
                            return True
                    
                    break
        
        # If still not successful, copy original
        print(f"✗ {os.path.basename(input_path)}: Failed to compress to under {max_size_mb}MB")
        import shutil
        shutil.copy2(input_path, output_path)
        return False
        
    except Exception as e:
        print(f"✗ Error processing {input_path}: {str(e)}")
        return False

def process_video_directory(directory, max_size_mb=600):
    """Process all videos in directory"""
    video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv'}
    
    # Get all video files
    video_files = []
    for file in os.listdir(directory):
        file_path = os.path.join(directory, file)
        if os.path.isfile(file_path):
            ext = os.path.splitext(file)[1].lower()
            if ext in video_extensions:
                file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                if file_size_mb > max_size_mb:
                    video_files.append((file_path, file_size_mb))
    
    if not video_files:
        print("No video files larger than 600MB found!")
        return
    
    print(f"Found {len(video_files)} videos to process (larger than {max_size_mb}MB)\n")
    
    # Sort by size (largest first)
    video_files.sort(key=lambda x: x[1], reverse=True)
    
    # Process each video
    processed = 0
    successful = 0
    total_original_size = 0
    total_compressed_size = 0
    
    for file_path, original_size in video_files:
        total_original_size += original_size
        
        # Create temp output path
        dir_name = os.path.dirname(file_path)
        base_name = os.path.basename(file_path)
        name, ext = os.path.splitext(base_name)
        
        # Use temporary file first, then replace
        temp_path = os.path.join(dir_name, f"_temp_{base_name}")
        
        print(f"\n📹 Processing: {base_name} ({original_size:.1f}MB)")
        
        if compress_video(file_path, temp_path, max_size_mb):
            # Replace original with compressed
            os.remove(file_path)
            os.rename(temp_path, file_path)
            
            compressed_size = os.path.getsize(file_path) / (1024 * 1024)
            total_compressed_size += compressed_size
            
            if compressed_size <= max_size_mb:
                successful += 1
            processed += 1
        else:
            # Clean up temp file if it exists
            if os.path.exists(temp_path):
                os.remove(temp_path)
            total_compressed_size += original_size
    
    # Summary
    total_reduction = ((total_original_size - total_compressed_size) / total_original_size * 100) if total_original_size > 0 else 0
    
    print("\n" + "="*60)
    print("📊 COMPRESSION SUMMARY")
    print("="*60)
    print(f"Total videos processed: {processed}")
    print(f"Successfully compressed: {successful}")
    print(f"Failed to compress: {processed - successful}")
    print(f"Original total size: {total_original_size:.1f}MB")
    print(f"Compressed total size: {total_compressed_size:.1f}MB")
    print(f"Total reduction: {total_reduction:.1f}%")
    print("="*60)

if __name__ == "__main__":
    # Set your video directory
    video_dir = "/app/media/posts/videos"
    
    if not os.path.exists(video_dir):
        print(f"Directory {video_dir} not found!")
        sys.exit(1)
    
    # Process videos over 600MB
    process_video_directory(video_dir, max_size_mb=600)