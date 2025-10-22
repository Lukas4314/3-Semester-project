import whisper

model = whisper.load_model("base.en")
result = model.transcribe("recording(1).mp3")
print(result["text"])