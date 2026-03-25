#!/bin/bash

set -e

echo "Welcome to the PolGen Installer!"
echo

PRINCIPAL=$(pwd)
MINICONDA_DIR="$HOME/miniconda3"
ENV_DIR="$PRINCIPAL/env"
MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-py311_25.1.1-2-Linux-x86_64.sh"
CONDA_EXE="$MINICONDA_DIR/bin/conda"

install_miniconda() {
    if [ -d "$MINICONDA_DIR" ]; then
        echo "Miniconda already installed. Skipping installation."
        return
    fi

    echo "Miniconda not found. Starting download and installation..."
    wget -O miniconda.sh "$MINICONDA_URL"
    if [ ! -f "miniconda.sh" ]; then
        echo "Download failed. Please check your internet connection and try again."
        exit 1
    fi

    bash miniconda.sh -b -p "$MINICONDA_DIR"
    if [ $? -ne 0 ]; then
        echo "Miniconda installation failed."
        exit 1
    fi

    rm miniconda.sh
    echo "Miniconda installation complete."
    echo
}

create_conda_env() {
    echo "Creating Conda environment..."
    "$MINICONDA_DIR/bin/conda" create --yes --prefix "$ENV_DIR" python=3.11
    if [ $? -ne 0 ]; then
        echo "An error occurred during environment creation."
        exit 1
    fi
}

install_dependencies() {
    echo "Installing dependencies..."
    source "$MINICONDA_DIR/etc/profile.d/conda.sh"
    conda activate "$ENV_DIR"
    pip install --upgrade setuptools
    pip install torch==2.7.1 torchaudio==2.7.1 torchvision==0.22.1 --upgrade --index-url https://download.pytorch.org/whl/cu128
    pip install -r "$PRINCIPAL/requirements.txt"
    conda deactivate
    echo "Dependencies installation complete."
    echo
}

install_ffmpeg() {
    if command -v brew > /dev/null; then
        echo "Installing FFmpeg using Homebrew on macOS..."
        brew install ffmpeg
    elif command -v apt > /dev/null; then
        echo "Installing FFmpeg using apt..."
        sudo apt update && sudo apt install -y ffmpeg
    elif command -v pacman > /dev/null; then
        echo "Installing FFmpeg using pacman..."
        sudo pacman -Syu --noconfirm ffmpeg
    elif command -v dnf > /dev/null; then
        echo "Installing FFmpeg using dnf..."
        sudo dnf install -y ffmpeg --allowerasing || install_ffmpeg_flatpak
    else
        echo "Unsupported distribution for FFmpeg installation. Trying Flatpak..."
        install_ffmpeg_flatpak
    fi
}

install_ffmpeg_flatpak() {
    if command -v flatpak > /dev/null; then
        echo "Installing FFmpeg using Flatpak..."
        flatpak install --user -y flathub org.freedesktop.Platform.ffmpeg
    else
        echo "Flatpak is not installed. Installing Flatpak..."
        if command -v apt > /dev/null; then
            sudo apt install -y flatpak
        elif command -v pacman > /dev/null; then
            sudo pacman -Syu --noconfirm flatpak
        elif command -v dnf > /dev/null; then
            sudo dnf install -y flatpak
        elif command -v brew > /dev/null; then
            brew install flatpak
        else
            echo "Unable to install Flatpak automatically. Please install Flatpak and try again."
            exit 1
        fi
        flatpak install --user -y flathub org.freedesktop.Platform.ffmpeg
    fi
}

install_miniconda
create_conda_env
install_dependencies
install_ffmpeg

echo "PolGen has been installed successfully!"
echo "To start PolGen, please run './run-PolGen.sh'."
echo
