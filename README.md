# 🎙️ Google Meet Assistant

A lightweight, AI-powered application that automatically joins Google Meet meetings, transcribes them in real-time, and generates AI summaries every 5 minutes using Claude.

## ✨ Features

- **🚪 Automatic Google Meet Joining**: Join meetings via browser automation (Playwright) - no app required
- **👤 Guest Access**: Join meetings as a guest without a Google account
- **🎤 Real-time Transcription**: Continuous speech-to-text using AssemblyAI or Deepgram
- **🤖 AI-Powered Summaries**: Generate structured summaries every 5 minutes with Claude
- **📊 Speaker Diarization**: Identify different speakers (service dependent)
- **💾 Export Functionality**: Save transcripts and summaries in Markdown, JSON, or Text
- **🖥️ Dual Interface**: Use via Streamlit web UI or command-line interface
- **📈 Live Updates**: See transcripts and summaries as they're generated

## 🏗️ Architecture

```
┌─────────────────┐
│ Google Meet Web │
└────────┬────────┘
         │ Audio
         ▼
┌─────────────────┐
│  Audio Capture  │ (System audio routing)
└────────┬────────┘
         │ PCM Audio Stream
         ▼
┌─────────────────┐
│  Transcription  │ (AssemblyAI/Deepgram)
│     Service     │
└────────┬────────┘
         │ Text Stream
         ▼
┌─────────────────┐      Every 5 min      ┌──────────────┐
│  Meeting        │─────────────────────▶ │   Claude AI  │
│  Manager        │                        │  Summarizer  │
└────────┬────────┘ ◀─────────────────────┘──────────────┘
         │           Structured Summary
         ▼
┌─────────────────┐
│  UI (Streamlit  │
│   or CLI)       │
└─────────────────┘
```

## 📋 Prerequisites

