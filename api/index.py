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
    url = re.sub(r'\?si=[^&\s]+', '', url)
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

@app.route('/')
def home():
    return 'YouTube Downloader API is running!'

@app.route('/api/download')
def download():
    raw_url = request.args.get('url')
    quality = request.args.get('quality', 'high').lower()
    
    if not raw_url:
        return jsonify({'error': 'url required'}), 400
    
    video_id = extract_video_id(raw_url)
    if video_id:
        url = f'https://www.youtube.com/watch?v={video_id}'
    else:
        return jsonify({'error': 'invalid YouTube URL'}), 400
    
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'format': QUALITY_MAP.get(quality, QUALITY_MAP['high']),
            'nocheckcertificate': True,
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}}
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_url = info.get('url') or (info.get('formats', [{}])[-1].get('url'))
            
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
                'uploader': info.get('uploader')
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
