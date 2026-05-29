# pyrefly: ignore [missing-import]
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.MenuList import MenuList
from enigma import eTimer, ePicLoad, eServiceReference, eSize, ePoint
from Tools.LoadPixmap import LoadPixmap
from Screens.MessageBox import MessageBox
from Screens.InfoBar import MoviePlayer
from .api import fetch_tmdb, TMDB_API_KEY
from .downloader import download_image, clear_cache
from .scraper import get_stream_url
import ssl
import urllib.request
import urllib.parse
import json

# Initialize SSL at module level to avoid Enigma2 thread segfaults
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

class MovieDetailsScreen(Screen):
    def __init__(self, session, movie, media_type):
        self.movie = movie
        self.media_type = media_type
        
        self.skin = """
            <screen name="MovieDetailsScreen" position="center,center" size="1920,1080" title="Movie Details" backgroundColor="#101010" flags="wfNoBorder">
                <!-- Full Screen Backdrop -->
                <widget name="backdrop" position="0,0" size="1920,1080" zPosition="-3" alphatest="blend" scale="1" />
                
                <!-- Text Content (Bottom Left) -->
                <widget name="title" position="50,550" size="1800,100" font="Regular;75" halign="left" foregroundColor="#FFFFFF" shadowColor="#000000" shadowOffset="3,3" transparent="1" />
                <widget name="rating" position="50,670" size="250,50" font="Regular;35" halign="left" foregroundColor="#FFD700" shadowColor="#000000" shadowOffset="2,2" transparent="1" />
                <widget name="year" position="300,670" size="850,50" font="Regular;35" halign="left" foregroundColor="#AAAAAA" shadowColor="#000000" shadowOffset="2,2" transparent="1" />
                <widget name="overview" position="50,740" size="1600,150" font="Regular;32" halign="left" valign="top" foregroundColor="#DDDDDD" shadowColor="#000000" shadowOffset="2,2" transparent="1" />
                
                <!-- Play Button -->
                <eLabel position="50,920" size="280,60" backgroundColor="#00FFFFFF" zPosition="0" />
                <widget name="btn_play" position="50,920" size="280,60" font="Regular;35" halign="center" valign="center" foregroundColor="#000000" backgroundColor="#00FFFFFF" transparent="1" zPosition="1" />
            </screen>
        """
        Screen.__init__(self, session)
        
        title_str = movie.get('title', '')
        self["title"] = Label(title_str)
        self["rating"] = Label(f"★ {movie.get('vote_average', 'N/A')}")
        self["year"] = Label(f"{movie.get('year', 'N/A')}")
        self["overview"] = Label(movie.get('overview', 'No overview available.'))
        self["btn_play"] = Label("▶ Play (OK)")
        
        self["backdrop"] = Pixmap()
        
        self["actions"] = ActionMap(["SetupActions", "ColorActions", "OkCancelActions"], {
            "ok": self.play,
            "cancel": self.close
        }, -1)
        
        self.onLayoutFinish.append(self.load_images)
        
    def load_images(self):
        backdrop_url = self.movie.get('backdrop')
        if backdrop_url:
            dest_bd = "/tmp/detail_backdrop.jpg"
            from .downloader import download_image
            download_image(backdrop_url, dest_bd, callback=self.backdrop_loaded)

    def backdrop_loaded(self, path):
        import os
        from Tools.LoadPixmap import LoadPixmap
        if os.path.exists(path):
            ptr = LoadPixmap(path)
            if ptr is not None:
                self["backdrop"].instance.setPixmap(ptr)
                
    def play(self):
        title = self.movie['title']
        imdb_id = self.movie.get('imdb_id', '')
        
        if self.media_type == "tv":
            tmdb_id = self.movie.get('tmdb_id')
            if not tmdb_id:
                self.session.open(MessageBox, _("No TMDB ID found for this series."), MessageBox.TYPE_ERROR)
                return
            from .ui import TVShowBrowser
            self.session.open(TVShowBrowser, title, imdb_id, tmdb_id)
            self.close()
            return
            
        if not imdb_id:
            self.session.open(MessageBox, _("No IMDb ID found for this selection."), MessageBox.TYPE_ERROR)
            return
            
        self.session.open(MessageBox, _("Searching for High Quality Stream..."), MessageBox.TYPE_INFO, timeout=3)
        
        from twisted.internet import threads
        def _fetch_all_streams():
            """Collect ALL available streams and return list for user to choose."""
            all_streams = []
            seen_hashes = set()
            
            # === SOURCE 1: Torrentio (aggregates from all providers) ===
            torrentio_urls = [
                f"https://torrentio.strem.fun/providers=yts,eztv,rarbg,1337x,thepiratebay,kickass/sort=seeders/stream/movie/{imdb_id}.json",
                f"https://torrentio.strem.fun/sort=seeders/stream/movie/{imdb_id}.json",
                f"https://torrentio.strem.fun/stream/movie/{imdb_id}.json",
            ]
            
            for torrentio_url in torrentio_urls:
                try:
                    req = urllib.request.Request(torrentio_url, headers={
                        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
                        'Accept': 'application/json',
                        'Accept-Language': 'en-US,en;q=0.9'
                    })
                    res = urllib.request.urlopen(req, timeout=15, context=ctx)
                    data = json.loads(res.read().decode('utf-8'))
                    streams = data.get('streams', [])
                    
                    for stream in streams:
                        info_hash = stream.get('infoHash', '')
                        direct_url = stream.get('url', '')
                        name = stream.get('name', '').strip()
                        stream_title = stream.get('title', '').strip()
                        
                        # Parse quality from name/title
                        label_parts = []
                        for quality in ['4K', '2160p', '1080p', '720p', '480p', '360p']:
                            if quality.lower() in (name + stream_title).lower():
                                label_parts.append(quality)
                                break
                        
                        # Source name
                        source = name.split('\n')[0] if '\n' in name else name[:15]
                        if not source:
                            source = 'Unknown'
                            
                        # Size/seeds from title
                        size_info = ''
                        for line in stream_title.split('\n'):
                            if '👤' in line or 'GB' in line or 'MB' in line:
                                size_info = line.strip()[:30]
                                break
                        
                        quality_label = label_parts[0] if label_parts else '?p'
                        display = f"{quality_label} | {source} | {size_info}" if size_info else f"{quality_label} | {source}"
                        
                        if info_hash and info_hash not in seen_hashes:
                            seen_hashes.add(info_hash)
                            trackers = "tr=udp%3A%2F%2Ftracker.opentrackr.org%3A1337&tr=udp%3A%2F%2Fopen.tracker.cl%3A1337&tr=udp%3A%2F%2Fp4p.arenabg.com%3A1337"
                            magnet = f"magnet:?xt=urn:btih:{info_hash}&dn={urllib.parse.quote(title)}&{trackers}"
                            all_streams.append({'label': display, 'magnet': magnet, 'quality': quality_label})
                        elif direct_url and direct_url.startswith('http') and direct_url not in seen_hashes:
                            seen_hashes.add(direct_url)
                            all_streams.append({'label': display, 'magnet': direct_url, 'quality': quality_label})
                    
                    if all_streams:
                        break  # Got results, no need to try next URL
                except Exception:
                    continue
                    
            # === SOURCE 2: YTS API (High Quality Direct Movie Torrents) ===
            if not all_streams and self.media_type != "tv" and imdb_id:
                try:
                    req = urllib.request.Request(
                        f"https://yts.mx/api/v2/list_movies.json?query_term={imdb_id}",
                        headers={'User-Agent': 'Mozilla/5.0'}
                    )
                    res = urllib.request.urlopen(req, timeout=10, context=ctx)
                    yts_data = json.loads(res.read().decode('utf-8'))
                    if yts_data.get('status') == 'ok' and yts_data.get('data', {}).get('movie_count', 0) > 0:
                        movies_list = yts_data['data']['movies']
                        for m in movies_list:
                            for t in m.get('torrents', []):
                                h = t.get('hash', '')
                                if h and h not in seen_hashes:
                                    seen_hashes.add(h)
                                    quality = t.get('quality', '?p')
                                    size = t.get('size', '')
                                    display = f"{quality} | YTS | {size}"
                                    trackers = "tr=udp%3A%2F%2Ftracker.opentrackr.org%3A1337&tr=udp%3A%2F%2Fopen.tracker.cl%3A1337&tr=udp%3A%2F%2Fp4p.arenabg.com%3A1337"
                                    magnet = f"magnet:?xt=urn:btih:{h}&dn={urllib.parse.quote(title)}&{trackers}"
                                    all_streams.append({'label': display, 'magnet': magnet, 'quality': quality})
                except Exception:
                    pass
                    
            # === SOURCE 3: apibay fallback ===
            if not all_streams:
                clean_title = title.split('(')[0].strip()
                for q in [imdb_id, urllib.parse.quote(clean_title)]:
                    if not q:
                        continue
                    try:
                        req = urllib.request.Request(
                            f"https://apibay.org/q.php?q={q}",
                            headers={'User-Agent': 'Mozilla/5.0'}
                        )
                        res = urllib.request.urlopen(req, timeout=8, context=ctx)
                        items = json.loads(res.read().decode('utf-8'))
                        if items and isinstance(items, list):
                            for item in items:
                                h = item.get('info_hash', '')
                                if h and h != '0000000000000000000000000000000000000000' and h not in seen_hashes:
                                    seen_hashes.add(h)
                                    item_name = item.get('name', 'Unknown')[:50]
                                    size_bytes = int(item.get('size', 0))
                                    size_gb = f"{size_bytes/1024/1024/1024:.1f}GB" if size_bytes > 0 else ''
                                    # Extract quality
                                    quality = '?p'
                                    for q_label in ['4K', '2160p', '1080p', '720p', '480p']:
                                        if q_label.lower() in item_name.lower():
                                            quality = q_label
                                            break
                                    display = f"{quality} | TPB | {size_gb}"
                                    magnet = f"magnet:?xt=urn:btih:{h}&dn={urllib.parse.quote(title)}&tr=udp%3A%2F%2Ftracker.opentrackr.org%3A1337"
                                    all_streams.append({'label': display, 'magnet': magnet, 'quality': quality})
                                    if len(all_streams) >= 10:
                                        break
                        if all_streams:
                            break
                    except Exception:
                        continue
                        
            return all_streams
            
        def on_fetch_success(streams):
            if not streams:
                self.session.open(MessageBox, _(
                    f'"{title}" not found.\n'
                    'The film may be too new or not yet available.\n'
                    'Try another movie.'
                ), MessageBox.TYPE_INFO)
                return
                
            from .ui import QualitySelectScreen
            self.session.open(QualitySelectScreen, streams, title, imdb_id)
            
        def on_fetch_error(failure):
            self.session.open(MessageBox, _(f"Error: {str(failure.getErrorMessage())}"), MessageBox.TYPE_ERROR)
            
        threads.deferToThread(_fetch_all_streams).addCallback(on_fetch_success).addErrback(on_fetch_error)
        self.close()

