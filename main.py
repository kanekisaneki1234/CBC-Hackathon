#!/usr/bin/env python3
"""
CLI interface for Google Meet Assistant
"""
import asyncio
import argparse
import logging
import signal
import sys
from pathlib import Path
from datetime import datetime

from src.meeting_manager import MeetingAssistant
from src.config import Config
from src.audio_capture import VirtualAudioRouter, list_audio_devices

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("logs/meeting_assistant.log")],
)

logger = logging.getLogger(__name__)

# Global assistant instance for cleanup
assistant = None


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\n\n⚠️  Interrupt received, stopping meeting...")
    if assistant:
        asyncio.create_task(assistant.cleanup())
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def print_banner():
    """Print application banner"""
    print(
        """
╔═══════════════════════════════════════════════════════╗
║                                                       ║
║      🎙️  GOOGLE MEET ASSISTANT  🎙️                   ║
║                                                       ║
║     Real-time Transcription + AI Summaries           ║
║                                                       ║
╚═══════════════════════════════════════════════════════╝
"""
    )


def print_status_update(status):
    """Print status updates"""
    status_emoji = {
        "initializing": "🔧",
        "ready": "✅",
        "joining": "🚪",
        "in_meeting": "📹",
        "recording": "⏺️ ",
        "stopping": "⏹️ ",
        "stopped": "🛑",
        "error": "❌",
    }

    emoji = status_emoji.get(status["status"], "ℹ️ ")
    timestamp = status.get("timestamp", "")[:19]

    print(f"\n{emoji} [{timestamp}] {status['status'].upper()}", end="")
    if status.get("details"):
        print(f" - {status['details']}", end="")
    print()


def print_transcript(transcript_result):
    """Print transcript updates"""
    if transcript_result.get("is_final"):
        text = transcript_result["text"]
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {text}")


def print_summary(summary):
    """Print summary"""
    print("\n" + "=" * 70)
    print(f"📊 SUMMARY - {summary.get('timestamp', '')[:19]}")
    print("=" * 70)

    if "parsed" in summary and summary["parsed"]:
        parsed = summary["parsed"]

        if parsed.get("overview"):
            print(f"\n📌 Overview:\n{parsed['overview']}\n")

        if parsed.get("key_points"):
            print("🔑 Key Points:")
            for point in parsed["key_points"]:
                print(f"  • {point}")
            print()

        if parsed.get("decisions"):
            print("✅ Decisions:")
            for decision in parsed["decisions"]:
                print(f"  • {decision}")
            print()

        if parsed.get("action_items"):
            print("📋 Action Items:")
            for item in parsed["action_items"]:
                print(f"  • {item}")
            print()

        if parsed.get("questions"):
            print("❓ Questions/Concerns:")
            for question in parsed["questions"]:
                print(f"  • {question}")
            print()
    else:
        print(summary.get("summary", ""))

    print("=" * 70 + "\n")


async def run_meeting(meeting_url: str, password: str = None, audio_device_id: int = None, export_format: str = "markdown"):
    """Run the meeting assistant"""
    global assistant

    try:
        # Validate config
        Config.validate()

        # Create assistant
        assistant = MeetingAssistant(
            on_transcript=print_transcript, on_summary=print_summary, on_status_change=print_status_update
        )

        # Initialize
        print("\n🔧 Initializing components...")
        await assistant.initialize()

        # Start meeting
        print(f"\n🚀 Starting meeting: {meeting_url}")
        if password:
            print("🔒 Using provided password")

        await assistant.start_meeting(meeting_url, password, audio_device_id)

        print(
            f"""
✅ Meeting started successfully!

📝 Transcript will appear below in real-time
📊 AI summaries will be generated every {Config.SUMMARY_INTERVAL_MINUTES} minutes

Press Ctrl+C to stop the meeting and export results
"""
        )

        # Keep running until interrupted
        while assistant.is_running:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        print("\n\n⚠️  Stopping meeting...")

    except Exception as e:
        logger.error(f"Error running meeting: {e}")
        print(f"\n❌ Error: {e}")

    finally:
        # Cleanup and export
        if assistant:
            print("\n🛑 Stopping meeting and generating final summary...")
            await assistant.stop_meeting()

            # Export results
            print(f"\n💾 Exporting meeting data ({export_format} format)...")
            export_content = assistant.export_meeting(format=export_format)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_dir = Config.EXPORTS_DIR
            export_dir.mkdir(exist_ok=True)

            if export_format == "json":
                filename = export_dir / f"meeting_{timestamp}.json"
            elif export_format == "text":
                filename = export_dir / f"meeting_{timestamp}.txt"
            else:
                filename = export_dir / f"meeting_{timestamp}.md"

            filename.write_text(export_content)

            print(f"✅ Meeting data exported to: {filename}")

            # Print stats
            stats = assistant.stats
            print(
                f"""
📊 Meeting Statistics:
   • Transcripts received: {stats['transcripts_received']}
   • Summaries generated: {stats['summaries_generated']}
   • Errors: {stats['errors']}
"""
            )

            # Cleanup
            await assistant.cleanup()

        print("\n👋 Goodbye!\n")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Google Meet Assistant - Automated transcription and AI summaries")

    parser.add_argument("meeting_url", nargs="?", help="Google Meet URL")
    parser.add_argument("-p", "--password", help="Meeting password")
    parser.add_argument("-d", "--device", type=int, help="Audio device ID (use --list-devices to see options)")
    parser.add_argument("-f", "--format", choices=["markdown", "json", "text"], default="markdown", help="Export format")
    parser.add_argument("--list-devices", action="store_true", help="List available audio devices and exit")
    parser.add_argument("--audio-setup", action="store_true", help="Show audio routing setup instructions and exit")

    args = parser.parse_args()

    print_banner()

    # Handle special commands
    if args.list_devices:
        print("📋 Available Audio Devices:\n")
        list_audio_devices()
        return

    if args.audio_setup:
        print("🔊 Audio Routing Setup Instructions:\n")
        print(VirtualAudioRouter.get_setup_instructions())
        return

    # Validate meeting URL
    if not args.meeting_url:
        parser.print_help()
        print(
            "\n❌ Error: Meeting URL is required\n\nExample:\n  python main.py https://meet.google.com/abc-defg-hij\n"
        )
        sys.exit(1)

    # Check for .env file
    if not Path(".env").exists():
        print(
            """
⚠️  WARNING: No .env file found!

Please create a .env file from .env.example with your API keys:
  1. Copy .env.example to .env
  2. Add your API keys:
     - ANTHROPIC_API_KEY (required)
     - ASSEMBLYAI_API_KEY or DEEPGRAM_API_KEY (required)

Then run the application again.
"""
        )
        sys.exit(1)

    # Run the meeting
    try:
        asyncio.run(run_meeting(args.meeting_url, args.password, args.device, args.format))
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
