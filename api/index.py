from flask import Flask, request, redirect, jsonify
import subprocess
import json
import re
import sys
import os

app = Flask(__name__)

@app.route('/')
def home():
    return 'YouTube Downloader API is running!'

@app.route('/api/download')
def download():
    raw_url = request.args.get('url')
    
    if not raw_url:
        return jsonify({'error': 'url parameter required'}), 400
    
    # Extract video ID
    video_id = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11})', raw_url)
    if not video_id:
        video_id = re.search(r'youtu\.be/([0-9A-Za-z_-]{11})', raw_url)
    
    if video_id:
        url = f'https://www.youtube.com/watch?v={video_id.group(1)}'
    else:
        url = raw_url
    
    try:
        # Try yt-dlp with debug
        cmd = [
            sys.executable, '-m', 'yt_dlp',
            '-g',
            '--no-check-certificate',
            url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        if result.returncode != 0:
            # Return detailed error
            return jsonify({
                'error': 'yt-dlp failed',
                'stderr': result.stderr[:500],
                'stdout': result.stdout[:500],
                'returncode': result.returncode
            }), 500
        
        video_url = result.stdout.strip().split('\n')[0]
        
        if not video_url:
            return jsonify({'error': 'No video URL found'}), 500
        
        return jsonify({
            'success': True,
            'video_url': video_url
        })
        
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Timeout'}), 504
    except Exception as e:
        return jsonify({'error': str(e)}), 500