- **Python 3.9+**
- **API Keys**:
  - [Anthropic API key](https://console.anthropic.com/) (Claude)
  - [AssemblyAI API key](https://www.assemblyai.com/) OR [Deepgram API key](https://deepgram.com/)
- **Audio Routing**: Virtual audio cable or loopback (see [Audio Setup](#-audio-setup))

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/google-meet-assistant.git
cd google-meet-assistant
```

### 2. Install Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python packages
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### 3. Configure API Keys

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your API keys
nano .env  # or use your favorite editor
```

**Required in `.env`:**

```env
# Transcription (choose one)
ASSEMBLYAI_API_KEY=your_key_here
# OR
DEEPGRAM_API_KEY=your_key_here

# AI Summarization
ANTHROPIC_API_KEY=your_key_here

# Settings
TRANSCRIPTION_SERVICE=assemblyai  # or 'deepgram'
SUMMARY_INTERVAL_MINUTES=5
CLAUDE_MODEL=claude-sonnet-4-20250514
```

### 4. Set Up Audio Routing

⚠️ **CRITICAL**: You must route Google Meet's audio to the application. See [Audio Setup](#-audio-setup) below.

### 5. Run the Application

**Option A: Streamlit UI (Recommended)**

```bash
streamlit run app.py
```

Then open your browser to `http://localhost:8501`

**Option B: Command Line**

```bash
python main.py "https://meet.google.com/abc-defg-hij"
```

## 🔊 Audio Setup

The application needs to capture audio from Google Meet. This requires virtual audio routing:

### Linux (PulseAudio/PipeWire)

```bash
# Load loopback module
pactl load-module module-loopback latency_msec=1

# In Google Meet: Set output to the loopback
# In this app: Set input to the loopback monitor

# To unload later:
pactl unload-module module-loopback
```

### macOS

```bash
# Install BlackHole (free virtual audio driver)
brew install blackhole-2ch

# 1. Open "Audio MIDI Setup"
# 2. Create "Multi-Output Device":
#    - Add your speakers/headphones
#    - Add BlackHole 2ch
# 3. Set Google Meet audio output to Multi-Output Device
# 4. Set this app to record from BlackHole 2ch
```

### Windows

```
1. Install VB-Cable or Virtual Audio Cable
2. Set Google Meet audio output to Virtual Cable
3. Set this app to record from Virtual Cable
4. (Optional) Enable "Listen to this device" in Windows sound settings to hear audio
```

**List Available Devices:**

```bash
# CLI
python main.py --list-devices

# Or in Python
python -c "from src.audio_capture import list_audio_devices; list_audio_devices()"
```

## 📖 Usage

### Streamlit UI

1. **Initialize**: Click "🚀 Initialize" button
2. **Enter Meeting URL**: Paste your Google Meet link
3. **Optional**: Password field available but typically not needed for Google Meet
4. **Start**: Click "▶️ Start Meeting"
5. **Monitor**: Watch live transcripts and summaries appear
6. **Export**: Click export buttons to save results
7. **Stop**: Click "⏹️ Stop Meeting" when done

### Command Line Interface

**Basic usage:**

```bash
python main.py "https://meet.google.com/abc-defg-hij"
```

**With password (optional):**

```bash
python main.py "https://meet.google.com/abc-defg-hij" -p mypassword
```

**Specify audio device:**

```bash
python main.py "https://meet.google.com/abc-defg-hij" -d 5
```

**Change export format:**

```bash
python main.py "https://meet.google.com/abc-defg-hij" -f json
```

**Get help:**

```bash
python main.py --help
```

## 🛠️ Configuration

Edit `.env` to customize:

| Variable                  | Description                              | Default                 |
| ------------------------- | ---------------------------------------- | ----------------------- |
| `TRANSCRIPTION_SERVICE`   | Which service to use                     | `assemblyai`            |
| `SUMMARY_INTERVAL_MINUTES`| How often to generate summaries          | `5`                     |
| `CLAUDE_MODEL`            | Claude model to use                      | `claude-sonnet-4-20250514` |
| `MEET_DISPLAY_NAME`       | Your name in the Google Meet meeting     | `Meeting Assistant Bot` |
| `ASSEMBLYAI_API_KEY`      | Your AssemblyAI API key                  | -                       |
| `DEEPGRAM_API_KEY`        | Your Deepgram API key                    | -                       |
| `ANTHROPIC_API_KEY`       | Your Anthropic/Claude API key            | -                       |

## 📁 Project Structure

```
google-meet-assistant/
├── src/
│   ├── __init__.py
│   ├── config.py              # Configuration management
│   ├── meet_joiner.py         # Playwright automation for Google Meet
│   ├── audio_capture.py       # Audio capture from system
│   ├── transcription.py       # Real-time transcription services
│   ├── summarizer.py          # Claude AI summarization
│   └── meeting_manager.py     # Main orchestration logic
├── app.py                     # Streamlit web UI
├── main.py                    # Command-line interface
├── requirements.txt           # Python dependencies
├── .env.example               # Example environment variables
├── .gitignore
├── README.md
├── exports/                   # Exported meeting data
└── logs/                      # Application logs
```

## 📊 Export Formats

### Markdown (Default)

```markdown
# Meeting Recording

**Started:** 2024-01-15 14:30:00

## Full Transcript

[14:30:05] Welcome everyone to the meeting...
[14:30:12] Let's start with the project updates...

---

## Summary 1 - 2024-01-15T14:35:00

**Key Points:**
- Project timeline discussed
- Budget review completed
```

### JSON

```json
{
  "meeting_start": "2024-01-15T14:30:00",
  "transcript": "Full transcript text...",
  "summaries": [
    {
      "timestamp": "2024-01-15T14:35:00",
      "parsed": {
        "key_points": ["..."],
        "decisions": ["..."],
        "action_items": ["..."]
      }
    }
  ],
  "stats": {
    "transcripts_received": 245,
    "summaries_generated": 6
  }
}
```

## 🐛 Troubleshooting

### "Failed to join meeting"

- **Check URL**: Ensure the Google Meet URL is valid (format: https://meet.google.com/xxx-yyyy-zzz)
- **Guest Access**: The app joins as a guest - ensure the meeting allows guest participants
- **Host Approval**: Some meetings require host approval - the app will wait up to 60 seconds
- **Browser**: The Playwright browser should open automatically - if not, check your display settings

### "No audio being captured"

- **Audio Routing**: Verify virtual audio cable is set up correctly
- **Device ID**: List devices with `python main.py --list-devices` and specify the correct one
- **Permissions**: Ensure microphone permissions are granted

### "Transcription not working"

- **API Key**: Verify your transcription API key is correct in `.env`
- **Service**: Check which service is configured (`TRANSCRIPTION_SERVICE`)
- **Network**: Ensure stable internet connection for API calls
- **Audio Quality**: The service needs clear audio to transcribe

### "Summaries not generating"

- **API Key**: Verify `ANTHROPIC_API_KEY` is set correctly
- **Interval**: Default is 5 minutes - ensure enough time has passed
- **Transcript**: Summaries need sufficient transcript data (50+ characters)

### "Import errors"

```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Install Playwright browsers
playwright install chromium
```

## 🔐 Security & Privacy

- **API Keys**: Never commit `.env` files to git
- **Meeting Data**: All data is processed in real-time; no cloud storage
- **Audio**: Audio is streamed to transcription APIs - check their privacy policies
- **Exports**: Saved locally in `exports/` directory
- **Bot Presence**: Other meeting participants will see "Meeting Assistant Bot" (or your configured name)
- **Guest Access**: The app joins as a guest without requiring a Google account

## ⚡ Performance Tips

1. **Use AssemblyAI**: Generally more accurate than Deepgram for meetings
2. **Audio Quality**: Better audio = better transcription
3. **Bandwidth**: Requires stable internet for real-time transcription
4. **System Resources**: Playwright browser + audio processing requires ~500MB RAM

## 🧪 Development

**Run tests:**

```bash
# TODO: Add tests
pytest tests/
```

**Code formatting:**

```bash
black src/ app.py main.py
flake8 src/ app.py main.py
```

## 📝 Roadmap

- [ ] Add unit tests
- [ ] Support for other meeting platforms (Zoom, Teams)
- [ ] Local Whisper option (offline transcription)
- [ ] Real-time translation
- [ ] Meeting action item extraction
- [ ] Calendar integration
- [ ] Post-meeting email summaries
- [ ] Google account authentication (alternative to guest join)

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details

## 🙏 Acknowledgments

- **AssemblyAI** - Real-time transcription API
- **Deepgram** - Alternative transcription service
- **Anthropic** - Claude AI for summarization
- **Playwright** - Browser automation
- **Streamlit** - Rapid UI development

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/google-meet-assistant/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/google-meet-assistant/discussions)

## ⚠️ Disclaimer

This tool is for legitimate meeting recording and transcription purposes only. Always:
- Obtain consent from all meeting participants before recording
- Comply with local laws and regulations regarding recording
- Respect privacy and confidentiality
- Follow your organization's policies

---

**Made with ❤️ for productive meetings**