class StarPlayGridScreen(Screen):
    # Base skin for 1920x1080 with grid items
    skin = """
    <screen position="center,center" size="1920,1080" title="StarPlay Grid" backgroundColor="#101010" flags="wfNoBorder">
        
        <!-- Header -->
        <widget name="header_title" position="50,30" size="1000,50" font="Regular;40" halign="left" valign="center" foregroundColor="#ffffff" transparent="1" />
        <widget name="page_info" position="1670,30" size="200,50" font="Regular;35" halign="right" valign="center" foregroundColor="#aaaaaa" transparent="1" />
        
        <!-- Top Categories Bar -->
        <ePixmap pixmap="skin_default/buttons/yellow.png" position="600,35" size="30,30" alphatest="on" />
        <widget name="key_yellow" position="640,30" size="200,40" font="Regular;30" halign="left" valign="center" foregroundColor="#ffff00" transparent="1" />
        
        <ePixmap pixmap="skin_default/buttons/blue.png" position="900,35" size="30,30" alphatest="on" />
        <widget name="key_blue" position="940,30" size="200,40" font="Regular;30" halign="left" valign="center" foregroundColor="#0088ff" transparent="1" />
        
        <widget name="loading_info" position="0,500" size="1920,80" font="Regular;45" halign="center" valign="center" foregroundColor="#ffff00" transparent="1" zPosition="10"/>
        
        <!-- Selection border (Yellow background to highlight) -->
        <widget name="selector" position="130,70" size="180,260" backgroundColor="#ffff00" zPosition="0" />
        
        {grid_xml}
        
        <!-- Bottom Buttons -->
        <ePixmap pixmap="skin_default/buttons/red.png" position="50,1000" size="40,40" alphatest="on" />
        <widget name="key_red" position="100,1000" zPosition="1" size="150,40" font="Regular;30" halign="left" valign="center" foregroundColor="#ffffff" transparent="1" />
        
        <ePixmap pixmap="skin_default/buttons/green.png" position="300,1000" size="40,40" alphatest="on" />
        <widget name="key_green" position="350,1000" zPosition="1" size="150,40" font="Regular;30" halign="left" valign="center" foregroundColor="#ffffff" transparent="1" />
    </screen>
    """

    def __init__(self, session, media_type="movie"):
        # Generate grid XML for 5x3 at 1920x1080
        grid_xml = ""
        self.cols = 5
        self.rows = 3
        self.item_w = 160
        self.item_h = 240
        self.spacing_x = 340
        self.spacing_y = 310
        self.start_x = 140
        self.start_y = 80

        for i in range(15):
            row = i // self.cols
            col = i % self.cols
            x = self.start_x + (col * self.spacing_x)
            y = self.start_y + (row * self.spacing_y)
            
            # Poster (zPosition=1)
            grid_xml += f'<widget name="poster_{i}" position="{x},{y}" size="{self.item_w},{self.item_h}" alphatest="on" scale="1" zPosition="1" backgroundColor="#202020" />\n'
            # Title Label (zPosition=1)
            grid_xml += f'<widget name="title_{i}" position="{x-10},{y+self.item_h+5}" size="{self.item_w+20},50" font="Regular;20" halign="center" valign="top" transparent="1" zPosition="1" foregroundColor="#ffffff" />\n'

        self.skin = self.skin.format(grid_xml=grid_xml)
        
        Screen.__init__(self, session)
        self.session = session
        
        self.media_type = media_type
        self.category = "popular" # default to popular
        self.genre_id = None
        self.genre_name = "All"
        self.page = 1
        self.movies = []
        self.current_idx = 0
        self.picloads = {}
        
        # UI Elements
        mtype_str = _("Movies") if self.media_type == "movie" else _("Series")
        cat_str = _("Popular") if self.category == "popular" else _("Latest")
        genre_str = f" - {self.genre_name}" if self.genre_id else ""
        self["header_title"] = Label(f"StarPlay - {mtype_str} ({cat_str}){genre_str}")
        self["page_info"] = Label(f"Page: {self.page}")
        self["loading_info"] = Label(_("Loading... Please wait"))
        self["selector"] = Label("") 
        
        self["key_red"] = Label(_("Close"))
        self["key_green"] = Label(_("Play"))
        self["key_yellow"] = Label(_("Toggle Sort"))
        self["key_blue"] = Label(_("Genres"))
        
        for i in range(15):
            self[f"poster_{i}"] = Pixmap()
            self[f"title_{i}"] = Label("")
            
        self["actions"] = ActionMap(["SetupActions", "DirectionActions", "ColorActions", "ChannelSelectEPGActions"],
        {
            "ok": self.playSelected,
            "cancel": self.closeUI,
            "red": self.closeUI,
            "green": self.playSelected,
            "yellow": self.toggleSort,
            "blue": self.openGenreSelect,
            "menu": self.openSettings,
            "left": self.moveLeft,
            "right": self.moveRight,
            "up": self.moveUp,
            "down": self.moveDown,
            "nextBouquet": self.pageNext,
            "prevBouquet": self.pagePrev
        }, -1)
        
        self.onLayoutFinish.append(self.startLoading)

    def closeUI(self):
        self.close()

    def toggleSort(self):
        if self.category == "latest":
            self.category = "popular"
        else:
            self.category = "latest"
        self.page = 1
        self.current_idx = 0
        self.updateHeader()
        self.startLoading()

    def openGenreSelect(self):
        from .ui import GenreSelectScreen
        self.session.openWithCallback(self.onGenreSelected, GenreSelectScreen, self.media_type)

    def onGenreSelected(self, genre_id=None, genre_name=None):
        if genre_name is not None:
            self.genre_id = genre_id
            self.genre_name = genre_name
            self.page = 1
            self.current_idx = 0
            self.updateHeader()
            self.startLoading()

    def openSettings(self):
        try:
            from .settings import StarPlaySettingsScreen
            self.session.open(StarPlaySettingsScreen)
        except Exception as e:
            print(f"StarPlay: Error opening settings {e}")

    def updateHeader(self):
        mtype_str = _("Movies") if self.media_type == "movie" else _("Series")
        cat_str = _("Popular") if self.category == "popular" else _("Latest")
        genre_str = f" - {self.genre_name}" if self.genre_id else ""
        self["header_title"].setText(f"StarPlay - {mtype_str} ({cat_str}){genre_str}")

    def startLoading(self):
        clear_cache()
        self["loading_info"].setText(_("Loading... Please wait"))
        self["page_info"].setText(f"Page: {self.page}")
        self.movies = []
        self.updateGrid()
        
        from twisted.internet import threads
        
        def worker():
            return fetch_tmdb(self.media_type, self.category, self.page, self.genre_id)
            
        def on_success(result):
            self.movies = result
            if not self.movies:
                self["loading_info"].setText(_("Error fetching data."))
            else:
                first_title = self.movies[0].get('title', '')
                if first_title.startswith("ERROR:"):
                    self["loading_info"].setText(first_title)
                else:
                    self["loading_info"].setText("")
            self.updateGrid()
            
        def on_error(failure):
            self.movies = [{"title": f"ERROR: {str(failure.getErrorMessage())}", "imdb_id": "", "poster": ""}]
            self["loading_info"].setText(self.movies[0]["title"])
            self.updateGrid()
            
        threads.deferToThread(worker).addCallback(on_success).addErrback(on_error)

    def updateGrid(self):
        for i in range(15):
            if i < len(self.movies):
                movie = self.movies[i]
                if not movie['title'].startswith("ERROR:"):
                    self[f"title_{i}"].setText(movie.get('display_title', movie['title']))
                    poster_url = movie['poster']
                    dest = f"/tmp/poster_{i}.jpg"
                    if poster_url:
                        download_image(poster_url, dest, callback=self.posterLoaded)
                else:
                    self[f"title_{i}"].setText("")
            else:
                self[f"title_{i}"].setText("")
                self[f"poster_{i}"].hide()
                
        self.updateSelector()

    def posterLoaded(self, path):
        try:
            idx = int(path.split('_')[1].split('.')[0])
            self.showPoster(idx, path)
        except:
            pass

    def showPoster(self, idx, path):
        import os
        if idx < 15 and self[f"poster_{idx}"] and os.path.exists(path):
            ptr = LoadPixmap(path)
            if ptr is not None:
                self[f"poster_{idx}"].instance.setPixmap(ptr)
                self[f"poster_{idx}"].show()

    def updateSelector(self):
        if not self.movies or (len(self.movies) > 0 and self.movies[0]['title'].startswith("ERROR:")):
            self["selector"].hide()
            return
            
        self["selector"].show()
        row = self.current_idx // self.cols
        col = self.current_idx % self.cols
        x = self.start_x + (col * self.spacing_x) - 5
        y = self.start_y + (row * self.spacing_y) - 5
        self["selector"].instance.move(ePoint(int(x), int(y)))

    def moveLeft(self):
        if self.current_idx > 0:
            self.current_idx -= 1
            self.updateSelector()
        else:
            # First item, jump to prev page
            self.pagePrev()

    def moveRight(self):
        if self.current_idx < len(self.movies) - 1:
            self.current_idx += 1
            self.updateSelector()
        elif self.current_idx == 14:
            # Last item on page, jump to next page
            self.pageNext()

    def moveUp(self):
        if self.current_idx - self.cols >= 0:
            self.current_idx -= self.cols
            self.updateSelector()

    def moveDown(self):
        if self.current_idx + self.cols < len(self.movies):
            self.current_idx += self.cols
            self.updateSelector()

    def pageNext(self):
        self.page += 1
        self.current_idx = 0
        self.startLoading()

    def pagePrev(self):
        if self.page > 1:
            self.page -= 1
            self.current_idx = 0
            self.startLoading()

    def playSelected(self):
        if not self.movies or self.current_idx >= len(self.movies):
            return
            
        movie = self.movies[self.current_idx]
        if movie.get('title', '').startswith("ERROR:"): return
        
        self.session.open(MovieDetailsScreen, movie, self.media_type)

