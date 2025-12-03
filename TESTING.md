# Testing Guide for Zoom Meeting Assistant

This guide helps you test the Meeting Assistant before using it in production.

## 🧪 Pre-Flight Checks

### 1. Environment Setup Test

```bash
# Check Python version (need 3.9+)
python --version

# Verify virtual environment
which python  # Should show your venv path

# Check all packages installed
pip list | grep -E "(streamlit|playwright|assemblyai|anthropic)"

# Verify Playwright browsers
playwright install chromium
```

### 2. Configuration Test

```bash
# Check .env exists
ls -la .env

# Test configuration loading
python -c "from src.config import Config; Config.validate(); print('✅ Config OK')"
```

Expected output: `✅ Config OK`

If you see errors, check your API keys in `.env`

### 3. Audio Device Test

```bash
# List all audio devices
python main.py --list-devices

# Check audio routing setup
python main.py --audio-setup
```

**Expected**: You should see a list of audio input devices with numbers

**Note the device ID** for your virtual audio cable (BlackHole, VB-Cable, etc.)

## 🎬 Component Testing

### Test 1: Zoom Browser Automation

Create a test script: `test_zoom.py`

```python
import asyncio
from src.zoom_joiner import ZoomJoiner

async def test_zoom():
    joiner = ZoomJoiner()
    await joiner.initialize()
    print("✅ Browser opened successfully")

    # Navigate to Zoom test page
    await joiner.page.goto("https://zoom.us/test")
    print("✅ Can navigate to Zoom website")

    await asyncio.sleep(5)
    await joiner.close()
    print("✅ Browser closed successfully")

if __name__ == "__main__":
    asyncio.run(test_zoom())
```

Run it:
```bash
python test_zoom.py
```

**Expected**: Browser window opens, shows Zoom page, closes after 5 seconds

### Test 2: Audio Capture

Create: `test_audio.py`

```python
from src.audio_capture import AudioCapturer
import time

def test_audio():
    print("Starting audio capture test (5 seconds)...")

    capturer = AudioCapturer()
    capturer.list_devices()

    # Start capture
    capturer.start_capture()
    print("✅ Audio capture started")

    # Capture for 5 seconds
    time.sleep(5)

    # Stop
    capturer.stop_capture()
    print("✅ Audio capture stopped")

if __name__ == "__main__":
    test_audio()
```

Run it:
```bash
python test_audio.py
```

**Expected**: No errors, prints device list and capture messages

### Test 3: Transcription Service

Create: `test_transcription.py`

```python
import asyncio
from src.transcription import TranscriptionManager

transcript_count = 0

def on_transcript(result):
    global transcript_count
    transcript_count += 1
    print(f"📝 Transcript {transcript_count}: {result['text']}")

async def test_transcription():
    print("Testing transcription service...")

    manager = TranscriptionManager(on_transcript=on_transcript)
    await manager.initialize()
    print("✅ Transcription service initialized")

    # Note: This won't produce transcripts without audio
    # Just testing initialization

    await asyncio.sleep(2)
    await manager.stop()
    print("✅ Transcription service stopped")

if __name__ == "__main__":
    asyncio.run(test_transcription())
```

Run it:
```bash
python test_transcription.py
```

**Expected**: Connects to service, no errors

### Test 4: Claude Summarizer

Create: `test_summarizer.py`

```python
import asyncio
from src.summarizer import MeetingSummarizer

async def test_summarizer():
    print("Testing Claude summarizer...")

    summarizer = MeetingSummarizer()

    # Test transcript
    test_transcript = """
    John: Let's discuss the Q4 roadmap. We need to prioritize the mobile app.
    Sarah: I agree. We should allocate 3 engineers to that project.
    Mike: What about the API refactoring? That's also critical.
    John: Good point. Let's do API work in parallel. Sarah, can you lead mobile?
    Sarah: Yes, I'll take that on. I'll need the team by Monday.
    """

    print("Generating summary...")
    summary = await summarizer.generate_summary(test_transcript)

    print("\n✅ Summary generated!")
    print("\n" + "="*70)
    print(summary['summary'])
    print("="*70)

if __name__ == "__main__":
    asyncio.run(test_summarizer())
```

Run it:
```bash
python test_summarizer.py
```

**Expected**: Claude generates a structured summary with key points, decisions, and action items

## 🎙️ Integration Testing

### End-to-End Test (Without Zoom)

Create: `test_e2e.py`

```python
import asyncio
from src.meeting_manager import MeetingAssistant

transcript_count = 0
summary_count = 0

def on_transcript(result):
    global transcript_count
    transcript_count += 1
    print(f"📝 [{transcript_count}] {result.get('text', '')[:50]}...")

def on_summary(summary):
    global summary_count
    summary_count += 1
    print(f"\n📊 Summary {summary_count} generated!")
    if 'parsed' in summary:
        print(f"   Key points: {len(summary['parsed'].get('key_points', []))}")

def on_status(status):
    print(f"🔄 Status: {status['status']}")

async def test_e2e():
    print("Testing Meeting Assistant (initialization only)...")

    assistant = MeetingAssistant(
        on_transcript=on_transcript,
        on_summary=on_summary,
        on_status_change=on_status
    )

    await assistant.initialize()
    print("✅ All components initialized successfully!")

    await assistant.cleanup()
    print("✅ Cleanup successful!")

if __name__ == "__main__":
    asyncio.run(test_e2e())
```

