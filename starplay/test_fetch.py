import ssl
import json
import urllib.request
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

imdb_id = "tt0111161"
yts_domains = ["yts.mx", "yts.rs", "yts.do", "yts.ag"]

for domain in yts_domains:
    url = f"https://{domain}/api/v2/list_movies.json?query_term={imdb_id}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        res = urllib.request.urlopen(req, timeout=6, context=ctx)
        print(f"SUCCESS: {domain} -> {res.read().decode('utf-8')[:50]}")
    except Exception as e:
        print(f"ERROR: {domain} -> {e}")

try:
    tpb_url = f"https://apibay.org/q.php?q={imdb_id}"
    tpb_req = urllib.request.Request(tpb_url, headers={'User-Agent': 'Mozilla/5.0'})
    tpb_res = urllib.request.urlopen(tpb_req, timeout=6, context=ctx)
    print(f"SUCCESS: apibay -> {tpb_res.read().decode('utf-8')[:50]}")
except Exception as e:
    print(f"ERROR: apibay -> {e}")
