python -m venv venv

call venv\Scripts\activate.bat

scoop install ffmpeg


pip install -U openai-whisper
pip install setuptools-rust
pip install paho-mqtt
pip install sounddevice
pip install torchaudio
pip install scipy