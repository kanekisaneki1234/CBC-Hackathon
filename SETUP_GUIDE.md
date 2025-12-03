# Quick Setup Guide for Zoom Meeting Assistant

## 🎯 What You Need

### 1. API Keys (Get these first!)

**Required:**
- **Anthropic API Key** - Get from https://console.anthropic.com/
  - Sign up for an account
  - Go to "API Keys" section
  - Create a new key
  - Copy it - you'll need this for `.env`

**One of these (choose based on preference):**
- **AssemblyAI API Key** (Recommended) - Get from https://www.assemblyai.com/
  - Sign up for free account
  - Get $50 free credit
  - Copy API key from dashboard

- **Deepgram API Key** (Alternative) - Get from https://deepgram.com/
  - Sign up for account
  - Get free credit
  - Copy API key from console

### 2. System Requirements

- **Python 3.9 or higher** - Check with `python --version`
- **300MB disk space** - For dependencies and browsers
- **Stable internet connection** - For API calls
- **Audio routing capability** - Virtual audio cable (see below)

## 🚀 Installation Steps

### Step 1: Install Python Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv

# Activate it
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install packages
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### Step 2: Configure API Keys

```bash
# Copy example file
cp .env.example .env

# Edit with your favorite editor
nano .env   # or vim, code, notepad, etc.
```

**Add your keys to `.env`:**

```env
# Choose ONE transcription service:
ASSEMBLYAI_API_KEY=paste_your_assemblyai_key_here

# OR (if using Deepgram):
# DEEPGRAM_API_KEY=paste_your_deepgram_key_here

# Required for AI summaries:
ANTHROPIC_API_KEY=paste_your_anthropic_key_here

# Settings (optional to change):
TRANSCRIPTION_SERVICE=assemblyai
SUMMARY_INTERVAL_MINUTES=5
CLAUDE_MODEL=claude-sonnet-4-20250514
ZOOM_DISPLAY_NAME=Meeting Assistant Bot
```

### Step 3: Set Up Audio Routing

**This is CRITICAL - the app needs to hear the Zoom audio!**

#### On Linux:
```bash
# Load loopback module
pactl load-module module-loopback latency_msec=1

# Then:
# 1. In Zoom settings: Set Speaker to "Loopback"
# 2. Run: python main.py --list-devices
# 3. Find the loopback device number
# 4. Use that device when starting the app
```

#### On macOS:
```bash
# Install BlackHole
brew install blackhole-2ch

# Then:
# 1. Open "Audio MIDI Setup" app
# 2. Click + and create "Multi-Output Device"
# 3. Check BOTH: Your speakers + BlackHole 2ch
# 4. Set Zoom output to "Multi-Output Device"
# 5. The app will record from "BlackHole 2ch"
```

#### On Windows:
```
1. Download and install VB-Cable from:
   https://vb-audio.com/Cable/

2. Set Zoom audio output to "CABLE Input"

3. In Windows Sound settings:
   - Right-click "CABLE Output"
   - Properties → Listen tab
   - Check "Listen to this device" (to hear audio)

4. The app will record from "CABLE Output"
```

## ▶️ Running the Application

### Option 1: Streamlit Web UI (Easier)

```bash
streamlit run app.py
```

Open browser to http://localhost:8501

### Option 2: Command Line

```bash
# Basic usage
python main.py "https://zoom.us/j/123456789"

# With password
python main.py "https://zoom.us/j/123456789" -p mypassword

# Specify audio device
python main.py "https://zoom.us/j/123456789" -d 5
```

## ✅ Quick Test Checklist

Before your first real meeting, test that:

- [ ] Python dependencies installed (`pip list | grep streamlit`)
- [ ] Playwright browsers installed (`playwright install chromium`)
- [ ] `.env` file exists with valid API keys
- [ ] Audio routing configured (can hear system audio in test)
- [ ] Can list audio devices (`python main.py --list-devices`)
- [ ] Streamlit starts without errors (`streamlit run app.py`)

## 🐛 Common Issues

### "Configuration errors: ANTHROPIC_API_KEY is required"
→ Your `.env` file is missing or has wrong key names. Check spelling!

### "Failed to join meeting"
→ Check the Zoom URL is correct. Wait for the browser window to open.

### "No audio being captured"
→ Audio routing not set up correctly. Follow audio setup guide carefully.

### "ModuleNotFoundError: No module named 'streamlit'"
→ Virtual environment not activated or requirements not installed.
```bash
source venv/bin/activate  # Activate venv
pip install -r requirements.txt  # Install again
```

### "Transcription not working"
→ Check your transcription API key in `.env`. Verify it's valid at the provider's website.

## 📊 What Happens During a Meeting

1. **Browser Opens**: Playwright opens a Chrome window
2. **Joins Meeting**: Automatically clicks through Zoom web join flow
3. **Starts Recording**: Begins capturing audio from configured device
4. **Live Transcription**: Text appears in real-time as people speak
5. **5-Minute Summaries**: Claude generates structured summary every 5 minutes
6. **Export Options**: Save transcript + summaries when meeting ends

## 💡 Pro Tips

1. **Test First**: Join a test Zoom meeting before your important one
2. **Check Audio**: Make sure you can see audio waveforms/activity
3. **Stable Connection**: Poor internet = poor transcription
4. **Inform Participants**: Tell meeting participants the bot is recording
5. **Manual Backup**: Keep Zoom's built-in recording as backup

## 🆘 Getting Help

1. **Check Logs**: Look in `logs/meeting_assistant.log`
2. **Read README**: Full documentation in `README.md`
3. **Test Components**:
   ```bash
   python main.py --list-devices    # Test audio
   python main.py --audio-setup     # Show audio instructions
   ```

## 📞 Support Resources

- **AssemblyAI Docs**: https://www.assemblyai.com/docs
- **Deepgram Docs**: https://developers.deepgram.com/
- **Anthropic Docs**: https://docs.anthropic.com/
- **Playwright Docs**: https://playwright.dev/python/

---

**Ready to go?** Try running: `streamlit run app.py` and test with a Zoom meeting!
