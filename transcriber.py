import whisper


class Transcriber:
    def __init__(self, model):
        self.model = model

    def transcribe(self, audio_file):
        # Load the audio file
        
        # Process the audio data with the model
        transcription = self.model.transcribe(audio_file)
        
        return transcription

        