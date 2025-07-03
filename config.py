#!/usr/bin/env python3
"""
MaxiWhisper Configuration File

Customize your key bindings here. After making changes, restart the application.
"""

from pynput import keyboard

# ─── KEY BINDINGS ────────────────────────────────────────────────────────────

# Push-to-talk mode: Hold this key/combination to record, release to stop
PUSH_TO_TALK_KEYS = keyboard.Key.f8  # Single key
# PUSH_TO_TALK_KEYS = [keyboard.Key.ctrl, keyboard.Key.space]  # Ctrl+Space combination

# Toggle mode: Press this key/combination to start/stop recording
TOGGLE_KEYS = [keyboard.Key.ctrl, keyboard.Key.f8]  # Ctrl+F8 combination  
# TOGGLE_KEYS = keyboard.Key.f9  # Single key F9

# To disable toggle mode entirely, set TOGGLE_KEYS to None:
# TOGGLE_KEYS = None

# ─── EXAMPLES ────────────────────────────────────────────────────────────────

# Single key examples:
# PUSH_TO_TALK_KEYS = keyboard.Key.f9           # F9 key
# PUSH_TO_TALK_KEYS = keyboard.Key.space        # Spacebar
# TOGGLE_KEYS = keyboard.Key.f10                # F10 key

# Key combination examples:
# PUSH_TO_TALK_KEYS = [keyboard.Key.ctrl, keyboard.Key.space]       # Ctrl+Space
# PUSH_TO_TALK_KEYS = [keyboard.Key.alt, keyboard.Key.f8]           # Alt+F8
# TOGGLE_KEYS = [keyboard.Key.shift, keyboard.Key.f9]               # Shift+F9
# TOGGLE_KEYS = [keyboard.Key.ctrl, keyboard.Key.alt, keyboard.Key.t]  # Ctrl+Alt+T

# Complex examples:
# PUSH_TO_TALK_KEYS = [keyboard.Key.ctrl, keyboard.Key.shift, keyboard.Key.space]  # Ctrl+Shift+Space
# TOGGLE_KEYS = [keyboard.Key.alt, keyboard.KeyCode.from_char('r')]  # Alt+R

# ─── OTHER SETTINGS ──────────────────────────────────────────────────────────

# Audio sample rate (Hz) - don't change unless you know what you're doing
SAMPLE_RATE = 16_000

# Output directory for transcript files (will be created if it doesn't exist)
# You can use an absolute path or relative path
OUTPUT_DIR = "maxiwhisper_records"  # relative to your home directory
# OUTPUT_DIR = "/path/to/your/custom/directory"  # absolute path example

# ─── KEY COMBINATION EXAMPLES ────────────────────────────────────────────────
"""
Common key examples:

Single Keys:
- keyboard.Key.f1 through keyboard.Key.f12    # Function keys
- keyboard.Key.space                           # Spacebar  
- keyboard.Key.tab                             # Tab key
- keyboard.Key.enter                           # Enter key
- keyboard.Key.backspace                       # Backspace
- keyboard.Key.delete                          # Delete key
- keyboard.Key.home, keyboard.Key.end          # Home/End keys
- keyboard.Key.page_up, keyboard.Key.page_down # Page Up/Down
- keyboard.Key.up, keyboard.Key.down           # Arrow keys
- keyboard.Key.left, keyboard.Key.right        # Arrow keys

Letter Keys:
- keyboard.KeyCode.from_char('a')              # Letter 'a'
- keyboard.KeyCode.from_char('z')              # Letter 'z'

Number Keys:
- keyboard.KeyCode.from_char('1')              # Number '1'
- keyboard.KeyCode.from_char('0')              # Number '0'

Modifier Keys:
- keyboard.Key.ctrl                            # Ctrl key
- keyboard.Key.alt                             # Alt key  
- keyboard.Key.shift                           # Shift key
- keyboard.Key.cmd                             # Cmd key (macOS)

Note: The application will show you the current key bindings when it starts.
""" 