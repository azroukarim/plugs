from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from enigma import eConsoleAppContainer

class StarPlayUpdateScreen(Screen):
    skin = """
    <screen position="center,center" size="1000,600" title="StarPlay Update Available" backgroundColor="#101010" flags="wfNoBorder">
        <widget name="title" position="0,20" size="1000,60" font="Regular;40" halign="center" valign="center" foregroundColor="#ffffff" transparent="1" />
        <widget name="changelog" position="50,100" size="900,380" font="Regular;28" halign="left" valign="top" foregroundColor="#cccccc" transparent="1" />
        
        <widget name="key_red" position="200,520" zPosition="1" size="250,50" font="Regular;30" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
        <widget name="key_green" position="550,520" zPosition="1" size="250,50" font="Regular;30" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
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
