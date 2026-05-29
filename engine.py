import os
import json
import urllib.request
import urllib.error
import subprocess
import time
import ssl
from enigma import eTimer
from Screens.MessageBox import MessageBox
from Screens.InfoBar import MoviePlayer
from enigma import eServiceReference

# Constants
TORR_PORT = 8090
TORR_BIN = "/usr/bin/TorrServer"
RELEASES_URL = "https://releases.yourok.ru/torr/server_release.json"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def get_arch():
    try:
        arch = subprocess.check_output('uname -m', shell=True).decode().strip()
        if 'armv7' in arch: return 'linux-arm7'
        if 'aarch64' in arch: return 'linux-arm64'
        if 'mips64' in arch: return 'linux-mips64le' # Enigma2 is mostly mipsel
        if 'mips' in arch: return 'linux-mipsle'
        if 'x86_64' in arch: return 'linux-amd64'
        if 'i686' in arch or 'i386' in arch: return 'linux-386'
        return 'linux-arm7' # Default fallback
    except:
        return 'linux-arm7'

def is_torrserver_running():
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{TORR_PORT}/echo")
        res = urllib.request.urlopen(req, timeout=2, context=ctx)
        return res.getcode() == 200
    except:
        return False

def start_torrserver():
    if is_torrserver_running():
        return True
        
    if not os.path.exists(TORR_BIN):
        return False
        
    try:
        os.system(f"chmod +x {TORR_BIN}")
        os.system("export GODEBUG=madvdontneed=1")
        fh = open(os.devnull, 'wb')
        subprocess.Popen([TORR_BIN, '--port', str(TORR_PORT)], shell=False, stdout=fh, stderr=fh)
        time.sleep(2)
        return is_torrserver_running()
    except Exception as e:
        print(f"[StarPlay] Error starting TorrServer: {e}")
        return False

def download_torrserver(session, callback):
    def _download():
        try:
            # 1. Get latest release
            req = urllib.request.Request(RELEASES_URL, headers={'User-Agent': 'Mozilla/5.0'})
            res = urllib.request.urlopen(req, timeout=10, context=ctx)
            data = json.loads(res.read().decode('utf-8'))
            
            arch_key = get_arch()
            download_url = data.get('links', {}).get(arch_key)
            
            if not download_url:
                session.open(MessageBox, "TorrServer not available for your architecture.", MessageBox.TYPE_ERROR)
                return
                
            # 2. Download binary
            session.open(MessageBox, f"Downloading TorrServer engine...\nPlease wait...", MessageBox.TYPE_INFO, timeout=3)
            dl_req = urllib.request.Request(download_url, headers={'User-Agent': 'Mozilla/5.0'})
            dl_res = urllib.request.urlopen(dl_req, timeout=60, context=ctx)
            
            with open(TORR_BIN, 'wb') as f:
                f.write(dl_res.read())
                
            os.system(f"chmod +x {TORR_BIN}")
            
            # 3. Start
            if start_torrserver():
                callback()
            else:
                session.open(MessageBox, "Failed to start TorrServer.", MessageBox.TYPE_ERROR)
                
        except Exception as e:
            session.open(MessageBox, f"Error downloading engine: {str(e)}", MessageBox.TYPE_ERROR)
            
    # Run in background to avoid blocking GUI
    import threading
    t = threading.Thread(target=_download)
    t.start()

