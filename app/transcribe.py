import openai
import os
from typing import Tuple
from dotenv import load_dotenv
from moviepy.editor import AudioFileClip, VideoFileClip
from faster_whisper import WhisperModel

load_dotenv()

class AudioProcessor:
    def __init__(self):
        # Initialize Whisper model (using base model for balance of speed and accuracy)
        self.whisper_model = WhisperModel("small", device="cpu")
        
        # Initialize OpenAI client for summarization
        openai.api_key = os.getenv("OPENAI_API_KEY")
        if not openai.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
    
    def transcribe_audio(self, audio_path: str) -> str:
        """Transcribe audio file using Faster Whisper"""
        try:
            # Transcribe audio and get segments
            segments, info = self.whisper_model.transcribe(audio_path)
            
            # Collect all transcribed text
            transcription_text = []
            for segment in segments:
                print(f"[{segment.start:.2f}s → {segment.end:.2f}s] {segment.text}")
                transcription_text.append(segment.text)
            
            # Join all segments into a single string
            return " ".join(transcription_text)
        except Exception as e:
            raise Exception(f"Error transcribing audio: {str(e)}")
    
    def summarize_text(self, text: str) -> str:
        """Summarize transcribed text using OpenAI GPT"""
        try:
            response = openai.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that creates concise, informative summaries of transcribed audio content. Focus on the key points, main topics, and important details."
                    },
                    {
                        "role": "user",
                        "content": f"Please provide a comprehensive summary of the following transcribed audio content:\n\n{text}"
                    }
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise Exception(f"Error summarizing text: {str(e)}")
    
    def process_audio(self, audio_path: str) -> Tuple[str, str]:
        """Complete audio processing pipeline: transcribe and summarize"""
        try:
            # Step 1: Transcribe the audio
            transcription = self.transcribe_audio(audio_path)
            
            # Step 2: Summarize the transcription
            summary = self.summarize_text(transcription)
            
            return transcription, summary
        except Exception as e:
            raise Exception(f"Error processing audio: {str(e)}")
        

    def get_media_duration(self, file_path: str) -> str:
        """
        Return the duration of an audio file as MM:SS (zero-padded).
        """
        clip = AudioFileClip(file_path)
        
        duration_seconds = int(clip.duration)  # get total seconds
        clip.close()

        minutes, seconds = divmod(duration_seconds, 60)
        return f"{minutes:02d}:{seconds:02d}"
