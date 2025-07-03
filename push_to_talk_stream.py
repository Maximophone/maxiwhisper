#!/usr/bin/env python3
"""
Hold F8 to stream audio to AssemblyAI, release to save WAV+TXT and copy text.
"""
import os, sys, datetime, pathlib, threading, time
import pyperclip
from pynput import keyboard
import assemblyai as aai
from dotenv import load_dotenv
import tkinter as tk
from queue import Queue
from assemblyai.streaming.v3 import (
    StreamingClient, StreamingClientOptions,
    StreamingParameters, StreamingEvents, TurnEvent,
    BeginEvent, TerminationEvent, StreamingError
)

# Load configuration and environment variables
try:
    import config
    print("● Configuration loaded from config.py")
except ImportError:
    print("● Warning: config.py not found, using default settings")
    # Create a default config object
    class DefaultConfig:
        PUSH_TO_TALK_KEYS = keyboard.Key.f8
        TOGGLE_KEYS = [keyboard.Key.ctrl, keyboard.Key.f8]
        SAMPLE_RATE = 16_000
        OUTPUT_DIR = "maxiwhisper_records"
    config = DefaultConfig()

load_dotenv()

# ─── CONFIGURATION ───────────────────────────────────────────────────────────
# Normalize key configurations to lists for uniform handling
def normalize_keys(keys):
    """Convert single key or list of keys to a standardized list format"""
    if keys is None:
        return None
    elif isinstance(keys, list):
        return keys
    else:
        return [keys]

# Keys from config.py
PUSH_TO_TALK_KEYS = normalize_keys(getattr(config, 'PUSH_TO_TALK_KEYS', keyboard.Key.f8))
TOGGLE_KEYS = normalize_keys(getattr(config, 'TOGGLE_KEYS', [keyboard.Key.ctrl, keyboard.Key.f8]))

# Other settings
RATE_HZ = getattr(config, 'SAMPLE_RATE', 16_000)
OUTPUT_DIR_NAME = getattr(config, 'OUTPUT_DIR', 'maxiwhisper_records')

# Setup output directory
if os.path.isabs(OUTPUT_DIR_NAME):
    OUT_DIR = pathlib.Path(OUTPUT_DIR_NAME)
else:
    OUT_DIR = pathlib.Path.home() / OUTPUT_DIR_NAME
OUT_DIR.mkdir(exist_ok=True)

API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
# ─────────────────────────────────────────────────────────────────────────────

if not API_KEY:
    sys.exit("Set ASSEMBLYAI_API_KEY in your environment.")

aai.settings.api_key = API_KEY  # fallback for extras helpers
full_turns  = []                # finalised turns for this session
current_transcript = ""         # latest transcript (including partial)
mic_stream  = None
client      = None
working     = False             # recording flag
toggle_mode = False             # whether we're in toggle recording mode
pressed_keys = set()            # track currently pressed keys
stream_thread = None            # track the streaming thread
ui_window = None                # tkinter window for displaying transcript
ui_update_queue = Queue()       # thread-safe queue for UI updates
ui_thread = None                # UI thread reference
recording_ready = False         # Track if recording is actually ready

def on_begin(_client, event: BeginEvent):
    global recording_ready
    print(f"● Session {event.id} started")
    recording_ready = True
    # Update UI to show it's ready with a special marker
    update_ui_text("READY|||🎤 Ready! Start speaking...")

