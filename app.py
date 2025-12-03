"""
Streamlit UI for Zoom Meeting Assistant
"""
import asyncio
import streamlit as st
from datetime import datetime
from pathlib import Path
import logging
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.meeting_manager import MeetingAssistant
from src.config import Config
from src.audio_capture import VirtualAudioRouter

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", handlers=[logging.StreamHandler()]
)

# Page config
st.set_page_config(page_title="Zoom Meeting Assistant", page_icon="🎙️", layout="wide", initial_sidebar_state="expanded")

# Custom CSS
st.markdown(
    """
<style>
    .transcript-box {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        max-height: 400px;
        overflow-y: auto;
        font-family: monospace;
        margin-bottom: 20px;
    }
    .summary-card {
        background-color: #e8f4f8;
        padding: 15px;
        border-radius: 10px;
        border-left: 4px solid #1f77b4;
        margin-bottom: 15px;
    }
    .status-box {
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 20px;
        font-weight: bold;
    }
    .status-ready { background-color: #d4edda; color: #155724; }
    .status-recording { background-color: #fff3cd; color: #856404; }
    .status-error { background-color: #f8d7da; color: #721c24; }
    .status-stopped { background-color: #d1ecf1; color: #0c5460; }
</style>
""",
    unsafe_allow_html=True,
)

# Initialize session state
if "assistant" not in st.session_state:
    st.session_state.assistant = None
if "transcripts" not in st.session_state:
    st.session_state.transcripts = []
if "summaries" not in st.session_state:
    st.session_state.summaries = []
if "status" not in st.session_state:
    st.session_state.status = {"status": "not_initialized", "details": "", "timestamp": ""}
if "is_running" not in st.session_state:
    st.session_state.is_running = False
if "initialized" not in st.session_state:
    st.session_state.initialized = False


# Callbacks
def on_transcript(transcript_result):
    """Handle new transcript"""
    if transcript_result.get("is_final"):
        st.session_state.transcripts.append(
            {"text": transcript_result["text"], "timestamp": datetime.now().strftime("%H:%M:%S")}
        )


def on_summary(summary):
    """Handle new summary"""
    st.session_state.summaries.append(summary)


def on_status_change(status):
    """Handle status change"""
    st.session_state.status = status


# Helper functions
async def initialize_assistant():
    """Initialize the meeting assistant"""
    try:
        assistant = MeetingAssistant(
            on_transcript=on_transcript, on_summary=on_summary, on_status_change=on_status_change
        )
        await assistant.initialize()
        st.session_state.assistant = assistant
        st.session_state.initialized = True
        return True
    except Exception as e:
        st.error(f"Failed to initialize: {e}")
        logging.error(f"Initialization error: {e}")
        return False


async def start_meeting(meeting_url, password, audio_device_id):
    """Start the meeting"""
    try:
        await st.session_state.assistant.start_meeting(meeting_url, password, audio_device_id)
        st.session_state.is_running = True
    except Exception as e:
        st.error(f"Failed to start meeting: {e}")
        logging.error(f"Meeting start error: {e}")


async def stop_meeting():
    """Stop the meeting"""
    try:
        await st.session_state.assistant.stop_meeting()
        st.session_state.is_running = False
    except Exception as e:
        st.error(f"Failed to stop meeting: {e}")
        logging.error(f"Meeting stop error: {e}")


# Main UI
st.title("🎙️ Zoom Meeting Assistant")
st.markdown("Automatically transcribe and summarize your Zoom meetings in real-time")

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")

    # Check if .env exists
    env_exists = Path(".env").exists()
    if not env_exists:
        st.warning("⚠️ No .env file found! Please create one from .env.example")

    # Configuration status
    st.subheader("Configuration")
    try:
        Config.validate()
        st.success("✅ Configuration valid")
    except Exception as e:
        st.error(f"❌ Configuration error:\n{e}")

    st.markdown("---")

    # Audio device selection
    st.subheader("Audio Setup")

    if st.button("📋 List Audio Devices"):
        with st.spinner("Listing audio devices..."):
            if st.session_state.assistant is None:
                # Create temporary assistant to list devices
                from src.audio_capture import list_audio_devices

                devices = list_audio_devices()

            st.info("Check the console/logs for audio device list")

    audio_device_id = st.number_input(
        "Audio Device ID (optional)", min_value=-1, value=-1, help="Leave as -1 to use system default"
    )

    if audio_device_id == -1:
        audio_device_id = None

    st.markdown("---")

    # Audio routing help
    with st.expander("🔊 Audio Routing Setup"):
        st.markdown(VirtualAudioRouter.get_setup_instructions())

    st.markdown("---")

    # Stats
    if st.session_state.assistant:
        st.subheader("📊 Stats")
        stats = st.session_state.assistant.stats
        st.metric("Transcripts", stats.get("transcripts_received", 0))
        st.metric("Summaries", stats.get("summaries_generated", 0))
        st.metric("Errors", stats.get("errors", 0))


# Main content
# Status display
status = st.session_state.status
status_class = {
    "not_initialized": "status-box status-ready",
    "ready": "status-box status-ready",
    "recording": "status-box status-recording",
    "in_meeting": "status-box status-recording",
    "error": "status-box status-error",
    "stopped": "status-box status-stopped",
}.get(status["status"], "status-box")

