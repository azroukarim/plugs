from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from enigma import eSize, ePoint
from twisted.web.client import getPage
import json
from .ui import StarPlayGridScreen
from .__init__ import __version__
from .update import StarPlayUpdateScreen

class StarPlayMainMenu(Screen):
    skin = """
    <screen position="center,center" size="1920,1080" title="StarPlay - Main Menu" backgroundColor="#101010" flags="wfNoBorder">
        <widget name="title" position="0,100" size="1920,80" font="Regular;60" halign="center" valign="center" foregroundColor="#ffffff" transparent="1" />
        
        <!-- Selection border (Yellow) -->
        <widget name="selector" position="560,360" size="380,380" backgroundColor="#ffff00" zPosition="0" />
        
        <!-- Movies Button -->
        <widget name="btn_movies_bg" position="570,370" size="360,360" backgroundColor="#202020" zPosition="1" />
        <widget name="txt_movies" position="570,520" size="360,60" font="Regular;50" halign="center" valign="center" foregroundColor="#ffffff" transparent="1" zPosition="2" />

        <!-- Series Button -->
        <widget name="btn_series_bg" position="990,370" size="360,360" backgroundColor="#202020" zPosition="1" />
        <widget name="txt_series" position="990,520" size="360,60" font="Regular;50" halign="center" valign="center" foregroundColor="#ffffff" transparent="1" zPosition="2" />
        
        <widget name="key_red" position="100,980" zPosition="1" size="200,50" font="Regular;30" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
        <widget name="key_green" position="350,980" zPosition="1" size="200,50" font="Regular;30" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
        <widget name="key_yellow" position="600,980" zPosition="1" size="250,50" font="Regular;30" halign="center" valign="center" backgroundColor="#d1c000" transparent="1" />
    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        
        self["title"] = Label(_(f"StarPlay v{__version__} - Select Category"))
        self["selector"] = Label("")
        
        self["btn_movies_bg"] = Label("")
        self["txt_movies"] = Label(_("Movies"))
        
        self["btn_series_bg"] = Label("")
        self["txt_series"] = Label(_("Series"))
        
        self["key_red"] = Label(_("Close"))
        self["key_green"] = Label(_("Select"))
        self["key_yellow"] = Label("")
        
        # 0 = Movies, 1 = Series
        self.current_idx = 0
        self.update_data = None
        
        self["actions"] = ActionMap(["SetupActions", "DirectionActions", "ColorActions"],
        {
            "ok": self.openGrid,
            "cancel": self.close,
            "red": self.close,
            "green": self.openGrid,
            "yellow": self.openUpdate,
            "left": self.moveLeft,
            "right": self.moveRight
        }, -1)
        
        self.onLayoutFinish.append(self.updateSelector)
        self.onLayoutFinish.append(self.checkForUpdates)

    def updateSelector(self):
        if self.current_idx == 0:
            self["selector"].instance.move(ePoint(560, 360))
        else:
            self["selector"].instance.move(ePoint(980, 360))

    def moveLeft(self):
        if self.current_idx > 0:
            self.current_idx = 0
            self.updateSelector()

    def moveRight(self):
        if self.current_idx < 1:
            self.current_idx = 1
            self.updateSelector()

    def openGrid(self):
        media_type = "movie" if self.current_idx == 0 else "tv"
        self.session.open(StarPlayGridScreen, media_type)

    def checkForUpdates(self):
        url = b"https://raw.githubusercontent.com/azroukarim/plugs/main/version.json"
        getPage(url).addCallback(self.onUpdateChecked).addErrback(self.onUpdateError)
        
    def onUpdateChecked(self, data):
        try:
            data_str = data.decode('utf-8') if isinstance(data, bytes) else data
            info = json.loads(data_str)
            remote_version = info.get("version", "1.0")
            if remote_version != __version__:
                self.update_data = info
                self["key_yellow"].setText(_("Update Available"))
        except Exception as e:
            print(f"[StarPlay] Error parsing version.json: {e}")
            
    def onUpdateError(self, error):
        print(f"[StarPlay] Failed to check for updates: {error}")
        
    def openUpdate(self):
        if self.update_data:
            self.session.open(StarPlayUpdateScreen, self.update_data.get("version"), self.update_data.get("changelog", "No details"))