Run it:
```bash
python test_e2e.py
```

**Expected**: All components initialize without errors

### Full Integration Test (With Zoom)

**Prerequisites:**
- Have a test Zoom meeting URL
- Audio routing configured
- All API keys set

**Option 1: Use Streamlit UI**

```bash
streamlit run app.py
```

1. Click "🚀 Initialize"
2. Enter a test meeting URL
3. Click "▶️ Start Meeting"
4. Speak into your microphone or play audio
5. Verify transcript appears
6. Wait 5 minutes for summary
7. Click "⏹️ Stop Meeting"
8. Try export buttons

**Option 2: Use CLI**

```bash
python main.py "YOUR_TEST_ZOOM_URL" -d DEVICE_ID
```

## ✅ Test Checklist

Before using in production meetings:

- [ ] Browser automation works (opens and closes)
- [ ] Can list audio devices
- [ ] Audio capture starts without errors
- [ ] Transcription service connects
- [ ] Claude API generates summaries
- [ ] Full initialization succeeds
- [ ] Can join a test Zoom meeting
- [ ] Live transcript appears
- [ ] Summaries generate after 5 minutes
- [ ] Export functions work (all 3 formats)
- [ ] Can cleanly stop and exit

## 🐛 Debugging Failed Tests

### Component-Level Debugging

**Enable debug logging:**

Add to your test scripts:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Check logs:**
```bash
tail -f logs/meeting_assistant.log
```

### Common Test Failures

**"playwright._impl._api_types.Error: Browser closed"**
→ Playwright installation issue
```bash
playwright install chromium --force
```

**"Connection refused" or API errors**
→ Check API keys are valid and have credits

**"No audio devices found"**
→ System audio permissions issue or sounddevice not installed properly

**"Timeout" errors**
→ Network issues, try increasing timeout values

## 📊 Performance Testing

### Test Metrics to Track

Create: `test_performance.py`

```python
import asyncio
import time
from src.meeting_manager import MeetingAssistant

async def performance_test():
    start_time = time.time()

    assistant = MeetingAssistant()

    # Measure initialization time
    init_start = time.time()
    await assistant.initialize()
    init_time = time.time() - init_start

    print(f"⏱️  Initialization time: {init_time:.2f}s")

    await assistant.cleanup()

    total_time = time.time() - start_time
    print(f"⏱️  Total time: {total_time:.2f}s")

    # Targets:
    # - Init < 10s: ✅ Good
    # - Init 10-20s: ⚠️  Acceptable
    # - Init > 20s: ❌ Too slow

if __name__ == "__main__":
    asyncio.run(performance_test())
```

**Target Performance:**
- Initialization: < 10 seconds
- Transcription latency: < 2 seconds
- Summary generation: < 10 seconds
- Memory usage: < 500MB

## 🎯 Test Meeting Scenarios

### Scenario 1: Quick Meeting (5 minutes)
- Join meeting
- Speak for 1 minute
- Verify transcription
- Stop before summary interval
- Check partial export

### Scenario 2: Standard Meeting (15 minutes)
- Join meeting
- Conduct conversation
- Wait for 2-3 summaries
- Verify summary quality
- Export and review

### Scenario 3: Error Recovery
- Join meeting
- Disconnect internet briefly
- Verify recovery
- Check error logging

### Scenario 4: Multiple Speakers
- Join meeting with 3+ people
- Verify all speech captured
- Check if summaries identify different topics

## 🔍 Quality Assurance

### Transcription Quality
✅ Good: 90%+ accuracy on clear audio
⚠️  Acceptable: 80-90% accuracy
❌ Poor: < 80% accuracy

**If poor:**
- Check audio quality (background noise?)
- Verify correct audio device
- Test with different transcription service

### Summary Quality
✅ Good: Captures all key points and action items
⚠️  Acceptable: Captures most points, minor omissions
❌ Poor: Misses critical information

**If poor:**
- Increase `SUMMARY_INTERVAL_MINUTES` (more context)
- Check transcript quality first
- Try different Claude model

## 📝 Creating Test Zoom Meetings

For consistent testing:

1. **Create a test Zoom account**
2. **Schedule recurring test meeting**
3. **No password** (easier for testing)
4. **Save the URL** for repeated use

Or use Zoom's test meeting:
```
https://zoom.us/test
```

## 🚀 Ready for Production?

You're ready when:
- ✅ All component tests pass
- ✅ Full integration test succeeds
- ✅ Tested with real Zoom meeting
- ✅ Transcription quality is acceptable
- ✅ Summaries are useful
- ✅ Export works correctly
- ✅ No critical errors in logs

---

**Happy testing! 🎉**

For issues, check `logs/meeting_assistant.log` and see `README.md` for troubleshooting.
