from Plugins.Plugin import PluginDescriptor
from .menu import StarPlayMainMenu

def main(session, **kwargs):
    session.open(StarPlayMainMenu)

def Plugins(**kwargs):
    return [
        PluginDescriptor(
            name="StarPlay",
            description="Play movies and series via IMDb ID",
            where=PluginDescriptor.WHERE_PLUGINMENU,
            icon="plugin.png",
            fnc=main
        )
    ]
