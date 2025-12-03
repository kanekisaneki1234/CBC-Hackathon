"""
Main meeting manager that orchestrates all components
"""
import asyncio
import logging
from typing import Optional, Callable, Dict, Any
from datetime import datetime, timedelta
from .meet_joiner import MeetJoiner
from .audio_capture import AudioCapturer
from .transcription import TranscriptionManager
from .summarizer import MeetingSummarizer
from .config import Config

logger = logging.getLogger(__name__)


class MeetingAssistant:
    """
    Main orchestrator for the Google Meet Assistant

    Coordinates:
    - Joining Google Meet meetings
    - Capturing audio
    - Real-time transcription
    - Periodic AI summaries
    """

    def __init__(
        self,
        on_transcript: Optional[Callable] = None,
        on_summary: Optional[Callable] = None,
        on_status_change: Optional[Callable] = None,
    ):
        """
        Initialize the meeting assistant

        Args:
            on_transcript: Callback for new transcript segments
            on_summary: Callback for new summaries
            on_status_change: Callback for status changes
        """
        self.on_transcript = on_transcript
        self.on_summary = on_summary
        self.on_status_change = on_status_change

        # Components
        self.meet_joiner: Optional[MeetJoiner] = None
        self.audio_capturer: Optional[AudioCapturer] = None
        self.transcription_manager: Optional[TranscriptionManager] = None
        self.summarizer: Optional[MeetingSummarizer] = None

        # State
        self.is_running = False
        self.meeting_start_time: Optional[datetime] = None
        self.last_summary_time: Optional[datetime] = None

        # Tasks
        self._audio_task: Optional[asyncio.Task] = None
        self._summary_task: Optional[asyncio.Task] = None

        # Stats
        self.stats = {
            "transcripts_received": 0,
            "summaries_generated": 0,
            "errors": 0,
        }

    def _update_status(self, status: str, details: Optional[str] = None):
        """Update and broadcast status"""
        logger.info(f"Status: {status}" + (f" - {details}" if details else ""))

        if self.on_status_change:
            self.on_status_change({"status": status, "details": details, "timestamp": datetime.now().isoformat()})

    async def initialize(self):
        """Initialize all components"""
        try:
            self._update_status("initializing", "Setting up components...")

            # Validate configuration
            Config.validate()

            # Initialize transcription manager
            self._update_status("initializing", "Setting up transcription service...")
            self.transcription_manager = TranscriptionManager(on_transcript=self._handle_transcript)
            await self.transcription_manager.initialize()

            # Initialize summarizer
            self._update_status("initializing", "Setting up AI summarizer...")
            self.summarizer = MeetingSummarizer(on_summary=self._handle_summary)

            # Initialize Google Meet joiner
            self._update_status("initializing", "Setting up Google Meet integration...")
            self.meet_joiner = MeetJoiner()
            await self.meet_joiner.initialize()

            # Initialize audio capturer
            self._update_status("initializing", "Setting up audio capture...")
            self.audio_capturer = AudioCapturer()

            self._update_status("ready", "All components initialized")
            logger.info("Meeting assistant initialized successfully")

        except Exception as e:
            self._update_status("error", f"Initialization failed: {e}")
            logger.error(f"Error initializing meeting assistant: {e}")
            raise

    async def start_meeting(
        self, meeting_url: str, password: Optional[str] = None, audio_device_id: Optional[int] = None
    ):
        """
        Join meeting and start transcription

        Args:
            meeting_url: Google Meet meeting URL
            password: Optional meeting password (not used for Google Meet)
            audio_device_id: Optional specific audio device to use
        """
        if self.is_running:
            logger.warning("Meeting already in progress")
            return

        try:
            self._update_status("joining", "Joining Google Meet meeting...")

            # Join Google Meet meeting
            success = await self.meet_joiner.join_meeting(meeting_url, password)

            if not success:
                self._update_status("error", "Failed to join meeting")
                return

            self._update_status("in_meeting", "Successfully joined meeting")
            self.is_running = True
            self.meeting_start_time = datetime.now()
            self.last_summary_time = datetime.now()

            # Start audio capture
            self._update_status("in_meeting", "Starting audio capture...")
            self.audio_capturer.start_capture(device_id=audio_device_id)

            # Start audio processing loop
            self._audio_task = asyncio.create_task(self._audio_processing_loop())

            # Start summary generation loop
            self._summary_task = asyncio.create_task(self._summary_loop())

            self._update_status("recording", "Recording and transcribing meeting...")
            logger.info("Meeting started successfully")

        except Exception as e:
            self._update_status("error", f"Error starting meeting: {e}")
            logger.error(f"Error starting meeting: {e}")
            self.stats["errors"] += 1
            raise

    async def _audio_processing_loop(self):
        """Process audio and send to transcription"""
        logger.info("Starting audio processing loop...")

        try:
            while self.is_running:
                # Get audio chunk from capturer
                audio_chunk = self.audio_capturer.get_audio_chunk(timeout=0.5)

                if audio_chunk is not None:
                    # Send to transcription service
                    await self.transcription_manager.transcribe_audio(audio_chunk)

                await asyncio.sleep(0.01)  # Small delay to prevent busy waiting

        except Exception as e:
            logger.error(f"Error in audio processing loop: {e}")
            self.stats["errors"] += 1
            self._update_status("error", f"Audio processing error: {e}")

    async def _summary_loop(self):
        """Generate summaries at regular intervals"""
        logger.info("Starting summary generation loop...")

        interval = timedelta(minutes=Config.SUMMARY_INTERVAL_MINUTES)

        try:
            while self.is_running:
                await asyncio.sleep(10)  # Check every 10 seconds

                if not self.last_summary_time:
                    continue

                time_since_last = datetime.now() - self.last_summary_time

                if time_since_last >= interval:
                    # Time to generate a summary
                    await self._generate_summary()
                    self.last_summary_time = datetime.now()

        except Exception as e:
            logger.error(f"Error in summary loop: {e}")
            self.stats["errors"] += 1
            self._update_status("error", f"Summary generation error: {e}")

    async def _generate_summary(self):
        """Generate a summary of recent transcript"""
        try:
            logger.info("Generating summary...")
            self._update_status("recording", "Generating summary...")

            # Get recent transcript
            transcript = self.transcription_manager.get_recent_transcript(minutes=Config.SUMMARY_INTERVAL_MINUTES)

            if not transcript or len(transcript.strip()) < 50:
                logger.info("Not enough transcript for summary yet")
                return

            # Get context from previous summaries
            context = self.summarizer.get_context_for_next_summary(num_previous=2)

            # Generate summary
            summary = await self.summarizer.generate_summary(transcript, context)

            self.stats["summaries_generated"] += 1
            logger.info(f"Summary generated (total: {self.stats['summaries_generated']})")

        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            self.stats["errors"] += 1

    def _handle_transcript(self, transcript_result: Dict[str, Any]):
        """Handle new transcript from transcription service"""
        self.stats["transcripts_received"] += 1

        if self.on_transcript:
            self.on_transcript(transcript_result)

    def _handle_summary(self, summary: Dict[str, Any]):
        """Handle new summary from summarizer"""
        if self.on_summary:
            self.on_summary(summary)

    async def stop_meeting(self):
        """Stop the meeting and cleanup"""
        if not self.is_running:
            return

        try:
            self._update_status("stopping", "Stopping meeting...")
            self.is_running = False

            # Cancel tasks
            if self._audio_task:
                self._audio_task.cancel()
                try:
                    await self._audio_task
                except asyncio.CancelledError:
                    pass

            if self._summary_task:
                self._summary_task.cancel()
                try:
                    await self._summary_task
                except asyncio.CancelledError:
                    pass

            # Generate final summary
            self._update_status("stopping", "Generating final summary...")
            await self._generate_summary()

            # Stop audio capture
            if self.audio_capturer:
                self.audio_capturer.stop_capture()

            # Stop transcription
            if self.transcription_manager:
                await self.transcription_manager.stop()

            # Leave Google Meet meeting
            if self.meet_joiner:
                await self.meet_joiner.leave_meeting()

            self._update_status("stopped", "Meeting ended")
            logger.info("Meeting stopped successfully")

            # Log stats
            logger.info(f"Meeting stats: {self.stats}")

        except Exception as e:
            logger.error(f"Error stopping meeting: {e}")
            self.stats["errors"] += 1

    async def cleanup(self):
        """Full cleanup of all resources"""
        try:
            if self.is_running:
                await self.stop_meeting()

            # Close browser
            if self.meet_joiner:
                await self.meet_joiner.close()

            self._update_status("closed", "All resources cleaned up")
            logger.info("Cleanup completed")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def get_full_transcript(self) -> str:
        """Get the complete meeting transcript"""
        if self.transcription_manager:
            return self.transcription_manager.get_full_transcript()
        return ""

    def get_all_summaries(self):
        """Get all generated summaries"""
        if self.summarizer:
            return self.summarizer.get_all_summaries()
        return []

    def export_meeting(self, format: str = "markdown") -> str:
        """
        Export complete meeting data

        Args:
            format: Export format ('markdown', 'json', or 'text')

        Returns:
            Formatted export string
        """
        if format == "json":
            import json

            return json.dumps(
                {
                    "meeting_start": self.meeting_start_time.isoformat() if self.meeting_start_time else None,
                    "transcript": self.get_full_transcript(),
                    "summaries": self.get_all_summaries(),
                    "stats": self.stats,
                },
                indent=2,
            )

        elif format == "markdown":
            output = "# Meeting Recording\n\n"

            if self.meeting_start_time:
                output += f"**Started:** {self.meeting_start_time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"

            output += "## Full Transcript\n\n"
            output += self.get_full_transcript() + "\n\n"
            output += "---\n\n"

            if self.summarizer:
                output += self.summarizer.export_summaries(format="markdown")

            output += f"\n## Stats\n\n"
            output += f"- Transcripts received: {self.stats['transcripts_received']}\n"
            output += f"- Summaries generated: {self.stats['summaries_generated']}\n"
            output += f"- Errors: {self.stats['errors']}\n"

            return output

        else:  # text
            output = "MEETING RECORDING\n"
            output += "=" * 70 + "\n\n"

            if self.meeting_start_time:
                output += f"Started: {self.meeting_start_time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"

            output += "TRANSCRIPT:\n"
            output += "-" * 70 + "\n"
            output += self.get_full_transcript() + "\n\n"

            if self.summarizer:
                output += self.summarizer.export_summaries(format="text")

            return output

    def list_audio_devices(self):
        """List available audio devices"""
        if not self.audio_capturer:
            self.audio_capturer = AudioCapturer()
        return self.audio_capturer.list_devices()
