"""
Real-time transcription using AssemblyAI or Deepgram
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional, Callable, Dict, Any
import queue
import threading
import json

try:
    import assemblyai as aai
except ImportError:
    aai = None

try:
    from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions
except ImportError:
    DeepgramClient = None

from .config import Config

logger = logging.getLogger(__name__)


class TranscriptionService(ABC):
    """Abstract base class for transcription services"""

    def __init__(self, on_transcript: Optional[Callable] = None):
        self.on_transcript = on_transcript
        self.is_active = False

    @abstractmethod
    async def start(self):
        """Start the transcription service"""
        pass

    @abstractmethod
    async def send_audio(self, audio_data: bytes):
        """Send audio data for transcription"""
        pass

    @abstractmethod
    async def stop(self):
        """Stop the transcription service"""
        pass


class AssemblyAITranscriber(TranscriptionService):
    """Real-time transcription using AssemblyAI"""

    def __init__(self, on_transcript: Optional[Callable] = None):
        super().__init__(on_transcript)

        if not aai:
            raise ImportError("AssemblyAI package not installed. Run: pip install assemblyai")

        if not Config.ASSEMBLYAI_API_KEY:
            raise ValueError("ASSEMBLYAI_API_KEY not set in environment")

        aai.settings.api_key = Config.ASSEMBLYAI_API_KEY
        self.transcriber = None

    async def start(self):
        """Start AssemblyAI real-time transcription"""
        try:
            logger.info("Starting AssemblyAI transcription...")

            def on_open(session_opened: aai.RealtimeSessionOpened):
                logger.info(f"AssemblyAI session opened: {session_opened.session_id}")

            def on_data(transcript: aai.RealtimeTranscript):
                if not transcript.text:
                    return

                if isinstance(transcript, aai.RealtimeFinalTranscript):
                    # Final transcript with punctuation
                    result = {
                        "text": transcript.text,
                        "is_final": True,
                        "confidence": getattr(transcript, "confidence", None),
                    }

                    if self.on_transcript:
                        self.on_transcript(result)

            def on_error(error: aai.RealtimeError):
                logger.error(f"AssemblyAI error: {error}")

            def on_close():
                logger.info("AssemblyAI session closed")

            # Create transcriber with callbacks
            self.transcriber = aai.RealtimeTranscriber(
                sample_rate=Config.SAMPLE_RATE,
                on_open=on_open,
                on_data=on_data,
                on_error=on_error,
                on_close=on_close,
            )

            # Connect to AssemblyAI
            self.transcriber.connect()
            self.is_active = True
            logger.info("AssemblyAI transcription started")

        except Exception as e:
            logger.error(f"Error starting AssemblyAI: {e}")
            raise

    async def send_audio(self, audio_data: bytes):
        """Send audio data to AssemblyAI"""
        if not self.is_active or not self.transcriber:
            return

        try:
            # AssemblyAI expects raw PCM audio bytes
            if hasattr(audio_data, "tobytes"):
                audio_bytes = audio_data.tobytes()
            else:
                audio_bytes = audio_data

            self.transcriber.stream(audio_bytes)

        except Exception as e:
            logger.error(f"Error sending audio to AssemblyAI: {e}")

    async def stop(self):
        """Stop AssemblyAI transcription"""
        if not self.is_active:
            return

        try:
            logger.info("Stopping AssemblyAI transcription...")

            if self.transcriber:
                self.transcriber.close()

            self.is_active = False
            logger.info("AssemblyAI transcription stopped")

        except Exception as e:
            logger.error(f"Error stopping AssemblyAI: {e}")


class DeepgramTranscriber(TranscriptionService):
    """Real-time transcription using Deepgram"""

    def __init__(self, on_transcript: Optional[Callable] = None):
        super().__init__(on_transcript)

        if not DeepgramClient:
            raise ImportError("Deepgram package not installed. Run: pip install deepgram-sdk")

        if not Config.DEEPGRAM_API_KEY:
            raise ValueError("DEEPGRAM_API_KEY not set in environment")

        self.client = DeepgramClient(Config.DEEPGRAM_API_KEY)
        self.connection = None

    async def start(self):
        """Start Deepgram real-time transcription"""
        try:
            logger.info("Starting Deepgram transcription...")

            # Create connection
            self.connection = self.client.listen.live.v("1")

            def on_message(self, result, **kwargs):
                try:
                    sentence = result.channel.alternatives[0].transcript

                    if len(sentence) == 0:
                        return

                    is_final = result.is_final

                    transcript_result = {
                        "text": sentence,
                        "is_final": is_final,
                        "confidence": result.channel.alternatives[0].confidence,
                    }

                    if self.on_transcript:
                        self.on_transcript(transcript_result)

                except Exception as e:
                    logger.error(f"Error processing Deepgram message: {e}")

            def on_error(self, error, **kwargs):
                logger.error(f"Deepgram error: {error}")

            def on_close(self, **kwargs):
                logger.info("Deepgram connection closed")

            # Register callbacks
            self.connection.on(LiveTranscriptionEvents.Transcript, on_message)
            self.connection.on(LiveTranscriptionEvents.Error, on_error)
            self.connection.on(LiveTranscriptionEvents.Close, on_close)

            # Configure options
            options = LiveOptions(
                model="nova-2",
                language="en",
                smart_format=True,
                encoding="linear16",
                sample_rate=Config.SAMPLE_RATE,
                channels=Config.CHANNELS,
            )

            # Start connection
            await self.connection.start(options)
            self.is_active = True
            logger.info("Deepgram transcription started")

        except Exception as e:
            logger.error(f"Error starting Deepgram: {e}")
            raise

    async def send_audio(self, audio_data: bytes):
        """Send audio data to Deepgram"""
        if not self.is_active or not self.connection:
            return

        try:
            # Convert numpy array to bytes if needed
            if hasattr(audio_data, "tobytes"):
                audio_bytes = audio_data.tobytes()
            else:
                audio_bytes = audio_data

            await self.connection.send(audio_bytes)

        except Exception as e:
            logger.error(f"Error sending audio to Deepgram: {e}")

    async def stop(self):
        """Stop Deepgram transcription"""
        if not self.is_active:
            return

        try:
            logger.info("Stopping Deepgram transcription...")

            if self.connection:
                await self.connection.finish()

            self.is_active = False
            logger.info("Deepgram transcription stopped")

        except Exception as e:
            logger.error(f"Error stopping Deepgram: {e}")


class TranscriptionManager:
    """Manages transcription with the configured service"""

    def __init__(self, on_transcript: Optional[Callable] = None):
        self.on_transcript = on_transcript
        self.service: Optional[TranscriptionService] = None
        self.transcript_buffer = []

    async def initialize(self):
        """Initialize the transcription service"""
        service_name = Config.TRANSCRIPTION_SERVICE.lower()

        logger.info(f"Initializing transcription service: {service_name}")

        if service_name == "assemblyai":
            self.service = AssemblyAITranscriber(on_transcript=self._handle_transcript)
        elif service_name == "deepgram":
            self.service = DeepgramTranscriber(on_transcript=self._handle_transcript)
        else:
            raise ValueError(f"Unknown transcription service: {service_name}")

        await self.service.start()

    def _handle_transcript(self, result: Dict[str, Any]):
        """Handle transcript from service"""
        # Add to buffer
        self.transcript_buffer.append(result)

        # Call user callback
        if self.on_transcript:
            self.on_transcript(result)

    async def transcribe_audio(self, audio_data: bytes):
        """Send audio for transcription"""
        if self.service:
            await self.service.send_audio(audio_data)

    async def stop(self):
        """Stop transcription"""
        if self.service:
            await self.service.stop()

    def get_full_transcript(self, final_only: bool = True) -> str:
        """
        Get full transcript text

        Args:
            final_only: If True, only include final transcripts

        Returns:
            Combined transcript text
        """
        if final_only:
            texts = [t["text"] for t in self.transcript_buffer if t.get("is_final", False)]
        else:
            texts = [t["text"] for t in self.transcript_buffer]

        return " ".join(texts)

    def clear_buffer(self):
        """Clear transcript buffer"""
        self.transcript_buffer.clear()

    def get_recent_transcript(self, minutes: int = 5) -> str:
        """
        Get transcript from last N minutes

        Note: This is a simplified version - for production, you'd want to
        track timestamps and filter based on actual time
        """
        # For now, return all transcripts (timestamp tracking can be added later)
        return self.get_full_transcript(final_only=True)