class QualitySelectScreen(Screen):
    skin = """
    <screen position="center,center" size="1920,1080" title="Choose Quality" backgroundColor="#101010" flags="wfNoBorder">
        <widget name="title" position="50,50" size="1820,80" font="Regular;50" halign="center" valign="center" foregroundColor="#f5c518" transparent="1" zPosition="2" />
        <widget name="subtitle" position="50,140" size="1820,50" font="Regular;35" halign="center" valign="center" foregroundColor="#aaaaaa" transparent="1" zPosition="2" />
        <widget name="list" position="200,220" size="1520,780" font="Regular;45" itemHeight="80" scrollbarMode="showOnDemand" transparent="1" zPosition="2" />
    </screen>
    """
    
    def __init__(self, session, streams, title, imdb_id):
        Screen.__init__(self, session)
        self.streams = streams
        self.movie_title = title
        self.imdb_id = imdb_id
        
        self["title"] = Label(f"{title}")
        self["subtitle"] = Label(f"{len(streams)} Quality Options Available - Press OK to Play")
        self["list"] = MenuList([])
        
        self["actions"] = ActionMap(["SetupActions", "ColorActions"], {
            "ok": self.onSelect,
            "cancel": self.close,
        }, -1)
        
        self.onLayoutFinish.append(self.populateList)
        
    def populateList(self):
        labels = [s['label'] for s in self.streams]
        self["list"].setList(labels)
        self["list"].show()
        
    def onSelect(self):
        idx = self["list"].getSelectedIndex()
        if idx < 0 or idx >= len(self.streams):
            return
        selected = self.streams[idx]
        magnet = selected['magnet']
        
        self["subtitle"].setText(_("Connecting to peers... Please wait..."))
        
        from .engine import play_magnet
        play_magnet(self.session, magnet, self.movie_title, self.imdb_id)