def play_magnet(session, magnet, title, imdb_id=None):
    if not start_torrserver():
        session.openWithCallback(
            lambda res: download_torrserver(session, lambda: play_magnet(session, magnet, title, imdb_id)) if res else None,
            MessageBox,
            "StarPlay needs to install the Torrent Engine (TorrServer) to play movies.\nSize is ~15MB.\nDo you want to install it now?",
            MessageBox.TYPE_YESNO
        )
        return

    # Connecting message is now handled by the calling screen (QualitySelectScreen)
    
    try:
        from Components.config import config
        subs_enabled = config.plugins.StarPlay.subs_enable.value
        subs_lang = config.plugins.StarPlay.subs_lang.value
    except Exception:
        subs_enabled = True
        subs_lang = "ar"

    from twisted.internet import threads
    
    def _start_playback():
        # Start subtitle download in background (if imdb_id is provided)
        srt_path = None
        dl_lang = None
        if not subs_enabled:
            srt_path = "error_disabled"
        elif imdb_id:
            try:
                from .subs import download_subtitle
                srt_path, dl_lang = download_subtitle(imdb_id, title, subs_lang)
            except Exception as e:
                print(f"StarPlay: Subtitle fetch error - {e}")

        # 1. Add torrent
        add_url = f"http://127.0.0.1:{TORR_PORT}/torrents"
        add_data = json.dumps({"action": "add", "link": magnet, "title": title, "save_to_db": True}).encode('utf-8')
        add_req = urllib.request.Request(add_url, data=add_data, headers={'Content-Type': 'application/json'})
        add_res = urllib.request.urlopen(add_req, timeout=10, context=ctx)
        torrent_info = json.loads(add_res.read().decode('utf-8'))
        
        torrent_hash = torrent_info.get("hash")
        if not torrent_hash:
            raise Exception("Failed to add torrent.")
            
        # 2. Wait for metadata to fetch
        stream_url = ""
        for _ in range(15): # reduced to 15 seconds to be faster
            time.sleep(1)
            stat_url = f"http://127.0.0.1:{TORR_PORT}/torrents"
            stat_data = json.dumps({"action": "list"}).encode('utf-8')
            stat_req = urllib.request.Request(stat_url, data=stat_data, headers={'Content-Type': 'application/json'})
            stat_res = urllib.request.urlopen(stat_req, timeout=5, context=ctx)
            all_torrents = json.loads(stat_res.read().decode('utf-8'))
            
            my_tor = next((t for t in all_torrents if t.get("hash") == torrent_hash), None)
            if my_tor and my_tor.get("file_stats"):
                files = my_tor["file_stats"]
                # Find largest video file
                video_files = [f for f in files if f.get("path", "").endswith(('.mp4', '.mkv', '.avi'))]
                if video_files:
                    biggest_file = max(video_files, key=lambda f: f.get("length", 0))
                else:
                    # Fallback to biggest file
                    biggest_file = max(files, key=lambda f: f.get("length", 0))
                    
                file_id = biggest_file.get("id", 1)
                file_path = urllib.parse.quote(biggest_file.get("path", "video.mp4").encode('utf-8'))
                stream_url = f"http://127.0.0.1:{TORR_PORT}/stream/{file_path}?link={torrent_hash}&index={file_id}&play"
                break
                
        if not stream_url:
            raise Exception("Timeout waiting for torrent metadata. Seeders might be zero.")
            
        return stream_url, srt_path, dl_lang

    def on_success(result):
        stream_url, srt_path, dl_lang = result
        
        from Components.Label import Label
        from Screens.Screen import Screen
        import re

        class StarPlaySubtitleOverlay(Screen):
            def __init__(self, session):
                try:
                    from Plugins.Extensions.StarPlay import settings
                    from Components.config import config
                    color = config.plugins.StarPlay.subs_color.value
                except Exception as e:
                    print(f"[StarPlay] Color config error: {e}")
                    color = "#FFFFFF"
                
                self.skin = f"""
                    <screen position="0,650" size="1920,200" flags="wfNoBorder" backgroundColor="transparent" zPosition="10">
                        <widget name="subdelay" position="10,0" size="1900,40" font="Regular;35" halign="left" valign="top" foregroundColor="#FFFF00" backgroundColor="#000000" transparent="1" shadowColor="#000000" shadowOffset="-2,-2" />
                        <widget name="subtext" position="10,40" size="1900,160" font="Regular;55" halign="center" valign="bottom" foregroundColor="{color}" backgroundColor="#000000" transparent="1" shadowColor="#000000" shadowOffset="-3,-3" />
                    </screen>
                """
                Screen.__init__(self, session)
                self["subdelay"] = Label("")
                self["subtext"] = Label("")

        class TorrPlayer(MoviePlayer):
            def __init__(self, session, ref, dl_lang=None):
                MoviePlayer.__init__(self, session, ref)
                self.skinName = "MoviePlayer"
                
                from Components.ActionMap import ActionMap
                self["TorrActions"] = ActionMap(["SetupActions", "ColorActions", "InfobarActions", "InfobarShowHideActions", "MoviePlayerActions", "NumberActions", "DirectionActions"], {
                    "cancel": self.keyStop,
                    "red": self.keyStop,
                    "2": self.subs_delay_plus,
                    "8": self.subs_delay_minus,
                    "up": self.subs_delay_plus,
                    "down": self.subs_delay_minus
                }, prio=-100)
                
                self.srt_path = srt_path
                self.dl_lang = dl_lang
                self.subs_overlay = None
                self.subs_timer = None
                self.subs_events = []
                self.subs_delay = 0
                self.onLayoutFinish.append(self.setup_subs)
                self.onClose.append(self.cleanup_subs)
                
            def subs_delay_plus(self):
                self.subs_delay += 1000
                self.show_delay()
                    
            def subs_delay_minus(self):
                self.subs_delay -= 1000
                self.show_delay()
                
            def show_delay(self):
                if self.subs_overlay:
                    self.subs_overlay["subdelay"].setText(f"Sync: {self.subs_delay} ms")
                    from enigma import eTimer
                    if hasattr(self, 'delay_hide_timer'):
                        self.delay_hide_timer.stop()
                    else:
                        self.delay_hide_timer = eTimer()
                        try:
                            self.delay_hide_timer.callback.append(self.hide_delay)
                        except:
                            self.delay_hide_timer_conn = self.delay_hide_timer.timeout.connect(self.hide_delay)
                    self.delay_hide_timer.start(2000, True)

            def hide_delay(self):
                if self.subs_overlay:
                    self.subs_overlay["subdelay"].setText("")
                
            def setup_subs(self):
                if self.srt_path and self.srt_path != "error_disabled" and os.path.exists(self.srt_path):
                    try:
                        self.subs_events = self.parse_srt(self.srt_path)
                        self.subs_overlay = self.session.instantiateDialog(StarPlaySubtitleOverlay)
                        self.subs_overlay.show()
                        self.subs_timer = eTimer()
                        try:
                            self.subs_timer.callback.append(self.update_subs)
                        except:
                            self.subs_timer_conn = self.subs_timer.timeout.connect(self.update_subs)
                        self.subs_timer.start(200, False)
                        print(f"[StarPlay] Native subtitles loaded: {len(self.subs_events)} lines")
                        
                        if getattr(self, 'dl_lang', None) == "en" and subs_lang != "en":
                            print("[StarPlay] Starting background translation...")
                            self.subs_overlay["subdelay"].setText("Translating...")
                            self.show_delay()
                            from twisted.internet import threads
                            threads.deferToThread(self._bg_translate)
                            
                    except Exception as e:
                        print(f"[StarPlay] Subs error: {e}")

            def _bg_translate(self):
                import urllib.request
                import urllib.parse
                import json
                import re
                
                chunk_size = 30
                for i in range(0, len(self.subs_events), chunk_size):
                    if not getattr(self, 'subs_overlay', None): break
                    chunk = self.subs_events[i:i+chunk_size]
                    
                    html_str = ""
                    for idx, x in enumerate(chunk):
                        safe_text = x[2].replace('\n', '<br>')
                        html_str += f'<div id="{idx}">{safe_text}</div>'
                        
                    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl={subs_lang}&dt=t"
                    try:
                        data = urllib.parse.urlencode({'q': html_str}).encode('utf-8')
                        req = urllib.request.Request(url, data=data)
                        res = urllib.request.urlopen(req, timeout=10, context=ctx)
                        resp_json = json.loads(res.read().decode('utf-8'))
                        
                        translated_html = "".join([segment[0] for segment in resp_json[0] if segment[0]])
                        
                        matches = re.findall(r'<div id="?(\d+)"?[^>]*>(.*?)</div>', translated_html, re.DOTALL | re.IGNORECASE)
                        for match in matches:
                            idx = int(match[0])
                            trans_text = match[1].replace('<br>', '\n').replace('<br/>', '\n').replace('</br>', '\n')
                            if i + idx < len(self.subs_events):
                                old_evt = self.subs_events[i + idx]
                                self.subs_events[i + idx] = (old_evt[0], old_evt[1], trans_text)
                                
                    except Exception as e:
                        print(f"StarPlay Translation error: {e}")
                        break
                
                print("[StarPlay] Translation completed.")

            def parse_srt(self, path):
                subs = []
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    blocks = content.replace('\r', '').split('\n\n')
                    for block in blocks:
                        lines = block.strip().split('\n')
                        if len(lines) >= 3:
                            times = lines[1]
                            m = re.match(r'(\d+):(\d+):(\d+),(\d+)\s*-->\s*(\d+):(\d+):(\d+),(\d+)', times)
                            if m:
                                h1, m1, s1, ms1, h2, m2, s2, ms2 = map(int, m.groups())
                                start = (h1*3600 + m1*60 + s1)*1000 + ms1
                                end = (h2*3600 + m2*60 + s2)*1000 + ms2
                                text = '\n'.join(lines[2:])
                                text = re.sub(r'<[^>]+>', '', text)
                                subs.append((start, end, text))
                except Exception as e:
                    print(f"StarPlay parse_srt error: {e}")
                return subs
                
            def update_subs(self):
                if not self.subs_overlay: return
                service = self.session.nav.getCurrentService()
                if service:
                    seek = service.seek()
                    if seek:
                        ret, pts = seek.getPlayPosition()
                        if not ret:
                            ms = (pts / 90) - self.subs_delay
                            low, high = 0, len(self.subs_events) - 1
                            found = ""
                            while low <= high:
                                mid = (low + high) // 2
                                s_start, s_end, s_text = self.subs_events[mid]
                                if ms < s_start:
                                    high = mid - 1
                                elif ms > s_end:
                                    low = mid + 1
                                else:
                                    found = s_text
                                    break
                            self.subs_overlay["subtext"].setText(found)

            def cleanup_subs(self):
                if self.subs_timer:
                    self.subs_timer.stop()
                if self.subs_overlay:
                    try:
                        self.subs_overlay.hide()
                        self.session.deleteDialog(self.subs_overlay)
                    except:
                        pass
                    self.subs_overlay = None

            def leavePlayer(self):
                self.cleanup_subs()
                self.session.nav.stopService()
                self.close()
                
            def leavePlayerConfirmed(self, answer):
                self.session.nav.stopService()
                self.close()
                
            def doEofInternal(self, playing):
                self.session.nav.stopService()
                self.close()
                
            def keyCancel(self):
                self.session.nav.stopService()
                self.close()
                
            def keyStop(self):
                self.session.nav.stopService()
                self.close()
                
        def do_open():
            try:
                ref = eServiceReference(4097, 0, stream_url)
                ref.setName(title)
                session.open(TorrPlayer, ref, dl_lang)
            except Exception as e:
                print(f"StarPlay: Error opening player - {e}")
                err_str = traceback.format_exc()
                with open("/tmp/StarPlay_error.log", "w") as f:
                    f.write(err_str)
                session.open(MessageBox, f"TorrPlayer init error: {e}\nSee /tmp/StarPlay_error.log", MessageBox.TYPE_ERROR)
                
        # Store timer as attribute so it doesn't get garbage collected
        session._StarPlay_timer = eTimer()
        try:
            session._StarPlay_timer.callback.append(do_open)
        except Exception:
            session._StarPlay_timer_conn = session._StarPlay_timer.timeout.connect(do_open)
        session._StarPlay_timer.start(100, True)
        
    def on_error(failure):
        def do_err():
            session.open(MessageBox, f"Download thread error: {str(failure.getErrorMessage())}", MessageBox.TYPE_ERROR)
            
        session._StarPlay_timer_err = eTimer()
        try:
            session._StarPlay_timer_err.callback.append(do_err)
        except Exception:
            session._StarPlay_timer_err_conn = session._StarPlay_timer_err.timeout.connect(do_err)
        session._StarPlay_timer_err.start(100, True)

    threads.deferToThread(_start_playback).addCallback(on_success).addErrback(on_error)
