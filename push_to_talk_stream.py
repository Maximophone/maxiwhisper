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
mic_stream  = None
client      = None
working     = False             # recording flag
stream_thread = None            # track the streaming thread

def on_begin(_client, event: BeginEvent):
    print(f"● Session {event.id} started")

def on_turn(_client, event: TurnEvent):
    # Immutable transcript chunks arrive here
    print(event.transcript, end="\r")
    if event.end_of_turn:                # speaker pause detected
        full_turns.append(event.transcript.strip())

def on_term(_client, event: TerminationEvent):
    print(f"\n● Session ended ({event.audio_duration_seconds:.1f}s)")

def on_error(_client, err: StreamingError):
    print("Streaming error:", err, file=sys.stderr)

def run_stream():
    global mic_stream
    try:
        mic_stream = aai.extras.MicrophoneStream(sample_rate=RATE_HZ)
        client.connect(StreamingParameters(sample_rate=RATE_HZ))
        client.stream(mic_stream)
    except Exception as e:
        print(f"Stream error: {e}")
    finally:
        try:
            client.disconnect(terminate=True)
        except:
            pass

def start_streaming():
    global client, working, stream_thread, full_turns
    working = True
    full_turns.clear()  # clear previous session data
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

def stop_streaming():
    global working, mic_stream, stream_thread
    working = False
    
    # Save audio data BEFORE closing the stream
    final_text = " ".join(full_turns).strip()
    ts = datetime.datetime.now().strftime("%y%m%d-%H%M%S")
    wav_path = OUT_DIR / f"{ts}.wav"
    txt_path = OUT_DIR / f"{ts}.txt"
    
    # Save the audio first while stream is still active
    try:
        if mic_stream:
            mic_stream.save_wav(wav_path)
            print(f"● Audio saved to {wav_path.name}")
    except Exception as e:
        print(f"Warning: Could not save audio - {e}")
    
    # Now close the stream
    try:
        if mic_stream:
            mic_stream.close()
    except Exception as e:
        print(f"Warning: Error closing mic stream - {e}")
    
    # Wait for the websocket to close gracefully
    try:
        client.wait_until_closed()
    except Exception as e:
        print(f"Warning: Error waiting for client close - {e}")
    
    # Wait for the streaming thread to finish
    if stream_thread and stream_thread.is_alive():
        stream_thread.join(timeout=2.0)
    
    # Save transcript
    try:
        txt_path.write_text(final_text, encoding="utf-8")
        pyperclip.copy(final_text)
        print(f"● Transcript saved and copied to clipboard.")
    except Exception as e:
        print(f"Warning: Could not save transcript - {e}")
        # Still try to copy to clipboard
        try:
            pyperclip.copy(final_text)
            print("● Transcript copied to clipboard.")
        except:
            print("● Could not copy to clipboard.")

def on_press(key):
    if key == HOTKEY and not working:
        start_streaming()

def on_release(key):
    if key == HOTKEY and working:
        stop_streaming()
    if key == keyboard.Key.esc:          # optional quit
        return False

print("Hold F8 to speak, release to finish (ESC to quit).")
with keyboard.Listener(on_press=on_press, on_release=on_release) as L:
    L.join()
