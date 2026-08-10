from flask import Flask, request, redirect, jsonify
import yt_dlp

app = Flask(__name__)

# Quality mapping
QUALITY_MAP = {
    'low': 'worstvideo[ext=mp4]+worstaudio[ext=m4a]/worst[ext=mp4]',
    'medium': 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]',
    'high': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]'
}

@app.route('/')
def home():
    return 'YouTube Downloader API is running!'

@app.route('/api/download')
def download():
    url = request.args.get('url')
    quality = request.args.get('quality', 'high').lower()
    
    if not url:
        return jsonify({'error': 'url parameter required'}), 400
    
    if 'youtube.com' not in url and 'youtu.be' not in url:
        return jsonify({'error': 'only YouTube URLs supported'}), 400
    
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
            
            # Redirect mode
            if request.args.get('redirect') == 'true':
                return redirect(video_url)
            
            # JSON response
            return jsonify({
                'success': True,
                'title': info.get('title', 'Unknown'),
                'video_url': video_url,
                'thumbnail': info.get('thumbnail'),
                'duration': info.get('duration'),
                'quality': quality,
                'uploader': info.get('uploader'),
                'view_count': info.get('view_count'),
                'like_count': info.get('like_count')
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
