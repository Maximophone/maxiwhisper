#!/usr/bin/env python3
"""
Hold F8 to stream audio to AssemblyAI, release to save WAV+TXT and copy text.
"""
import os, sys, datetime, pathlib, threading, time
import pyperclip
from pynput import keyboard
import assemblyai as aai
from dotenv import load_dotenv
from assemblyai.streaming.v3 import (
    StreamingClient, StreamingClientOptions,
    StreamingParameters, StreamingEvents, TurnEvent,
    BeginEvent, TerminationEvent, StreamingError
)

# Load environment variables from .env file
load_dotenv()

# ─── CONFIG ──────────────────────────────────────────────────────────────────
HOTKEY          = keyboard.Key.f8
RATE_HZ         = 16_000
OUT_DIR         = pathlib.Path.home() / "maxiwhisper_records"
OUT_DIR.mkdir(exist_ok=True)
API_KEY         = os.getenv("ASSEMBLYAI_API_KEY")
# ─────────────────────────────────────────────────────────────────────────────

if not API_KEY:
    sys.exit("Set ASSEMBLYAI_API_KEY in your environment.")

aai.settings.api_key = API_KEY  # fallback for extras helpers
full_turns  = []                # finalised turns for this session
current_transcript = ""         # latest transcript (including partial)
mic_stream  = None
client      = None
working     = False             # recording flag
stream_thread = None            # track the streaming thread

def on_begin(_client, event: BeginEvent):
    print(f"● Session {event.id} started")

def on_turn(_client, event: TurnEvent):
    global current_transcript
    # Immutable transcript chunks arrive here
    print(event.transcript, end="\r")
    
    # Always update the current transcript (partial or final)
    current_transcript = event.transcript.strip()
    
    if event.end_of_turn:                # speaker pause detected
        full_turns.append(event.transcript.strip())
    
    # Auto-save after any transcript update for safety
    incremental_save()

def on_term(_client, event: TerminationEvent):
    print(f"\n● Session ended ({event.audio_duration_seconds:.1f}s)")

def on_error(_client, err: StreamingError):
    print("Streaming error:", err, file=sys.stderr)
    # Emergency save current transcript before potential crash
    emergency_save()

def run_stream():
    global mic_stream
    try:
        mic_stream = aai.extras.MicrophoneStream(sample_rate=RATE_HZ)
        client.connect(StreamingParameters(sample_rate=RATE_HZ))
        client.stream(mic_stream)
    except Exception as e:
        print(f"Stream error: {e}")
        # Emergency save on stream error
        emergency_save()
    finally:
        try:
            client.disconnect(terminate=True)
        except:
            pass

def start_streaming():
    global client, working, stream_thread, full_turns, current_transcript
    working = True
    full_turns.clear()  # clear previous session data
    current_transcript = ""  # clear current transcript
    client = StreamingClient(
        StreamingClientOptions(api_key=API_KEY, api_host="streaming.assemblyai.com")
    )
    client.on(StreamingEvents.Begin, on_begin)
    client.on(StreamingEvents.Turn, on_turn)
    client.on(StreamingEvents.Termination, on_term)
    client.on(StreamingEvents.Error, on_error)
    stream_thread = threading.Thread(target=run_stream, daemon=True)
    stream_thread.start()
    print("● Listening… (hold F8)")

def get_complete_transcript():
    """Get the complete transcript using the same logic as incremental_save"""
    complete_text_parts = []
    if full_turns:
        complete_text_parts.extend(full_turns)
    if current_transcript and (not full_turns or current_transcript != full_turns[-1]):
        # Add current transcript if it's different from the last completed turn
        complete_text_parts.append(current_transcript)
    
    return " ".join(complete_text_parts).strip()

def stop_streaming():
    global working, mic_stream, stream_thread
    working = False
    
    # First, close the stream to stop new data
    try:
        if mic_stream:
            mic_stream.close()
    except Exception as e:
        print(f"Warning: Error closing mic stream - {e}")
    
    # Wait longer for all transcript events to finish processing
    time.sleep(0.5)
    
    # Wait for the streaming thread to finish
    if stream_thread and stream_thread.is_alive():
        stream_thread.join(timeout=3.0)
    
    # Now get the complete text - the clipboard should have the most up-to-date version
    # since incremental_save() is called from the streaming events
    try:
        final_text = pyperclip.paste().strip()
        print(f"DEBUG: Using clipboard text with length: {len(final_text)}")
    except Exception as e:
        print(f"Warning: Could not get clipboard text - {e}")
        # Fallback to our function
        final_text = get_complete_transcript()
        print(f"DEBUG: Using fallback text with length: {len(final_text)}")
    
    # Create final timestamped file
    ts = datetime.datetime.now().strftime("%y%m%d-%H%M%S")
    txt_path = OUT_DIR / f"{ts}.txt"
    
    # Save transcript
    save_transcript(final_text, txt_path)

def save_transcript(text, file_path):
    """Robustly save transcript to file and clipboard"""
    if not text.strip():
        print("● No transcript to save.")
        return
    
    # Try to save to file
    try:
        file_path.write_text(text, encoding="utf-8")
        print(f"● Transcript saved to {file_path.name} ({len(text)} chars)")
    except Exception as e:
        print(f"Warning: Could not save transcript to file - {e}")
    
    # Try to copy to clipboard
    try:
        pyperclip.copy(text)
        print("● Transcript copied to clipboard.")
    except Exception as e:
        print(f"Warning: Could not copy to clipboard - {e}")

def emergency_save():
    """Save current transcript in case of emergency/error"""
    try:
        complete_text = get_complete_transcript()
        
        if complete_text:
            ts = datetime.datetime.now().strftime("%y%m%d-%H%M%S")
            emergency_path = OUT_DIR / f"EMERGENCY_{ts}.txt"
            save_transcript(complete_text, emergency_path)
            print(f"● Emergency save completed to {emergency_path.name}")
    except Exception as e:
        print(f"Emergency save failed: {e}")

def incremental_save():
    """Save current transcript incrementally during long sessions"""
    try:
        complete_text = get_complete_transcript()
        
        if complete_text:
            # Save to a temporary incremental file that gets updated
            incremental_path = OUT_DIR / "current_session.txt"
            incremental_path.write_text(complete_text, encoding="utf-8")
            # Also update clipboard after each turn
            pyperclip.copy(complete_text)
    except Exception as e:
        # Don't print warnings for incremental saves to avoid spam
        pass

def on_press(key):
    try:
        if key == HOTKEY and not working:
            start_streaming()
    except Exception as e:
        print(f"Error in key press handler: {e}")
        emergency_save()

def on_release(key):
    try:
        if key == HOTKEY and working:
            stop_streaming()
        if key == keyboard.Key.esc:          # optional quit
            # Emergency save before quitting
            if working:
                emergency_save()
            return False
    except Exception as e:
        print(f"Error in key release handler: {e}")
        emergency_save()

print("Hold F8 to speak, release to finish (ESC to quit).")
try:
    with keyboard.Listener(on_press=on_press, on_release=on_release) as L:
        L.join()
except KeyboardInterrupt:
    print("\n● Interrupted by user")
    emergency_save()
except Exception as e:
    print(f"Unexpected error: {e}")
    emergency_save()
finally:
    print("● Session ended")
