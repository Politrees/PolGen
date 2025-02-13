#!/bin/bash

set -e

echo "Welcome to the PolGen Installer!"
echo

PRINCIPAL=$(pwd)
MINICONDA_DIR="$HOME/miniconda3"
ENV_DIR="$PRINCIPAL/env"
MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-py310_24.11.1-0-Linux-x86_64.sh"
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
    "$MINICONDA_DIR/bin/conda" create --yes --prefix "$ENV_DIR" python=3.10
    if [ $? -ne 0 ]; then
        echo "An error occurred during environment creation."
        exit 1
    fi

    if [ -f "$ENV_DIR/bin/python" ]; then
        echo "Installing specific pip version..."
        "$ENV_DIR/bin/python" -m pip install "pip<24.1"
        if [ $? -ne 0 ]; then
            echo "Pip installation failed."
            exit 1
        fi
        echo "Pip installation complete."
        echo
    fi
}

install_dependencies() {
    echo "Installing dependencies..."
    source "$MINICONDA_DIR/etc/profile.d/conda.sh"
    conda activate "$ENV_DIR"
    pip install --upgrade setuptools
    pip install -r "$PRINCIPAL/requirements.txt"
    pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --upgrade --index-url https://download.pytorch.org/whl/cu121
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

installing_necessary_models() {
    echo "Checking for required models..."
    HUBERT_BASE="$PRINCIPAL/PolGen/rvc/models/embedders/hubert_base.pt"
    FCPE="$PRINCIPAL/PolGen/rvc/models/predictors/fcpe.pt"
    RMVPE="$PRINCIPAL/PolGen/rvc/models/predictors/rmvpe.pt"

    if [ -f "$HUBERT_BASE" ] && [ -f "$FCPE" ] && [ -f "$RMVPE" ]; then
        echo "All required models are installed."
    else
        echo "Required models were not found. Installing models..."
        "$ENV_DIR/bin/python" download_models.py
        if [ $? -ne 0 ]; then
            echo "Model installation failed."
            exit 1
        fi
    fi
    echo
}

install_miniconda
create_conda_env
install_dependencies
install_ffmpeg
installing_necessary_models

echo "PolGen has been installed successfully!"
echo "To start PolGen, please run './PolGen.sh'."
echo
