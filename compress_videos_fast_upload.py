# compress_videos_fast_upload.py
import os
import subprocess
import sys
import json
import shutil
from datetime import datetime

# Set FFmpeg paths (try common locations)
def get_ffmpeg_paths():
    """Find ffmpeg and ffprobe executables"""
    # Try common paths
    possible_paths = [
        '/usr/bin/ffmpeg',
        '/usr/local/bin/ffmpeg',
        '/bin/ffmpeg',
        'ffmpeg'  # Try system PATH
    ]
    
    possible_probe_paths = [
        '/usr/bin/ffprobe',
        '/usr/local/bin/ffprobe',
        '/bin/ffprobe',
        'ffprobe'  # Try system PATH
    ]
    
    ffmpeg_path = None
    ffprobe_path = None
    
    for path in possible_paths:
        try:
            result = subprocess.run([path, '-version'], capture_output=True, timeout=2)
            if result.returncode == 0:
                ffmpeg_path = path
                break
        except:
            continue
    
    for path in possible_probe_paths:
        try:
            result = subprocess.run([path, '-version'], capture_output=True, timeout=2)
            if result.returncode == 0:
                ffprobe_path = path
                break
        except:
            continue
    
    return ffmpeg_path, ffprobe_path

# Get FFmpeg paths
FFMPEG_PATH, FFPROBE_PATH = get_ffmpeg_paths()

if not FFMPEG_PATH or not FFPROBE_PATH:
    print("⚠️  FFmpeg not found! Please install FFmpeg:")
    print("   apt-get update && apt-get install -y ffmpeg")
    print("\nTrying to continue with system PATH...")
    FFMPEG_PATH = 'ffmpeg'
    FFPROBE_PATH = 'ffprobe'

print(f"Using FFmpeg: {FFMPEG_PATH}")
print(f"Using FFprobe: {FFPROBE_PATH}")
print("")

