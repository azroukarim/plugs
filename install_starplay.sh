#!/bin/bash

# --- Colors ---
R='\033[1;31m'
G='\033[1;32m'
Y='\033[1;33m'
B='\033[1;34m'
C='\033[1;36m'
W='\033[1;37m'
NC='\033[0m' # No Color

URL="https://github.com/azroukarim/plugs/raw/refs/heads/main/starplay.tar.gz"
TMP_DIR="/tmp"
PLUGINS_PATH="/usr/lib/enigma2/python/Plugins/Extensions"

clear > /dev/null 2>&1

echo -e "${C}"
echo "  ██████  ████████  █████  ██████  ██▓███   ██▓     ▄▄▄       ██▓███  "
echo "▒██    ▒  ▓  ██▒ ▓▒██▓  ██▒██   ██▒▓██░  ██▒▓██▒    ▒████▄    ▓██░  ██▒"
echo "░ ▓██▄    ▒ ▓██░ ▒░██▒  ██░██████▒▒▓██░ ██▓▒▒██░    ▒██  ▀█▄  ▓██░ ██▓▒"
echo "  ▒   ██▒ ░ ▓██▓ ░░██  █▀ ░██  ▀██▒▒██▄█▓▒ ▒▒██░    ░██▄▄▄▄██ ▒██▄█▓▒ ▒"
echo "▒██████▒▒   ▒██▒ ░░▒███▒█▄░██▓  ██▒▒██▒ ░  ░░██████▒ ▓█   ▓██▒▒██▒ ░  ░"
echo "▒ ▒▓▒ ▒ ░   ▒ ░░  ░░ ▒▒░ ▒░ ▒▓ ░▒▓░▒▓▒░ ░  ░░ ▒░▓  ░ ▒▒   ▓▒█░▒▓▒░ ░  ░"
echo "░ ░▒  ░ ░     ░    ░ ▒░  ░  ░▒ ░ ▒░░▒ ░     ░ ░ ▒  ░  ▒   ▒▒ ░░▒ ░     "
echo "░  ░  ░     ░        ░   ░  ░░   ░ ░░         ░ ░     ░   ▒   ░░       "
echo "      ░               ░      ░                  ░  ░      ░  ░         "
echo -e "${NC}"
echo -e "${W}=======================================================================${NC}"
echo -e "${Y}                 StarPlay Plugin Installer                             ${NC}"
echo -e "${W}=======================================================================${NC}\n"


echo -e "${B}[*] ${W}Checking for required dependencies...${NC}"

# Function to install missing packages
install_pkg() {
    if ! opkg list-installed | grep -q "^$1"; then
        echo -e "${Y}    - Installing $1...${NC}"
        opkg install $1 >/dev/null 2>&1
    else
        echo -e "${G}    - $1 is already installed.${NC}"
    fi
}

install_pkg "wget"
install_pkg "gstreamer1.0"
install_pkg "gstreamer1.0-plugins-base"
install_pkg "gstreamer1.0-plugins-good"
install_pkg "enigma2-plugin-systemplugins-serviceapp"
install_pkg "exteplayer3"

echo -e "\n${B}[*] ${W}Downloading StarPlay Archive...${NC}"
if wget -q --no-check-certificate "$URL" -O "$TMP_DIR/starplay.tar.gz"; then
    echo -e "${G}[+] Download successful.${NC}\n"
    
    echo -e "${B}[*] ${W}Extracting files...${NC}"
    tar -xzf "$TMP_DIR/starplay.tar.gz" -C "$TMP_DIR"

    EXTRACTED_DIR=$(tar -tzf "$TMP_DIR/starplay.tar.gz" | head -1 | cut -d'/' -f1)

    if [ -d "$TMP_DIR/$EXTRACTED_DIR" ]; then
        echo -e "${B}[*] ${W}Installing to Enigma2 Plugins directory...${NC}"
        rm -rf "$PLUGINS_PATH/StarPlay"
        rm -rf "$PLUGINS_PATH/starplay"
        mkdir -p "$PLUGINS_PATH"
        cp -rf "$TMP_DIR/$EXTRACTED_DIR" "$PLUGINS_PATH/StarPlay"
    fi

    echo -e "${B}[*] ${W}Cleaning up temporary files...${NC}"
    rm -rf "$TMP_DIR/starplay.tar.gz" "$TMP_DIR/$EXTRACTED_DIR"
    
    echo -e "\n${G}=======================================================================${NC}"
    echo -e "${G}         StarPlay has been successfully installed/updated!             ${NC}"
    echo -e "${G}=======================================================================${NC}\n"
    
    echo -e "${Y}[!] Restarting Enigma2 GUI in 3 seconds...${NC}"
    sleep 3
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
    echo -e "\n${R}[!] Download failed. Please check your internet connection.${NC}"
    exit 1
fi
