import os
import threading
import urllib.request
import ssl
from twisted.internet import reactor

def _download_thread(url, dest_path, callback, errback):
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req, timeout=10, context=ctx)
        
        with open(dest_path, 'wb') as f:
            f.write(response.read())
            
        if callback:
            # Must use callFromThread to safely execute the callback in the Enigma2 main GUI thread
            reactor.callFromThread(callback, dest_path)
    except Exception as e:
        print(f"[StarPlay] Error downloading {url}: {e}")
        if errback:
            reactor.callFromThread(errback, url)

def download_image(url, dest_path, callback=None, errback=None):
    """
    Downloads an image asynchronously using threading, to bypass Twisted SSL issues.
    """
    if not url:
        if errback: errback("No URL")
        return
        
    t = threading.Thread(target=_download_thread, args=(url, dest_path, callback, errback))
    t.daemon = True
    t.start()

def clear_cache():
    for i in range(15):
        path = f"/tmp/poster_{i}.jpg"
        if os.path.exists(path):
            try:
                os.remove(path)
            except:
                pass
