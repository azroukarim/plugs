import urllib.request, ssl, json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

imdb_id = "tt33054858"

# Test 1: Torrentio default
print("=== Test 1: Torrentio default ===")
try:
    url = f"https://torrentio.strem.fun/stream/movie/{imdb_id}.json"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36', 'Accept': 'application/json'})
    res = urllib.request.urlopen(req, timeout=15, context=ctx)
    data = json.loads(res.read().decode('utf-8'))
    streams = data.get('streams', [])
    print(f"RESULT: {len(streams)} streams")
    for s in streams[:3]:
        print(f"  - hash={s.get('infoHash','')[:20]} url={str(s.get('url',''))[:40]} name={s.get('name','')}")
except Exception as e:
    print(f"ERROR: {e}")

# Test 2: Torrentio with sort
print("\n=== Test 2: Torrentio with sort=seeders ===")
try:
    url = f"https://torrentio.strem.fun/sort=seeders/stream/movie/{imdb_id}.json"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36', 'Accept': 'application/json'})
    res = urllib.request.urlopen(req, timeout=15, context=ctx)
    data = json.loads(res.read().decode('utf-8'))
    streams = data.get('streams', [])
    print(f"RESULT: {len(streams)} streams")
    for s in streams[:3]:
        print(f"  - hash={s.get('infoHash','')[:20]} url={str(s.get('url',''))[:40]} name={s.get('name','')}")
except Exception as e:
    print(f"ERROR: {e}")

# Test 3: Torrentio with all providers
print("\n=== Test 3: Torrentio all providers ===")
try:
    url = f"https://torrentio.strem.fun/providers=yts,eztv,rarbg,1337x,thepiratebay,kickass/sort=seeders/stream/movie/{imdb_id}.json"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36', 'Accept': 'application/json'})
    res = urllib.request.urlopen(req, timeout=15, context=ctx)
    data = json.loads(res.read().decode('utf-8'))
    streams = data.get('streams', [])
    print(f"RESULT: {len(streams)} streams")
    for s in streams[:3]:
        print(f"  - hash={s.get('infoHash','')[:20]} url={str(s.get('url',''))[:40]} name={s.get('name','')}")
except Exception as e:
    print(f"ERROR: {e}")

# Test 4: apibay by title search
print("\n=== Test 4: apibay title search ===")
try:
    url = "https://apibay.org/q.php?q=tt33054858"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    res = urllib.request.urlopen(req, timeout=8, context=ctx)
    data = json.loads(res.read().decode('utf-8'))
    print(f"RESULT: {len(data)} items")
    if data:
        print(f"  First: hash={data[0].get('info_hash','')[:20]} name={data[0].get('name','')[:40]}")
except Exception as e:
    print(f"ERROR: {e}")
