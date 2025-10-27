python -m venv venv

call venv\Scripts\activate.bat

pip install -U openai-whisper
scoop install ffmpeg
pip install setuptools-rust
pip install paho-mqtt
pip install sounddevice