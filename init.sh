# 1. Create a virtual environment
python3 -m venv venv

# 2. Activate the virtual environment
source venv/bin/activate

# 3. Install Whisper
pip install -U openai-whisper

# 4. Install FFmpeg (system-wide)
sudo apt install ffmpeg -y   # Debian/Ubuntu
# or: sudo dnf install ffmpeg -y   # Fedora
# or: sudo pacman -S ffmpeg        # Arch

# 5. Install setuptools-rust (inside the venv)
pip install setuptools-rust