def get_video_info(file_path):
    """Get video file information using ffprobe"""
    try:
        cmd = [
            FFPROBE_PATH,
            '-v', 'quiet',
            '-print_format', 'json',
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
    try:
        cmd = [
            FFPROBE_PATH,
            '-v', 'quiet',
            '-show_format',
            '-print_format', 'json',
            file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            if 'format' in data and 'duration' in data['format']:
                return float(data['format']['duration'])
        return None
    except Exception as e:
        print(f"Error getting duration: {e}")
        return None

def is_vertical_video(file_path):
    """Check if video is vertical (portrait) orientation"""
    info = get_video_info(file_path)
    if info and 'streams' in info:
        for stream in info['streams']:
            if stream.get('codec_type') == 'video':
                width = int(stream.get('width', 0))
                height = int(stream.get('height', 0))
                if width > 0 and height > 0:
                    return height > width
    return False

def compress_video_fast_upload(input_path, output_path, target_mb=1.5, max_mb=2):
    """
    Compress video for fast upload (1-2 MB)
    Optimized for TikTok/Shorts style vertical videos
    """
    try:
        original_size_mb = os.path.getsize(input_path) / (1024 * 1024)
        
        # If already under max, just copy
        if original_size_mb <= max_mb:
            shutil.copy2(input_path, output_path)
            print(f"✓ {os.path.basename(input_path)}: Already {original_size_mb:.1f}MB (≤{max_mb}MB)")
            return True
        
        # Get video duration
        duration = get_video_duration(input_path)
        if not duration:
            print(f"⚠ Could not get duration for {os.path.basename(input_path)}, using default settings")
            duration = 30  # Assume 30 seconds as fallback
        
        # Check orientation
        is_vertical = is_vertical_video(input_path)
        orientation = "Vertical" if is_vertical else "Horizontal"
        print(f"  Orientation: {orientation}")
        
        # Calculate target bitrate for 1.5MB (with 10% margin)
        target_size_bits = (target_mb * 0.9) * 1024 * 1024 * 8
        target_bitrate = int(target_size_bits / duration)
        
        # Bitrate limits for fast upload
        min_bitrate = 300000   # 300 kbps minimum
        max_bitrate = 1500000  # 1.5 Mbps maximum
        
        if target_bitrate < min_bitrate:
            target_bitrate = min_bitrate
            print(f"  ⚠ Long video ({duration:.0f}s), using minimum bitrate")
        elif target_bitrate > max_bitrate:
            target_bitrate = max_bitrate
        
        print(f"  Duration: {duration:.1f}s")
        print(f"  Bitrate: {target_bitrate/1000:.1f} kbps")
        
        # Resolution based on duration and orientation (optimized for 1-2MB)
        if is_vertical:
            # Vertical video (TikTok/Shorts)
            if duration <= 15:      # Very short
                width, height = 540, 960
            elif duration <= 30:    # Short
                width, height = 480, 854
            elif duration <= 60:    # Medium
                width, height = 426, 758
            else:                   # Long
                width, height = 360, 640
        else:
            # Horizontal video
            if duration <= 15:
                width, height = 640, 360
            elif duration <= 30:
                width, height = 480, 270
            elif duration <= 60:
                width, height = 426, 240
            else:
                width, height = 320, 180
        
        # If bitrate is very low, reduce resolution more
        if target_bitrate < 500000:
            if is_vertical:
                width, height = 360, 640
            else:
                width, height = 320, 180
        
        print(f"  Resolution: {width}x{height}")
        
        # Fast compression strategies (prioritizing speed)
        strategies = [
            # Strategy 1: Fast CRF (balanced)
            {
                'name': 'Fast CRF',
                'cmd': [
                    FFMPEG_PATH,
                    '-i', input_path,
                    '-c:v', 'libx264',
                    '-crf', '28',
                    '-preset', 'veryfast',  # Fast encoding
                    '-profile:v', 'baseline',
                    '-level', '3.0',
                    '-vf', f'scale={width}:{height}',
                    '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac',
                    '-b:a', '64k',
                    '-ac', '1',  # Mono for smaller size
                    '-ar', '22050',  # 22kHz
                    '-movflags', '+faststart',
                    '-y',
                    output_path
                ]
            },
            # Strategy 2: Target bitrate (more predictable size)
            {
                'name': 'Target Bitrate',
                'cmd': [
                    FFMPEG_PATH,
                    '-i', input_path,
                    '-c:v', 'libx264',
                    '-b:v', f'{target_bitrate}',
                    '-maxrate', f'{int(target_bitrate * 1.2)}',
                    '-bufsize', f'{int(target_bitrate * 1.3)}',
                    '-preset', 'veryfast',
                    '-profile:v', 'baseline',
                    '-level', '3.0',
                    '-vf', f'scale={width}:{height}',
                    '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac',
                    '-b:a', '64k',
                    '-ac', '1',
                    '-ar', '22050',
                    '-movflags', '+faststart',
                    '-y',
                    output_path
                ]
            },
            # Strategy 3: Aggressive compression (for large files)
            {
                'name': 'Aggressive',
                'cmd': [
                    FFMPEG_PATH,
                    '-i', input_path,
                    '-c:v', 'libx264',
                    '-crf', '32',
                    '-preset', 'veryfast',
                    '-profile:v', 'baseline',
                    '-level', '2.0',
                    '-vf', f'scale={width//2}:{height//2}',
                    '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac',
                    '-b:a', '48k',
                    '-ac', '1',
                    '-ar', '16000',
                    '-movflags', '+faststart',
                    '-y',
                    output_path
                ]
            }
        ]
        
        # Try each strategy
        for strategy in strategies:
            print(f"  Trying {strategy['name']}...")
            
            try:
                start_time = datetime.now()
                result = subprocess.run(
                    strategy['cmd'],
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minutes timeout
                )
                elapsed = (datetime.now() - start_time).total_seconds()
                
                if result.returncode == 0 and os.path.exists(output_path):
                    compressed_size_mb = os.path.getsize(output_path) / (1024 * 1024)
                    if compressed_size_mb <= max_mb:
                        reduction = (original_size_mb - compressed_size_mb) / original_size_mb * 100
                        print(f"✓ {os.path.basename(input_path)}: {original_size_mb:.1f}MB → {compressed_size_mb:.1f}MB ({reduction:.1f}% reduction) [{strategy['name']}] ⏱{elapsed:.1f}s")
                        return True
                    else:
                        print(f"  ✗ Result: {compressed_size_mb:.1f}MB (still too large)")
                        if os.path.exists(output_path):
                            os.remove(output_path)
                else:
                    if os.path.exists(output_path):
                        os.remove(output_path)
                    if result.stderr:
                        error_msg = result.stderr[-150:] if len(result.stderr) > 150 else result.stderr
                        print(f"  ✗ Failed: {error_msg}")
                        
            except subprocess.TimeoutExpired:
                print(f"  ✗ Timed out after 5 minutes")
                if os.path.exists(output_path):
                    os.remove(output_path)
            except Exception as e:
                print(f"  ✗ Error: {e}")
                if os.path.exists(output_path):
                    os.remove(output_path)
        
        # Ultimate fallback: very low quality
        print(f"  Trying ultimate fallback...")
        
        fallback_cmd = [
            FFMPEG_PATH,
            '-i', input_path,
            '-c:v', 'libx264',
            '-crf', '35',
            '-preset', 'ultrafast',
            '-profile:v', 'baseline',
            '-level', '1.3',
            '-vf', f'scale=320:180',
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac',
            '-b:a', '32k',
            '-ac', '1',
            '-ar', '8000',
            '-movflags', '+faststart',
            '-y',
            output_path
        ]
        
        try:
            result = subprocess.run(fallback_cmd, capture_output=True, text=True, timeout=180)
            if result.returncode == 0 and os.path.exists(output_path):
                compressed_size_mb = os.path.getsize(output_path) / (1024 * 1024)
                if compressed_size_mb <= max_mb:
                    reduction = (original_size_mb - compressed_size_mb) / original_size_mb * 100
                    print(f"✓ {os.path.basename(input_path)}: {original_size_mb:.1f}MB → {compressed_size_mb:.1f}MB ({reduction:.1f}% reduction) [Fallback]")
                    return True
                else:
                    if os.path.exists(output_path):
                        os.remove(output_path)
        except Exception as e:
            print(f"  ✗ Fallback failed: {e}")
            if os.path.exists(output_path):
                os.remove(output_path)
        
        # If all fails, keep original
        print(f"✗ {os.path.basename(input_path)}: Failed to compress to under {max_mb}MB")
        shutil.copy2(input_path, output_path)
        return False
        
    except Exception as e:
        print(f"✗ Error processing {input_path}: {str(e)}")
        return False

def process_videos_fast(directory, target_mb=1.5, max_mb=2):
    """Process all videos in directory"""
    video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv', '.m4v'}
    
    # Get all video files
    video_files = []
    for file in os.listdir(directory):
        file_path = os.path.join(directory, file)
        if os.path.isfile(file_path) and not file.startswith('_temp_'):
            ext = os.path.splitext(file)[1].lower()
            if ext in video_extensions:
                file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                if file_size_mb > max_mb:
                    video_files.append((file_path, file_size_mb))
    
    if not video_files:
        print(f"✅ No video files larger than {max_mb}MB found!")
        print(f"   All videos are already optimized for fast upload!")
        return
    
    # Sort by size (largest first)
    video_files.sort(key=lambda x: x[1], reverse=True)
    
    print(f"🎬 FAST UPLOAD VIDEO COMPRESSOR")
    print(f"📁 Directory: {directory}")
    print("="*60)
    print(f"📊 Found {len(video_files)} videos larger than {max_mb}MB")
    print(f"🎯 Target: {target_mb}MB | 📏 Maximum: {max_mb}MB")
    print(f"⚡ Optimized for: Fast upload, mobile viewing")
    print("="*60)
    
    # Show files to be processed
    print("\n📹 Videos to compress:")
    for file_path, size in video_files[:5]:  # Show first 5
        print(f"   - {os.path.basename(file_path)} ({size:.1f}MB)")
    if len(video_files) > 5:
        print(f"   ... and {len(video_files) - 5} more")
    
    # Confirm
    response = input(f"\nContinue with compression? (y/n): ")
    if response.lower() != 'y':
        print("❌ Cancelled")
        return
    
    print("\n⚡ Processing...\n")
    
    processed = 0
    successful = 0
    total_original_mb = 0
    total_compressed_mb = 0
    total_time = 0
    
    for file_path, original_size_mb in video_files:
        total_original_mb += original_size_mb
        
        base_name = os.path.basename(file_path)
        temp_path = os.path.join(directory, f"_temp_{base_name}")
        
        print(f"\n📹 {base_name} ({original_size_mb:.1f}MB)")
        
        start_time = datetime.now()
        result = compress_video_fast_upload(file_path, temp_path, target_mb, max_mb)
        elapsed = (datetime.now() - start_time).total_seconds()
        total_time += elapsed
        
        if result:
            # Replace original with compressed
            os.remove(file_path)
            os.rename(temp_path, file_path)
            
            compressed_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            total_compressed_mb += compressed_size_mb
            
            if compressed_size_mb <= max_mb:
                successful += 1
            processed += 1
        else:
            # Clean up temp file if it exists
            if os.path.exists(temp_path):
                os.remove(temp_path)
            total_compressed_mb += original_size_mb
    
    # Summary
    if total_original_mb > 0:
        reduction = (total_original_mb - total_compressed_mb) / total_original_mb * 100
        
        print("\n" + "="*60)
        print("📊 COMPRESSION SUMMARY")
        print("="*60)
        print(f"✅ Videos processed: {processed}")
        print(f"✅ Successfully compressed: {successful}")
        print(f"❌ Failed to compress: {processed - successful}")
        print(f"📦 Original total: {total_original_mb:.1f}MB ({total_original_mb/1024:.2f}GB)")
        print(f"📦 Compressed total: {total_compressed_mb:.1f}MB ({total_compressed_mb/1024:.2f}GB)")
        print(f"📉 Total reduction: {reduction:.1f}%")
        print(f"💾 Space saved: {total_original_mb - total_compressed_mb:.1f}MB ({(total_original_mb - total_compressed_mb)/1024:.2f}GB)")
        print(f"⏱️  Total time: {total_time:.1f}s ({total_time/60:.1f} minutes)")
        print("="*60)

if __name__ == "__main__":
    video_dir = "/app/media/posts/videos"
    
    if not os.path.exists(video_dir):
        print(f"Directory {video_dir} not found!")
        sys.exit(1)
    
    # Settings for fast upload (1-2 MB)
    target_mb = 1.5  # Target file size
    max_mb = 2       # Maximum file size
    
    # Check command line arguments
    if len(sys.argv) > 1:
        try:
            target_mb = float(sys.argv[1])
            if len(sys.argv) > 2:
                max_mb = float(sys.argv[2])
        except:
            pass
    
    process_videos_fast(video_dir, target_mb, max_mb)