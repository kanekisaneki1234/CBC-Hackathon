"""
Audio capture from system audio or browser
"""
import asyncio
import logging
import queue
import threading
from typing import Optional, Callable
import sounddevice as sd
import numpy as np
from .config import Config

logger = logging.getLogger(__name__)


class AudioCapturer:
    """Captures audio from system input"""

    def __init__(
        self,
        sample_rate: int = Config.SAMPLE_RATE,
        channels: int = Config.CHANNELS,
        callback: Optional[Callable] = None,
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.callback = callback
        self.audio_queue = queue.Queue()
        self.stream = None
        self.is_recording = False
        self._recording_thread = None

    def list_devices(self):
        """List available audio devices"""
        logger.info("Available audio devices:")
        devices = sd.query_devices()
        for i, device in enumerate(devices):
            logger.info(f"  [{i}] {device['name']} (in: {device['max_input_channels']}, out: {device['max_output_channels']})")
        return devices

    def start_capture(self, device_id: Optional[int] = None):
        """
        Start capturing audio

        Args:
            device_id: Optional specific device ID to use (default uses system default)
        """
        if self.is_recording:
            logger.warning("Audio capture already running")
            return

        try:
            logger.info(f"Starting audio capture (sample_rate={self.sample_rate}, channels={self.channels})")

            if device_id is not None:
                logger.info(f"Using device ID: {device_id}")

            def audio_callback(indata, frames, time_info, status):
                """Called for each audio block"""
                if status:
                    logger.warning(f"Audio callback status: {status}")

                # Convert to bytes and add to queue
                audio_data = indata.copy()

                # Put in queue for transcription
                self.audio_queue.put(audio_data)

                # Call custom callback if provided
                if self.callback:
                    try:
                        self.callback(audio_data)
                    except Exception as e:
                        logger.error(f"Error in audio callback: {e}")

            # Open audio stream
            self.stream = sd.InputStream(
                device=device_id,
                channels=self.channels,
                samplerate=self.sample_rate,
                callback=audio_callback,
                blocksize=int(self.sample_rate * 0.1),  # 100ms blocks
            )

            self.stream.start()
            self.is_recording = True
            logger.info("Audio capture started successfully")

        except Exception as e:
            logger.error(f"Error starting audio capture: {e}")
            raise

    def stop_capture(self):
        """Stop capturing audio"""
        if not self.is_recording:
            return

        try:
            logger.info("Stopping audio capture...")

            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None

            self.is_recording = False
            logger.info("Audio capture stopped")

        except Exception as e:
            logger.error(f"Error stopping audio capture: {e}")

    def get_audio_chunk(self, timeout: float = 1.0) -> Optional[np.ndarray]:
        """
        Get next audio chunk from queue

        Args:
            timeout: Maximum time to wait for audio data

        Returns:
            Audio data as numpy array or None if timeout
        """
        try:
            return self.audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def clear_queue(self):
        """Clear the audio queue"""
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break


class VirtualAudioRouter:
    """
    Helper class for setting up virtual audio routing

    NOTE: This requires external setup:
    - Linux: PulseAudio/PipeWire loopback
    - macOS: BlackHole or Loopback
    - Windows: Virtual Audio Cable
    """

    @staticmethod
    def get_setup_instructions():
        """Get platform-specific setup instructions"""
        import platform

        os_name = platform.system()

        if os_name == "Linux":
            return """
            Linux Audio Setup (PulseAudio):

            1. Load loopback module:
               pactl load-module module-loopback latency_msec=1

            2. Set Zoom to output to the loopback
            3. Set this app to record from the loopback

            To unload: pactl unload-module module-loopback
            """

        elif os_name == "Darwin":  # macOS
            return """
            macOS Audio Setup:

            1. Install BlackHole (free):
               brew install blackhole-2ch

            2. Open Audio MIDI Setup
            3. Create Multi-Output Device with:
               - Your speakers/headphones
               - BlackHole 2ch

            4. Set Zoom to use Multi-Output Device
            5. Set this app to record from BlackHole 2ch
            """

        elif os_name == "Windows":
            return """
            Windows Audio Setup:

            1. Install VB-Cable or Virtual Audio Cable
            2. Set Zoom audio output to Virtual Cable
            3. Set this app to record from Virtual Cable
            4. Optionally use "Listen to this device" to hear audio
            """

        return "Platform-specific audio routing required"

    @staticmethod
    def print_setup_instructions():
        """Print setup instructions"""
        print(VirtualAudioRouter.get_setup_instructions())


# Convenience functions
def list_audio_devices():
    """List available audio devices"""
    capturer = AudioCapturer()
    return capturer.list_devices()
