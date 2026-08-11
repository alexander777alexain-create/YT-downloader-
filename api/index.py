from flask import Flask, request, redirect, jsonify
import requests
import re

app = Flask(__name__)

def extract_video_id(url):
    """Extract YouTube video ID from any URL"""
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
    
    if not raw_url:
        return jsonify({'error': 'url parameter required'}), 400
    
    video_id = extract_video_id(raw_url)
    if not video_id:
        return jsonify({'error': 'invalid YouTube URL'}), 400
    
    try:
        # External API — works on Vercel, no yt-dlp dependency
        api_url = f'https://api.vevioz.com/api/button/mp3/{video_id}'
        resp = requests.get(api_url, timeout=10)
        data = resp.json()
        
        if data.get('success'):
            video_url = data.get('download') or data.get('link')
            if not video_url:
                return jsonify({'error': 'download link not found'}), 500
            
            # Redirect mode
            if request.args.get('redirect') == 'true':
                return redirect(video_url)
            
            return jsonify({
                'success': True,
                'title': data.get('title', 'Unknown'),
                'video_url': video_url,
                'thumbnail': data.get('thumbnail'),
                'duration': data.get('duration'),
                'uploader': data.get('uploader')
            })
        else:
            return jsonify({'error': 'API returned error'}), 500
            
    except requests.Timeout:
        return jsonify({'error': 'request timed out'}), 504
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
