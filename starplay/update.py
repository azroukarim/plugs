from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from enigma import eConsoleAppContainer

class StarPlayUpdateScreen(Screen):
    skin = """
    <screen position="0,0" size="1920,1080" title="StarPlay Update Available" backgroundColor="#101010" flags="wfNoBorder">
        <widget name="title" position="0,100" size="1920,80" font="Regular;60" halign="center" valign="center" foregroundColor="#ffffff" transparent="1" />
        <widget name="changelog" position="200,250" size="1520,600" font="Regular;40" halign="left" valign="top" foregroundColor="#cccccc" transparent="1" />
        
        <widget name="key_red" position="300,950" zPosition="1" size="400,70" font="Regular;40" halign="center" valign="center" backgroundColor="#9f1313" foregroundColor="#ffffff" transparent="0" />
        <widget name="key_green" position="1220,950" zPosition="1" size="400,70" font="Regular;40" halign="center" valign="center" backgroundColor="#1f771f" foregroundColor="#ffffff" transparent="0" />
    </screen>
    """

    def __init__(self, session, new_version, changelog):
        Screen.__init__(self, session)
        self.session = session
        
        self["title"] = Label(f"New Update Available: v{new_version}")
        self["changelog"] = Label(f"Changelog:\n\n{changelog}")
        
        self["key_red"] = Label(_("Cancel"))
        self["key_green"] = Label(_("Update Now"))
        
        self["actions"] = ActionMap(["SetupActions", "ColorActions"],
        {
            "cancel": self.close,
            "red": self.close,
            "green": self.startUpdate
        }, -1)
        
        self.container = eConsoleAppContainer()

    def startUpdate(self):
        self["title"].setText("Downloading and installing... Please wait")
        self["changelog"].setText("The system will restart automatically after the update is finished.\nDo not turn off your device.")
        self["key_green"].hide()
        self["key_red"].hide()
        
        # We disable actions to prevent interrupting the update
        self["actions"].setEnabled(False)
        
        # Execute the update script
        cmd = 'wget -q "--no-check-certificate" https://raw.githubusercontent.com/azroukarim/plugs/refs/heads/main/install_starplay.sh -O - | /bin/sh'
        self.container.execute(cmd)