class TVShowBrowser(Screen):
    skin = """
    <screen position="center,center" size="1920,1080" title="TV Show Browser" backgroundColor="#101010" flags="wfNoBorder">
        <widget name="poster" position="1150,150" size="650,850" alphatest="on" scale="1" zPosition="1" backgroundColor="#202020" />
        <widget name="title" position="50,50" size="1100,80" font="Regular;50" halign="left" valign="center" foregroundColor="#ffffff" transparent="1" zPosition="2" />
        <widget name="list" position="50,150" size="1050,850" font="Regular;40" itemHeight="60" scrollbarMode="showOnDemand" transparent="1" zPosition="2" />
        <widget name="loading" position="50,450" size="1050,100" font="Regular;40" halign="center" valign="center" foregroundColor="#ffff00" transparent="1" zPosition="10"/>
    </screen>
    """
    
    def __init__(self, session, show_title, imdb_id, tmdb_id):
        Screen.__init__(self, session)
        self.show_title = show_title
        self.imdb_id = imdb_id
        self.tmdb_id = tmdb_id
        
        self.state = "seasons" # "seasons" or "episodes"
        self.seasons = []
        self.episodes = []
        self.selected_season = None
        
        self["title"] = Label(f"{show_title} - Seasons")
        self["list"] = MenuList([])
        self["loading"] = Label("Loading Seasons...")
        self["poster"] = Pixmap()
        
        self["actions"] = ActionMap(["SetupActions", "ColorActions"], {
            "ok": self.onSelect,
            "cancel": self.onCancel,
        }, -1)
        
        self.onLayoutFinish.append(self.loadSeasons)
        self["list"].onSelectionChanged.append(self.selectionChanged)
        
    def loadSeasons(self):
        from twisted.internet import threads
        from .api import fetch_seasons
        self["list"].hide()
        self["loading"].show()
        threads.deferToThread(fetch_seasons, self.tmdb_id).addCallback(self.onSeasonsLoaded).addErrback(self.onError)
        
    def onSeasonsLoaded(self, seasons):
        self["loading"].hide()
        self.seasons = seasons
        if not seasons:
            self.session.open(MessageBox, "No seasons found.", MessageBox.TYPE_ERROR)
            self.close()
            return
            
        list_items = [s['name'] for s in seasons]
        self["list"].setList(list_items)
        self["list"].show()
        self.selectionChanged()
        
    def selectionChanged(self):
        idx = self["list"].getSelectedIndex()
        if idx == -1: return
        
        poster_url = ""
        if self.state == "seasons" and self.seasons and idx < len(self.seasons):
            poster_url = self.seasons[idx].get('poster')
        elif self.state == "episodes" and self.episodes and idx < len(self.episodes):
            poster_url = self.episodes[idx].get('still')
            
        if poster_url:
            from .downloader import download_image
            import os
            # Delete old poster to force refresh
            if os.path.exists("/tmp/tv_poster.jpg"):
                try: os.remove("/tmp/tv_poster.jpg")
                except: pass
                
            download_image(poster_url, "/tmp/tv_poster.jpg", self.showPoster)
            
    def showPoster(self, path):
        import os
        if path and os.path.exists(path):
            ptr = LoadPixmap(path)
            if ptr is not None:
                self["poster"].instance.setPixmap(ptr)
                self["poster"].show()
        
    def loadEpisodes(self, season_num):
        from twisted.internet import threads
        from .api import fetch_episodes
        self.state = "episodes"
        self.selected_season = season_num
        self["title"].setText(f"{self.show_title} - Season {season_num} Episodes")
        self["list"].hide()
        self["loading"].show()
        threads.deferToThread(fetch_episodes, self.tmdb_id, season_num).addCallback(self.onEpisodesLoaded).addErrback(self.onError)
        
    def onEpisodesLoaded(self, episodes):
        self["loading"].hide()
        self.episodes = episodes
        if not episodes:
            self.session.open(MessageBox, "No episodes found.", MessageBox.TYPE_ERROR)
            self.state = "seasons"
            self["title"].setText(f"{self.show_title} - Seasons")
            self["list"].setList([s['name'] for s in self.seasons])
            self["list"].show()
            return
            
        list_items = [e['name'] for e in episodes]
        self["list"].setList(list_items)
        self["list"].show()
        self.selectionChanged()
        
    def onError(self, failure):
        self["loading"].hide()
        self.session.open(MessageBox, f"Error: {str(failure.getErrorMessage())}", MessageBox.TYPE_ERROR)
        
    def onCancel(self):
        if self.state == "episodes":
            self.state = "seasons"
            self["title"].setText(f"{self.show_title} - Seasons")
            self["list"].setList([s['name'] for s in self.seasons])
            self["list"].show()
        else:
            self.close()
            
    def onSelect(self):
        idx = self["list"].getSelectedIndex()
        if self.state == "seasons":
            season = self.seasons[idx]
            self.loadEpisodes(season['season_number'])
        else:
            episode = self.episodes[idx]
            self.playEpisode(episode)
            
    def playEpisode(self, episode):
        ep_num = episode['episode_number']
        season_num = self.selected_season
        ep_title = f"{self.show_title} S{season_num:02d}E{ep_num:02d}"
        
        self.session.open(MessageBox, f"Searching torrent for {ep_title}...", MessageBox.TYPE_INFO, timeout=2)
        
        from twisted.internet import threads
        
        def _fetch_episode_magnet():
            # Try EZTV with limit 100
            import urllib.request, json, urllib.parse
            eztv_domains = ["eztvx.to", "eztv.re"]
            torrents = []
            eztv_id = self.imdb_id.replace('tt', '')
            for domain in eztv_domains:
                try:
                    url = f"https://{domain}/api/get-torrents?imdb_id={eztv_id}&limit=100"
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    res = urllib.request.urlopen(req, timeout=5, context=ctx)
                    data = json.loads(res.read().decode('utf-8'))
                    torrents = data.get('torrents', [])
                    if torrents:
                        break
                except Exception:
                    continue
                    
            magnet = ""
            if torrents:
                # Filter by season and episode
                for t in torrents:
                    if str(t.get('season')) == str(season_num) and str(t.get('episode')) == str(ep_num):
                        magnet = t.get('magnet_url')
                        break
            
            # TPB Fallback
            if not magnet:
                try:
                    query = f"{self.show_title} s{season_num:02d}e{ep_num:02d}"
                    tpb_url = f"https://apibay.org/q.php?q={urllib.parse.quote(query)}"
                    tpb_req = urllib.request.Request(tpb_url, headers={'User-Agent': 'Mozilla/5.0'})
                    tpb_res = urllib.request.urlopen(tpb_req, timeout=5, context=ctx)
                    tpb_data = json.loads(tpb_res.read().decode('utf-8'))
                    if tpb_data and isinstance(tpb_data, list) and tpb_data[0].get('info_hash') and tpb_data[0].get('info_hash') != '0000000000000000000000000000000000000000':
                        hash = tpb_data[0]['info_hash']
                        magnet = f"magnet:?xt=urn:btih:{hash}&dn={urllib.parse.quote(ep_title)}&tr=udp%3A%2F%2Ftracker.opentrackr.org%3A1337"
                except Exception:
                    pass
                    
            return magnet
            
        def on_fetch_success(magnet):
            if not magnet:
                self.session.open(MessageBox, "Episode not found in Torrents.", MessageBox.TYPE_ERROR)
                return
            from .engine import play_magnet
            play_magnet(self.session, magnet, ep_title, imdb_id=self.imdb_id, season=season_num, episode=ep_num)
            
        def on_fetch_error(failure):
            self.session.open(MessageBox, f"Error fetching Episode: {str(failure.getErrorMessage())}", MessageBox.TYPE_ERROR)
            
        threads.deferToThread(_fetch_episode_magnet).addCallback(on_fetch_success).addErrback(on_fetch_error)


