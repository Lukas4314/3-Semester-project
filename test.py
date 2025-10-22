import whisper

model = whisper.load_model("base.en")

for i in range(1, 8):
    result = model.transcribe(f"sound_recordings/recording({i}).mp3")
    print(f"Transcription {i}:")
    print(result["text"])
    print()