def on_turn(_client, event: TurnEvent):
    global current_transcript
    # Immutable transcript chunks arrive here
    print(event.transcript, end="\r")
    
    # Always update the current transcript (partial or final)
    current_transcript = event.transcript.strip()
    
    # Update UI with complete transcript
    complete_text = get_complete_transcript()
    update_ui_text(complete_text)
    
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
    global client, working, stream_thread, full_turns, current_transcript, recording_ready
    working = True
    recording_ready = False  # Reset ready state
    full_turns.clear()  # clear previous session data
    current_transcript = ""  # clear current transcript
    
    # Show UI window
    show_ui()
    
    client = StreamingClient(
        StreamingClientOptions(api_key=API_KEY, api_host="streaming.assemblyai.com")
    )
    client.on(StreamingEvents.Begin, on_begin)
    client.on(StreamingEvents.Turn, on_turn)
    client.on(StreamingEvents.Termination, on_term)
    client.on(StreamingEvents.Error, on_error)
    stream_thread = threading.Thread(target=run_stream, daemon=True)
    stream_thread.start()
    if not toggle_mode:
        print("● Listening… (release F8 to stop)")

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
    global working, mic_stream, stream_thread, toggle_mode
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
    
    # Hide UI window
    hide_ui()
    
    # Now get the complete text - the clipboard should have the most up-to-date version
    # since incremental_save() is called from the streaming events
    try:
        final_text = pyperclip.paste().strip()
        print(f"● Using clipboard text with length: {len(final_text)}")
    except Exception as e:
        print(f"Warning: Could not get clipboard text - {e}")
        # Fallback to our function
        final_text = get_complete_transcript()
        print(f"● Using fallback text with length: {len(final_text)}")
    
    # Create final timestamped file
    ts = datetime.datetime.now().strftime("%y%m%d-%H%M%S")
    txt_path = OUT_DIR / f"{ts}.txt"
    
    # Save transcript
    save_transcript(final_text, txt_path)
    
    # Reset toggle mode if this was a toggle session
    if toggle_mode:
        toggle_mode = False

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

def create_ui_window():
    """Create and configure the minimalistic transcription window"""
    global ui_window
    
    root = tk.Tk()
    root.title("Transcribing...")
    
    # Get UI settings from config
    bg_color = getattr(config, 'UI_BACKGROUND', '#1e1e1e')
    text_bg = getattr(config, 'UI_TEXT_BACKGROUND', '#2d2d2d')
    text_color = getattr(config, 'UI_TEXT_COLOR', '#ffffff')
    font_family = getattr(config, 'UI_FONT_FAMILY', 'Arial')
    font_size = getattr(config, 'UI_FONT_SIZE', 11)
    window_width = getattr(config, 'UI_WIDTH', 400)
    window_height = getattr(config, 'UI_HEIGHT', 150)
    position = getattr(config, 'UI_POSITION', 'bottom-right')
    
    # Window styling
    root.configure(bg=bg_color)
    root.attributes('-topmost', True)  # Always on top
    
    # Make window frameless for minimal look (optional)
    # root.overrideredirect(True)  
    
    # Get screen dimensions
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    
    # Calculate window position based on config
    margin = 20
    if position == 'bottom-right':
        x = screen_width - window_width - margin
        y = screen_height - window_height - 60
    elif position == 'bottom-left':
        x = margin
        y = screen_height - window_height - 60
    elif position == 'top-right':
        x = screen_width - window_width - margin
        y = margin
    elif position == 'top-left':
        x = margin
        y = margin
    else:  # center
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
    
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    # Create text widget
    text_widget = tk.Text(root, 
                         wrap=tk.WORD,
                         bg=text_bg,
                         fg=getattr(config, 'UI_CONNECTING_COLOR', '#ffaa00'),  # Start with connecting color
                         font=(font_family, font_size),
                         padx=15,
                         pady=15,
                         relief=tk.FLAT,
                         borderwidth=0)
    text_widget.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
    
    # Add initial text
    text_widget.insert('1.0', 'Connecting...')
    text_widget.config(state=tk.DISABLED)  # Make read-only
    
    ui_window = root
    return root, text_widget

def run_ui():
    """Run the UI in a separate thread"""
    global ui_window
    
    try:
        root, text_widget = create_ui_window()
        
        # Get color settings from config
        default_color = getattr(config, 'UI_TEXT_COLOR', '#ffffff')
        connecting_color = getattr(config, 'UI_CONNECTING_COLOR', '#ffaa00')
        ready_color = getattr(config, 'UI_READY_COLOR', '#00ff00')
        
        def update_text():
            """Check for text updates from the queue"""
            try:
                while not ui_update_queue.empty():
                    new_text = ui_update_queue.get_nowait()
                    text_widget.config(state=tk.NORMAL)
                    text_widget.delete('1.0', tk.END)
                    
                    # Check for special ready marker
                    if new_text and new_text.startswith("READY|||"):
                        # Remove the marker and set ready color
                        new_text = new_text.replace("READY|||", "")
                        text_widget.config(fg=ready_color)
                    elif new_text:
                        # Normal transcript text - use default color
                        text_widget.config(fg=default_color)
                    else:
                        # Connecting state - use connecting color
                        new_text = 'Connecting...'
                        text_widget.config(fg=connecting_color)
                    
                    text_widget.insert('1.0', new_text)
                    text_widget.config(state=tk.DISABLED)
                    text_widget.see(tk.END)  # Auto-scroll
            except:
                pass
            
            # Schedule next update check
            if ui_window:
                root.after(50, update_text)  # Check every 50ms
        
        # Start update checking
        update_text()
        
        # Run the UI event loop
        root.mainloop()
    except Exception as e:
        print(f"UI Error: {e}")
    finally:
        ui_window = None

