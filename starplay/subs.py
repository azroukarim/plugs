import os
import json
import urllib.request
import urllib.parse
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

API_KEY_PATH = "/etc/enigma2/subapi-key/api-key.txt"

def log_debug(msg):
    try:
        with open("/tmp/StarPlay_subs.log", "a") as f:
            f.write(msg + "\n")
    except:
        pass

def get_api_key():
    try:
        if os.path.exists(API_KEY_PATH):
            with open(API_KEY_PATH, "r") as f:
                return f.read().strip()
    except Exception:
        pass
    return None

def download_subtitle(imdb_id, title, lang="ar"):
    log_debug(f"--- Starting subtitle fetch for {title} (IMDb: {imdb_id}) ---")
    log_debug(f"Selected language: {lang}")
    api_key = get_api_key()
    if not api_key:
        log_debug("No API key found.")
        return None, None

    clean_imdb_id = imdb_id.replace('tt', '')
    
    search_url = f"https://api.opensubtitles.com/api/v1/subtitles?imdb_id={clean_imdb_id}&languages={lang}"
    log_debug(f"Search URL: {search_url}")
    try:
        req = urllib.request.Request(search_url, headers={
            'Api-Key': api_key,
            'User-Agent': 'StarPlay v1',
            'Accept': 'application/json'
        })
        res = urllib.request.urlopen(req, timeout=10, context=ctx)
        data = json.loads(res.read().decode('utf-8'))
        
        if not data.get('data'):
            log_debug(f"No {lang} subtitles found in API response.")
            if lang != "en":
                log_debug("Falling back to English (en) for auto-translation...")
                return download_subtitle(imdb_id, title, "en")
            return None, None
            
        file_id = data['data'][0]['attributes']['files'][0]['file_id']
        log_debug(f"Found subtitle, file_id: {file_id}")
        
        download_url = "https://api.opensubtitles.com/api/v1/download"
        post_data = json.dumps({"file_id": file_id}).encode('utf-8')
        
        req_dl = urllib.request.Request(download_url, data=post_data, headers={
            'Api-Key': api_key,
            'User-Agent': 'StarPlay v1',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        res_dl = urllib.request.urlopen(req_dl, timeout=10, context=ctx)
        dl_data = json.loads(res_dl.read().decode('utf-8'))
        
        srt_link = dl_data.get('link')
        if not srt_link:
            log_debug("No download link in response.")
            return None, None
            
        log_debug(f"Download link: {srt_link}")
        clean_title = "".join(x for x in title if x.isalnum() or x in " -_")
        srt_path = f"/tmp/{clean_title}.srt"
        
        req_srt = urllib.request.Request(srt_link, headers={
            'User-Agent': 'StarPlay v1'
        })
        res_srt = urllib.request.urlopen(req_srt, timeout=10, context=ctx)
        
        with open(srt_path, 'wb') as f:
            f.write(res_srt.read())
            
        log_debug(f"Successfully downloaded to {srt_path}")
        return srt_path, lang
        
    except Exception as e:
        log_debug(f"Subtitle error: {str(e)}")
        return None, None
