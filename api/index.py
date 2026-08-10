from flask import Flask, request, redirect, jsonify
import yt_dlp
import re

app = Flask(__name__)

QUALITY_MAP = {
    'low': 'worstvideo[ext=mp4]+worstaudio[ext=m4a]/worst[ext=mp4]',
    'medium': 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]',
    'high': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]'
}

def extract_video_id(url):
    """Extract video ID from any YouTube URL (including shorts)"""
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
    """Check if URL is a YouTube Shorts link"""
    return '/shorts/' in url or 'shorts/' in url

@app.route('/')
def home():
    return 'YouTube Downloader API is running!'

@app.route('/api/download')
def download():
    url = request.args.get('url')
    quality_param = request.args.get('quality', 'high').lower()
    
    if not url:
        return jsonify({'error': 'url parameter required'}), 400
    
    # Extract video ID and normalize URL
    video_id = extract_video_id(url)
    if video_id:
        url = f'https://www.youtube.com/watch?v={video_id}'
    
    if 'youtube.com' not in url and 'youtu.be' not in url:
        return jsonify({'error': 'only YouTube URLs supported'}), 400
    
    # Check if it's a Shorts link
    is_shorts = is_shorts_url(request.args.get('url'))
    
    # If shorts, force high quality (best available)
    quality = 'high' if is_shorts else quality_param
    
    if quality not in QUALITY_MAP:
        return jsonify({'error': 'quality must be low, medium, or high'}), 400
    
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'format': QUALITY_MAP[quality],
            'nocheckcertificate': True,
            'ignoreerrors': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if not info:
                return jsonify({'error': 'No data found'}), 500
            
            # Extract video URL
            video_url = None
            if 'url' in info:
                video_url = info['url']
            elif 'formats' in info and info['formats']:
                for f in info['formats']:
                    if f.get('url') and 'video' in f.get('format_note', '').lower():
                        video_url = f['url']
                        break
                if not video_url:
                    video_url = info['formats'][-1].get('url')
            
            if not video_url:
                return jsonify({'error': 'video URL not found'}), 500
            
            # If shorts and redirect mode, redirect directly
            if is_shorts and request.args.get('redirect') == 'true':
                return redirect(video_url)
            
            # Build response
            response = {
                'success': True,
                'title': info.get('title', 'Unknown'),
                'video_url': video_url,
                'thumbnail': info.get('thumbnail'),
                'duration': info.get('duration'),
                'quality': 'original' if is_shorts else quality,
                'is_shorts': is_shorts,
                'uploader': info.get('uploader'),
                'view_count': info.get('view_count'),
                'like_count': info.get('like_count')
            }
            
            # If shorts, add message
            if is_shorts:
                response['message'] = 'YouTube Shorts detected — delivered in original quality'
            
            # Redirect mode (for non-shorts)
            if not is_shorts and request.args.get('redirect') == 'true':
                return redirect(video_url)
            
            return jsonify(response)
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
