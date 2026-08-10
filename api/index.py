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
    """Extract 11-character video ID from any YouTube URL"""
    # Remove tracking parameters like ?si=...
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
    
    # Convert any YouTube URL to standard watch URL
    video_id = extract_video_id(raw_url)
    if video_id:
        url = f'https://www.youtube.com/watch?v={video_id}'
    else:
        url = raw_url
    
    if 'youtube.com' not in url:
        return jsonify({'error': 'only YouTube URLs supported'}), 400
    
    # Shorts force original quality
    is_shorts = is_shorts_url(raw_url)
    final_quality = 'high' if is_shorts else quality
    
    if final_quality not in QUALITY_MAP:
        return jsonify({'error': 'quality must be low, medium, or high'}), 400
    
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'format': QUALITY_MAP[final_quality],
            'nocheckcertificate': True,
            'ignoreerrors': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],
                    'skip': ['dash', 'hls']
                }
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if not info:
                return jsonify({'error': 'No data found'}), 500
            
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
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
