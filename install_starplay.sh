#!/bin/bash

URL="https://github.com/azroukarim/plugs/raw/refs/heads/main/starplay.tar.gz"
TMP_DIR="/tmp"
PLUGINS_PATH="/usr/lib/enigma2/python/Plugins/Extensions"

clear > /dev/null 2>&1

# Check and install wget
package="wget"
if ! opkg list-installed | grep -q "^$package"; then
    if [ -f /etc/apt/apt.conf ]; then
        apt-get update >/dev/null 2>&1
        apt install $package -y >/dev/null 2>&1
    else
        opkg update > /dev/null 2>&1
        opkg install $package >/dev/null 2>&1
    fi
fi

# Download archive
echo "> Downloading StarPlay ..."
if wget -q --no-check-certificate "$URL" -O "$TMP_DIR/starplay.tar.gz"; then
    echo "> Extracting ..."
    tar -xzf "$TMP_DIR/starplay.tar.gz" -C "$TMP_DIR"

    # Find extracted folder
    EXTRACTED_DIR=$(tar -tzf "$TMP_DIR/starplay.tar.gz" | head -1 | cut -d'/' -f1)

    if [ -d "$TMP_DIR/$EXTRACTED_DIR" ]; then
        echo "> Installing to $PLUGINS_PATH ..."
        mkdir -p "$PLUGINS_PATH"
        cp -rf "$TMP_DIR/$EXTRACTED_DIR" "$PLUGINS_PATH/"
    fi

    # Cleanup
    echo "> Cleaning up ..."
    rm -rf "$TMP_DIR/starplay.tar.gz" "$TMP_DIR/$EXTRACTED_DIR"

    # Restart
    echo "> Restarting ..."
    if command -v killall &> /dev/null; then
        killall -9 enigma2
    elif command -v init &> /dev/null; then
        init 4
        sleep 2
        init 3
    else
        reboot
    fi
else
    echo "> Download failed. Check your internet connection."
    exit 1
fi
