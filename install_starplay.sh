#!/bin/sh
echo "================================================="
echo "   StarPlay Enigma2 Plugin Auto Installer        "
echo "================================================="
echo "Downloading latest version from GitHub..."

wget -qO /tmp/starplay.zip "https://github.com/azroukarim/plugs/archive/refs/heads/main.zip"
if [ $? -ne 0 ]; then
    echo "Download failed! Please check your internet connection."
    exit 1
fi

echo "Extracting files..."
unzip -qo /tmp/starplay.zip -d /tmp/

echo "Installing to /usr/lib/enigma2/python/Plugins/Extensions/StarPlay..."
rm -rf /usr/lib/enigma2/python/Plugins/Extensions/StarPlay
mkdir -p /usr/lib/enigma2/python/Plugins/Extensions/StarPlay
cp -r /tmp/plugs-main/starplay/* /usr/lib/enigma2/python/Plugins/Extensions/StarPlay/

echo "Cleaning up temporary files..."
rm -rf /tmp/starplay.zip /tmp/plugs-main

echo "Installation successful! The system will now restart."
echo "Restarting Enigma2 GUI..."
sleep 2
killall -9 enigma2
exit 0
