import json
import urllib.request
import urllib.error
import ssl

# =======================================================
# ضع مفتاح TMDB الخاص بك هنا (مهم جداً لكي تعمل الإضافة)
# =======================================================
TMDB_API_KEY = "e18ea3ce815513964722e3b189cec5d5"

# Initialize SSL context at module level (main thread) to avoid Enigma2 segfaults
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def fetch_tmdb(media_type="movie", category="popular", page=1, genre_id=None):
    """
    media_type: 'movie' or 'tv'
    category: 'latest' or 'popular'
    genre_id: optional TMDB genre ID
    """
    if TMDB_API_KEY == "PUT_YOUR_TMDB_API_KEY_HERE" or not TMDB_API_KEY:
        return [{"title": "ERROR: Please insert your TMDB API KEY in api.py", "imdb_id": "", "poster": ""}]
        
    url = ""
    if genre_id:
        # Use discover API when genre is specified
        endpoint = "discover/movie" if media_type == "movie" else "discover/tv"
        sort_param = "popularity.desc"
        if category == "latest":
            sort_param = "primary_release_date.desc" if media_type == "movie" else "first_air_date.desc"
        url = f"https://api.themoviedb.org/3/{endpoint}?api_key={TMDB_API_KEY}&page={page}&language=en&with_genres={genre_id}&sort_by={sort_param}"
    else:
        # Standard endpoints
        endpoint = ""
        if media_type == "movie":
            endpoint = "movie/now_playing" if category == "latest" else "movie/popular"
        else:
            endpoint = "tv/on_the_air" if category == "latest" else "tv/popular"
        url = f"https://api.themoviedb.org/3/{endpoint}?api_key={TMDB_API_KEY}&page={page}&language=en"

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req, timeout=10, context=ctx)
        data = json.loads(response.read().decode('utf-8'))
        
        results = data.get('results', [])[:15] # Take 15 to fit our 3x5 grid
        movies = []
        
        for item in results:
            tmdb_id = item.get('id')
            title = item.get('title') or item.get('name') or 'Unknown'
            poster_path = item.get('poster_path')
            
            # Extract release date
            release_date = item.get('release_date') or item.get('first_air_date') or ''
            year = release_date[:4] if release_date else ''
            display_title = f"{title} ({year})" if year else title
            
            poster_url = ""
            if poster_path:
                # Use w342 or w500 since we have a 1920x1080 UI and larger posters
                poster_url = f"https://image.tmdb.org/t/p/w342{poster_path}"
                
            # Fetch IMDb ID and Details
            imdb_id = ""
            overview = item.get('overview', '')
            vote_average = item.get('vote_average', 0.0)
            
            backdrop_path = item.get('backdrop_path')
            backdrop_url = f"https://image.tmdb.org/t/p/w1280{backdrop_path}" if backdrop_path else ""
            
            if tmdb_id:
                try:
                    if media_type == 'movie':
                        detail_url = f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={TMDB_API_KEY}&language=ar"
                        det_req = urllib.request.Request(detail_url, headers={'User-Agent': 'Mozilla/5.0'})
                        det_res = urllib.request.urlopen(det_req, timeout=5, context=ctx)
                        det_data = json.loads(det_res.read().decode('utf-8'))
                        imdb_id = det_data.get('imdb_id', '')
                        overview = det_data.get('overview') or overview
                        vote_average = det_data.get('vote_average') or vote_average
                    elif media_type == 'tv':
                        ext_url = f"https://api.themoviedb.org/3/tv/{tmdb_id}/external_ids?api_key={TMDB_API_KEY}"
                        ext_req = urllib.request.Request(ext_url, headers={'User-Agent': 'Mozilla/5.0'})
                        ext_res = urllib.request.urlopen(ext_req, timeout=5, context=ctx)
                        ext_data = json.loads(ext_res.read().decode('utf-8'))
                        imdb_id = ext_data.get('imdb_id', '')
                        
                        det_url = f"https://api.themoviedb.org/3/tv/{tmdb_id}?api_key={TMDB_API_KEY}&language=ar"
                        det_req = urllib.request.Request(det_url, headers={'User-Agent': 'Mozilla/5.0'})
                        det_res = urllib.request.urlopen(det_req, timeout=5, context=ctx)
                        det_data = json.loads(det_res.read().decode('utf-8'))
                        overview = det_data.get('overview') or overview
                        vote_average = det_data.get('vote_average') or vote_average
                except:
                    pass
            
            movies.append({
                'title': title,
                'display_title': display_title,
                'imdb_id': imdb_id,
                'tmdb_id': tmdb_id,
                'poster': poster_url,
                'backdrop': backdrop_url,
                'year': year,
                'overview': overview,
                'vote_average': vote_average
            })
            
        return movies
    except urllib.error.HTTPError as e:
        if e.code == 401:
            err_msg = "Invalid TMDB API Key. Please check your key."
        else:
            err_msg = f"HTTP Error {e.code}"
        print(f"[StarPlay] {err_msg}")
        return [{"title": f"ERROR: {err_msg}", "imdb_id": "", "poster": ""}]
    except Exception as e:
        err_msg = str(e)
        print(f"[StarPlay] Error fetching TMDB: {err_msg}")
        return [{"title": f"ERROR: {err_msg}", "imdb_id": "", "poster": ""}]

def fetch_seasons(tmdb_id):
    if not TMDB_API_KEY or TMDB_API_KEY == "PUT_YOUR_TMDB_API_KEY_HERE":
        return []
        
    url = f"https://api.themoviedb.org/3/tv/{tmdb_id}?api_key={TMDB_API_KEY}&language=en"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req, timeout=5, context=ctx)
        data = json.loads(response.read().decode('utf-8'))
        
        seasons = data.get('seasons', [])
        # Filter out "Specials" (season 0) if desired, but let's keep them for completeness
        valid_seasons = []
        for s in seasons:
            if s.get('season_number') is not None:
                valid_seasons.append({
                    'name': s.get('name', f"Season {s.get('season_number')}"),
                    'season_number': s.get('season_number'),
                    'episode_count': s.get('episode_count', 0),
                    'poster': f"https://image.tmdb.org/t/p/w500{s.get('poster_path')}" if s.get('poster_path') else ""
                })
        return valid_seasons
    except Exception as e:
        print(f"[StarPlay] Error fetching seasons: {e}")
        return []

def fetch_episodes(tmdb_id, season_number):
    if not TMDB_API_KEY or TMDB_API_KEY == "PUT_YOUR_TMDB_API_KEY_HERE":
        return []
        
    url = f"https://api.themoviedb.org/3/tv/{tmdb_id}/season/{season_number}?api_key={TMDB_API_KEY}&language=en"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req, timeout=5, context=ctx)
        data = json.loads(response.read().decode('utf-8'))
        
        episodes = data.get('episodes', [])
        valid_episodes = []
        for e in episodes:
            if e.get('episode_number') is not None:
                valid_episodes.append({
                    'name': f"S{season_number:02d}E{e.get('episode_number'):02d} - {e.get('name', 'Episode ' + str(e.get('episode_number')))}",
                    'episode_number': e.get('episode_number'),
                    'still': f"https://image.tmdb.org/t/p/w500{e.get('still_path')}" if e.get('still_path') else ""
                })
        return valid_episodes
    except Exception as e:
        print(f"[StarPlay] Error fetching episodes: {e}")
        return []
