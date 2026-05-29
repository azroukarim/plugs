import urllib.request
import urllib.error
import json
import re

# Import the API key from api.py
from .api import TMDB_API_KEY

def get_stream_url(imdb_id, media_type="movie"):
    """
    Since free movie streaming APIs use heavy JS obfuscation,
    this scraper will fallback to fetching the Official Trailer from YouTube.
    Enigma2 can play YouTube links natively if youtube-dl or ServiceApp is installed.
    """
    url = f"https://api.themoviedb.org/3/{media_type}/{imdb_id}/videos?api_key={TMDB_API_KEY}"
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req, timeout=10)
        data = json.loads(response.read().decode('utf-8'))
        
        for video in data.get('results', []):
            if video.get('site') == 'YouTube' and video.get('type') == 'Trailer':
                yt_key = video.get('key')
                if yt_key:
                    # Return standard YouTube link. Enigma2 handles this via youtube-dl usually.
                    return f"https://www.youtube.com/watch?v={yt_key}"
                    
        # Fallback to just the YouTube search link if no trailer is found in TMDB
        return None
        
    except Exception as e:
        print(f"[StarPlay] Error fetching trailer: {e}")
        return None
