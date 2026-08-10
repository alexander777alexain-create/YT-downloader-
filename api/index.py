from flask import Flask, request, redirect, jsonify
import subprocess
import json
import re
import os

app = Flask(__name__)

QUALITY_MAP = {
    'low': 'worstvideo[ext=mp4]+worstaudio[ext=m4a]/worst[ext=mp4]',
    'medium': 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]',
    'high': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]'
}

def extract_video_id(url):
    """Extract video ID from any YouTube URL"""
    # Remove tracking parameters
    url = re.sub(r'\?si=[^&\s]+', '', url)
    url = re.sub(r'&si=[^&\s]+', '', url)
    
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11})(?:[?&]|$)',
        r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})',
        r'(?:shorts\/)([0-9A-Za-z_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def is_shorts_url(url):
    return '/shorts/' in url or 'shorts/' in url or 'youtu.be/' in url

@app.route('/')
def home():
    return 'YouTube Downloader API is running!'

@app.route('/api/download')
def download():
    raw_url = request.args.get('url')
    quality = request.args.get('quality', 'high').lower()
    
    if not raw_url:
        return jsonify({'error': 'url parameter required'}), 400
    
    # Convert to watch URL
    video_id = extract_video_id(raw_url)
    if video_id:
        url = f'https://www.youtube.com/watch?v={video_id}'
    else:
        url = raw_url
    
    if 'youtube.com' not in url:
        return jsonify({'error': 'only YouTube URLs supported'}), 400
    
    is_shorts = is_shorts_url(raw_url)
    final_quality = 'high' if is_shorts else quality
    
    if final_quality not in QUALITY_MAP:
        return jsonify({'error': 'quality must be low, medium, or high'}), 400
    
    try:
        # 🔥 Use subprocess instead of yt-dlp Python module
        format_filter = QUALITY_MAP[final_quality]
        
        # Get video URL
        cmd = [
            'yt-dlp',
            '-g',  # Get URL only
            '--extractor-args', 'youtube:player_client=android',
            '--format', format_filter,
            '--no-check-certificate',
            url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            # Try with web client as fallback
            cmd[4] = 'youtube:player_client=web'
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                return jsonify({'error': f'yt-dlp failed: {result.stderr[:200]}'}), 500
        
        video_url = result.stdout.strip().split('\n')[0]
        
        if not video_url:
            return jsonify({'error': 'No video URL found'}), 500
        
        # Get metadata
        meta_cmd = [
            'yt-dlp',
            '-j',  # JSON output
            '--extractor-args', 'youtube:player_client=android',
            '--no-check-certificate',
            url
        ]
        meta_result = subprocess.run(meta_cmd, capture_output=True, text=True, timeout=30)
        
        info = {}
        if meta_result.returncode == 0 and meta_result.stdout:
            try:
                info = json.loads(meta_result.stdout)
            except:
                pass
        
        if request.args.get('redirect') == 'true':
            return redirect(video_url)
        
        return jsonify({
            'success': True,
            'title': info.get('title', 'Unknown'),
            'video_url': video_url,
            'thumbnail': info.get('thumbnail'),
            'duration': info.get('duration'),
            'quality': 'original' if is_shorts else final_quality,
            'is_shorts': is_shorts,
            'uploader': info.get('uploader'),
            'view_count': info.get('view_count'),
            'like_count': info.get('like_count')
        })
        
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Timeout — video too large or slow'}), 504
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