def show_ui():
    """Start the UI in a separate thread"""
    global ui_thread
    
    # Check if UI is enabled
    if not getattr(config, 'SHOW_UI', True):
        return
    
    ui_thread = threading.Thread(target=run_ui, daemon=True)
    ui_thread.start()
    time.sleep(0.2)  # Give UI time to initialize

def hide_ui():
    """Close the UI window"""
    global ui_window
    if ui_window:
        try:
            ui_window.quit()
            ui_window = None
        except:
            pass

def update_ui_text(text):
    """Thread-safe UI text update"""
    # Check if UI is enabled
    if not getattr(config, 'SHOW_UI', True):
        return
    
    ui_update_queue.put(text)

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

def is_key_combination_pressed(key_combination):
    """Check if all keys in a combination are currently pressed"""
    if key_combination is None:
        return False
    return all(key in pressed_keys for key in key_combination)

def on_press(key):
    global toggle_mode, pressed_keys
    try:
        # Add key to pressed keys set
        pressed_keys.add(key)
        
        # Check for push-to-talk combination
        if PUSH_TO_TALK_KEYS and is_key_combination_pressed(PUSH_TO_TALK_KEYS):
            if not working and not toggle_mode:
                start_streaming()
            elif toggle_mode:
                toggle_name = get_keys_display_name(TOGGLE_KEYS)
                print(f"● Already recording in toggle mode. Use {toggle_name} to stop.")
        
        # Check for toggle combination
        elif TOGGLE_KEYS and is_key_combination_pressed(TOGGLE_KEYS):
            if not working:
                toggle_mode = True
                start_streaming()
                toggle_name = get_keys_display_name(TOGGLE_KEYS)
                print(f"● Toggle mode: Recording started ({toggle_name} to stop)")
            else:
                # Stop toggle recording
                toggle_mode = False
                stop_streaming()
                print("● Toggle mode: Recording stopped")
                
    except Exception as e:
        print(f"Error in key press handler: {e}")
        emergency_save()

def on_release(key):
    global pressed_keys
    try:
        # Remove key from pressed keys set
        pressed_keys.discard(key)
        
        # Check if push-to-talk combination is no longer active
        if PUSH_TO_TALK_KEYS and not is_key_combination_pressed(PUSH_TO_TALK_KEYS):
            if working and not toggle_mode:
                stop_streaming()
        
        # Check for ESC key
        if key == keyboard.Key.esc:
            # Emergency save before quitting
            if working:
                emergency_save()
            return False
            
    except Exception as e:
        print(f"Error in key release handler: {e}")
        emergency_save()

def get_key_name(key):
    """Get a human-readable name for a single key"""
    if hasattr(key, 'name'):
        name = key.name.replace('_', ' ').title()
        # Clean up common key names
        name = name.replace('Key ', '').replace('L ', '').replace('R ', '')
        return name
    elif hasattr(key, 'char') and key.char:
        return key.char.upper()
    else:
        return str(key)

def get_keys_display_name(key_combination):
    """Get a human-readable name for a key combination"""
    if key_combination is None:
        return "None"
    elif len(key_combination) == 1:
        return get_key_name(key_combination[0])
    else:
        key_names = [get_key_name(key) for key in key_combination]
        return "+".join(key_names)

# Display current key bindings
def display_key_bindings():
    push_name = get_keys_display_name(PUSH_TO_TALK_KEYS) if PUSH_TO_TALK_KEYS else "None"
    
    if TOGGLE_KEYS:
        toggle_name = get_keys_display_name(TOGGLE_KEYS)
        toggle_text = f"{toggle_name}: Toggle recording"
    else:
        toggle_text = "Toggle mode: Disabled"
    
    print(f"● Key bindings: {push_name}: Hold to speak | {toggle_text} | ESC: Quit")

display_key_bindings()
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