class GenreSelectScreen(Screen):
    skin = """
    <screen position="center,center" size="600,800" title="Select Genre" backgroundColor="#101010" flags="wfNoBorder">
        <widget name="list" position="20,20" size="560,760" font="Regular;35" itemHeight="60" scrollbarMode="showOnDemand" transparent="1" zPosition="2" />
    </screen>
    """
    
    def __init__(self, session, media_type):
        Screen.__init__(self, session)
        self.media_type = media_type
        
        # TMDB Genres
        self.movie_genres = [
            ("All", None), ("Action", 28), ("Adventure", 12), ("Animation", 16), 
            ("Comedy", 35), ("Crime", 80), ("Documentary", 99), ("Drama", 18), 
            ("Family", 10751), ("Fantasy", 14), ("History", 36), ("Horror", 27), 
            ("Music", 10402), ("Mystery", 9648), ("Romance", 10749), ("Sci-Fi", 878), 
            ("Thriller", 53), ("War", 10752), ("Western", 37)
        ]
        
        self.tv_genres = [
            ("All", None), ("Action & Adventure", 10759), ("Animation", 16), ("Comedy", 35),
            ("Crime", 80), ("Documentary", 99), ("Drama", 18), ("Family", 10751), 
            ("Kids", 10762), ("Mystery", 9648), ("News", 10763), ("Reality", 10764),
            ("Sci-Fi & Fantasy", 10765), ("Soap", 10766), ("Talk", 10767), ("War & Politics", 10768),
            ("Western", 37)
        ]
        
        self.genres = self.movie_genres if media_type == "movie" else self.tv_genres
        
        from Components.MenuList import MenuList
        self["list"] = MenuList([g[0] for g in self.genres])
        
        self["actions"] = ActionMap(["SetupActions", "ColorActions"], {
            "ok": self.onSelect,
            "cancel": self.closeUI
        }, -1)
        
    def closeUI(self):
        self.close(None, None)
        
    def onSelect(self):
        idx = self["list"].getSelectedIndex()
        genre_name = self.genres[idx][0]
        genre_id = self.genres[idx][1]
        self.close(genre_id, genre_name)
