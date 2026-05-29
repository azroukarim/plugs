from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigListScreen
from Components.config import config, ConfigSubsection, ConfigYesNo, ConfigSelection, getConfigListEntry
import os

# Initialize plugin config
config.plugins.StarPlay = ConfigSubsection()
config.plugins.StarPlay.subs_enable = ConfigYesNo(default=True)
config.plugins.StarPlay.subs_lang = ConfigSelection(default="ar", choices=[
    ("ar", _("Arabic")),
    ("en", _("English")),
    ("fr", _("French")),
    ("es", _("Spanish")),
    ("de", _("German")),
    ("it", _("Italian")),
    ("pt", _("Portuguese")),
    ("tr", _("Turkish")),
])
config.plugins.StarPlay.subs_color = ConfigSelection(default="#FFFFFF", choices=[
    ("#FFFFFF", _("White")),
    ("#FFFF00", _("Yellow")),
    ("#00FFFF", _("Cyan")),
    ("#00FF00", _("Green")),
])

class StarPlaySettingsScreen(Screen, ConfigListScreen):
    skin = """
    <screen position="center,center" size="1000,600" title="StarPlay Settings" backgroundColor="#101010" flags="wfNoBorder">
        <widget name="config" position="50,50" size="900,400" scrollbarMode="showOnDemand" font="Regular;35" itemHeight="50" transparent="1" />
        
        <ePixmap pixmap="skin_default/buttons/red.png" position="50,500" size="40,40" alphatest="on" />
        <widget name="key_red" position="100,500" size="200,40" font="Regular;30" halign="left" valign="center" foregroundColor="#ffffff" transparent="1" />
        
        <ePixmap pixmap="skin_default/buttons/green.png" position="350,500" size="40,40" alphatest="on" />
        <widget name="key_green" position="400,500" size="200,40" font="Regular;30" halign="left" valign="center" foregroundColor="#ffffff" transparent="1" />
    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        
        self.list = []
        ConfigListScreen.__init__(self, self.list)
        
        self.createSetup()
        
        from Components.Label import Label
        self["key_red"] = Label(_("Cancel"))
        self["key_green"] = Label(_("Save"))
        
        self["actions"] = ActionMap(["SetupActions", "ColorActions"], {
            "green": self.save,
            "red": self.cancel,
            "cancel": self.cancel,
            "ok": self.save
        }, -2)
        
    def createSetup(self):
        self.list = []
        self.list.append(getConfigListEntry(_("Enable Subtitle Download"), config.plugins.StarPlay.subs_enable))
        self.list.append(getConfigListEntry(_("Subtitle Language"), config.plugins.StarPlay.subs_lang))
        self.list.append(getConfigListEntry(_("Subtitle Color"), config.plugins.StarPlay.subs_color))
        self["config"].list = self.list
        self["config"].l.setList(self.list)
        
    def save(self):
        for x in self["config"].list:
            x[1].save()
        config.plugins.StarPlay.save()
        self.close()
        
    def cancel(self):
        for x in self["config"].list:
            x[1].cancel()
        self.close()