status_text = status["status"].upper().replace("_", " ")
if status["details"]:
    status_text += f" - {status['details']}"

st.markdown(f'<div class="{status_class}">{status_text}</div>', unsafe_allow_html=True)

# Meeting controls
col1, col2 = st.columns([3, 1])

with col1:
    meeting_url = st.text_input(
        "Zoom Meeting URL", placeholder="https://zoom.us/j/123456789", help="Paste your Zoom meeting link here"
    )

    meeting_password = st.text_input(
        "Meeting Password (optional)", type="password", help="Enter if the meeting requires a password"
    )

with col2:
    st.markdown("<br>", unsafe_allow_html=True)

    if not st.session_state.initialized:
        if st.button("🚀 Initialize", use_container_width=True):
            with st.spinner("Initializing..."):
                asyncio.run(initialize_assistant())
                st.rerun()

    elif not st.session_state.is_running:
        if st.button("▶️ Start Meeting", use_container_width=True, disabled=not meeting_url):
            with st.spinner("Starting meeting..."):
                asyncio.run(start_meeting(meeting_url, meeting_password or None, audio_device_id))
                st.rerun()
    else:
        if st.button("⏹️ Stop Meeting", use_container_width=True):
            with st.spinner("Stopping meeting..."):
                asyncio.run(stop_meeting())
                st.rerun()

st.markdown("---")

# Two-column layout for transcript and summaries
col_transcript, col_summaries = st.columns([1, 1])

with col_transcript:
    st.subheader("📝 Live Transcript")

    # Transcript display
    transcript_container = st.container()

    with transcript_container:
        if st.session_state.transcripts:
            transcript_text = ""
            for t in st.session_state.transcripts[-50:]:  # Show last 50
                transcript_text += f"[{t['timestamp']}] {t['text']}\n\n"

            st.markdown(f'<div class="transcript-box">{transcript_text}</div>', unsafe_allow_html=True)
        else:
            st.info("Waiting for transcript data...")

    # Auto-refresh button
    if st.session_state.is_running:
        if st.button("🔄 Refresh Transcript"):
            st.rerun()

with col_summaries:
    st.subheader("📊 AI Summaries")

    # Summaries display
    if st.session_state.summaries:
        for i, summary in enumerate(reversed(st.session_state.summaries), 1):
            with st.expander(f"Summary {len(st.session_state.summaries) - i + 1} - {summary.get('timestamp', '')[:19]}"):
                if "parsed" in summary and summary["parsed"]:
                    parsed = summary["parsed"]

                    if parsed.get("overview"):
                        st.markdown(f"**Overview:** {parsed['overview']}")

                    if parsed.get("key_points"):
                        st.markdown("**Key Points:**")
                        for point in parsed["key_points"]:
                            st.markdown(f"- {point}")

                    if parsed.get("decisions"):
                        st.markdown("**Decisions:**")
                        for decision in parsed["decisions"]:
                            st.markdown(f"- {decision}")

                    if parsed.get("action_items"):
                        st.markdown("**Action Items:**")
                        for item in parsed["action_items"]:
                            st.markdown(f"- {item}")

                    if parsed.get("questions"):
                        st.markdown("**Questions/Concerns:**")
                        for question in parsed["questions"]:
                            st.markdown(f"- {question}")
                else:
                    st.markdown(summary.get("summary", ""))
    else:
        st.info("Summaries will appear here every 5 minutes...")

st.markdown("---")

# Export section
st.subheader("💾 Export")

col_export1, col_export2, col_export3 = st.columns(3)

with col_export1:
    if st.button("📄 Export as Markdown", use_container_width=True):
        if st.session_state.assistant:
            export_content = st.session_state.assistant.export_meeting(format="markdown")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"meeting_{timestamp}.md"

            st.download_button(
                label="⬇️ Download Markdown",
                data=export_content,
                file_name=filename,
                mime="text/markdown",
                use_container_width=True,
            )

with col_export2:
    if st.button("📋 Export as Text", use_container_width=True):
        if st.session_state.assistant:
            export_content = st.session_state.assistant.export_meeting(format="text")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"meeting_{timestamp}.txt"

            st.download_button(
                label="⬇️ Download Text",
                data=export_content,
                file_name=filename,
                mime="text/plain",
                use_container_width=True,
            )

with col_export3:
    if st.button("🗂️ Export as JSON", use_container_width=True):
        if st.session_state.assistant:
            export_content = st.session_state.assistant.export_meeting(format="json")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"meeting_{timestamp}.json"

            st.download_button(
                label="⬇️ Download JSON",
                data=export_content,
                file_name=filename,
                mime="application/json",
                use_container_width=True,
            )

# Footer
st.markdown("---")
st.markdown(
    """
<div style='text-align: center; color: #666;'>
    <p>Zoom Meeting Assistant v1.0 | Powered by AssemblyAI/Deepgram + Claude AI</p>
    <p>⚠️ Ensure proper audio routing is set up for best results</p>
</div>
""",
    unsafe_allow_html=True,
)

# Cleanup on app close
if st.session_state.assistant and not st.session_state.is_running:
    # Note: Streamlit doesn't have a reliable app close hook
    # Users should manually stop the meeting before closing
    pass
