#!/bin/bash

set -e

if [ ! -d "env" ]; then
    echo "Please run './PolGen-Installer.sh' first to set up the environment."
    exit 1
fi

check_internet_connection() {
    echo "Checking internet connection..."
    if ping -c 1 google.com &> /dev/null; then
        echo "Internet connection is available."
        INTERNET_AVAILABLE=1
    else
        echo "No internet connection detected."
        INTERNET_AVAILABLE=0
    fi
    echo
}

running_interface() {
    echo "Running Interface..."
    if [ "$INTERNET_AVAILABLE" -eq 1 ]; then
        echo "Running app.py in ONLINE mode..."
        "./env/bin/python" app.py
    else
        echo "Running app.py in OFFLINE mode..."
        "./env/bin/python" app.py --offline
    fi
}

check_internet_connection
running_interface
