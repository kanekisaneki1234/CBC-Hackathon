"""
Configuration management for the Zoom Meeting Assistant
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Application configuration"""

    # API Keys
    ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY", "")
    DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

    # Transcription settings
    TRANSCRIPTION_SERVICE = os.getenv("TRANSCRIPTION_SERVICE", "assemblyai")

    # Summary settings
    SUMMARY_INTERVAL_MINUTES = int(os.getenv("SUMMARY_INTERVAL_MINUTES", "5"))
    CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

    # Google Meet settings
    MEET_DISPLAY_NAME = os.getenv("MEET_DISPLAY_NAME", "Meeting Assistant Bot")

    # Directories
    BASE_DIR = Path(__file__).parent.parent
    EXPORTS_DIR = BASE_DIR / "exports"
    LOGS_DIR = BASE_DIR / "logs"

    # Audio settings
    SAMPLE_RATE = 16000  # 16kHz for speech recognition
    CHANNELS = 1  # Mono

    @classmethod
    def validate(cls):
        """Validate required configuration"""
        errors = []

        if not cls.ANTHROPIC_API_KEY:
            errors.append("ANTHROPIC_API_KEY is required")

        if cls.TRANSCRIPTION_SERVICE == "assemblyai" and not cls.ASSEMBLYAI_API_KEY:
            errors.append("ASSEMBLYAI_API_KEY is required for AssemblyAI transcription")
        elif cls.TRANSCRIPTION_SERVICE == "deepgram" and not cls.DEEPGRAM_API_KEY:
            errors.append("DEEPGRAM_API_KEY is required for Deepgram transcription")

        if errors:
            raise ValueError(f"Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))

        # Create directories
        cls.EXPORTS_DIR.mkdir(exist_ok=True)
        cls.LOGS_DIR.mkdir(exist_ok=True)

        return True
