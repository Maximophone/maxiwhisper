# MaxiWhisper

*A push‑to‑talk, low‑latency desktop voice‑to‑text helper powered by AssemblyAI’s v3 Universal‑Streaming API.*  
Hold **F8** to speak, release to finish; a `.wav` + `.txt` pair is saved and the transcript is already in your clipboard.  
Latency is typically well under one second because audio is streamed over WebSockets instead of uploaded as a whole file. :contentReference[oaicite:0]{index=0}

---

## ✨ Features
- **Live streaming transcription** via AssemblyAI’s Python SDK—no polling logic required. :contentReference[oaicite:1]{index=1}  
- **Hot‑key recording** implemented with `pynput`; defaults to **F8** but is configurable. :contentReference[oaicite:2]{index=2}  
- **Automatic clipboard copy** with `pyperclip` for instant paste anywhere. :contentReference[oaicite:3]{index=3}  
- **Lightweight stack**: single script, <40 MB of wheels, runs on macOS, Linux, Windows.

---

## 📦 Requirements

| Type | Package / Library | Notes |
|------|-------------------|-------|
| **Python** | `assemblyai[extras] == 0.41.5` | Includes `extras.MicrophoneStream` helper. :contentReference[oaicite:4]{index=4} |
|           | `pynput >= 1.7.6` | Global key listener. :contentReference[oaicite:5]{index=5} |
|           | `pyperclip >= 1.8.2` | Cross‑platform clipboard. :contentReference[oaicite:6]{index=6} |
| **System** | **PortAudio** | Needed by `pyaudio/sounddevice`; install with `brew install portaudio` on macOS or `apt install portaudio19-dev` on Debian/Ubuntu. :contentReference[oaicite:7]{index=7} |

---

## 🚀 Quick‑start

```bash
git clone https://github.com/your‑name/maxiwhisper.git
cd maxiwhisper
python -m venv venv && source venv/bin/activate   # .\venv\Scripts\activate on Windows
pip install -r requirements.txt

# Create .env file with your API key
echo "ASSEMBLYAI_API_KEY=your_actual_api_key_here" > .env

python push_to_talk_stream.py
````

> **Tip:** You obtain an API key from the AssemblyAI dashboard (free tier includes 500 minutes/month). ([assemblyai.com][1])

---

## 🔧 Configuration

| Variable  | Default                  | Description                                                                          |
| --------- | ------------------------ | ------------------------------------------------------------------------------------ |
| `HOTKEY`  | `pynput.keyboard.Key.f8` | Change to any `pynput.keyboard.Key` or key combination. ([pynput.readthedocs.io][2]) |
| `RATE_HZ` | `16000`                  | Sample rate sent to the API.                                                         |
| `OUT_DIR` | `~/maxiwhisper_records`  | Where audio + text files are stored.                                                 |

Edit these near the top of **`push_to_talk_stream.py`**.

---

## 🗂 File layout

```
maxiwhisper/
├─ push_to_talk_stream.py   # main script
├─ requirements.txt
└─ README.md
```

Each session produces:

```
maxiwhisper_records/
├─ 250703-153012.wav
└─ 250703-153012.txt
```

*(timestamps are YYMMDD‑HHMMSS)*

---

## 🛣 Roadmap

* Keep the WebSocket open across multiple turns to emulate Wispr Flow’s “session” concept and further cut RTT. ([assemblyai.com][1])
* Allow punctuation / summarisation by passing a `TranscriptionConfig` to the streaming client. ([assemblyai.com][1], [assemblyai.com][3])
* Optional **GUI tray icon** for mute status and recording length.

---

## 🤝 Contributing

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a pull request

---

## 📝 License

Distributed under the MIT License. See **`LICENSE`** for more information. ([makeareadme.com][4])

---

## 🙌 Acknowledgements

* [AssemblyAI Docs](https://www.assemblyai.com/docs/) for the streaming quick‑start. ([assemblyai.com][1], [assemblyai.com][5])
* [`pynput`](https://pynput.readthedocs.io/) for painless cross‑platform hot‑keys. ([pynput.readthedocs.io][2])
* [`pyperclip`](https://pypi.org/project/pyperclip/) for clipboard convenience. ([pypi.org][6])
* [Make‑a‑README](https://www.makeareadme.com/) & [Best‑README‑Template](https://github.com/othneildrew/Best-README-Template) for layout inspiration. ([makeareadme.com][4], [github.com][7])


[1]: https://www.assemblyai.com/docs/speech-to-text/universal-streaming?utm_source=chatgpt.com "Streaming Audio | AssemblyAI | Documentation"
[2]: https://pynput.readthedocs.io/en/latest/keyboard.html?utm_source=chatgpt.com "Handling the keyboard — pynput 1.7.6 documentation"
[3]: https://www.assemblyai.com/docs/guides?utm_source=chatgpt.com "Cookbooks | AssemblyAI | Documentation"
[4]: https://www.makeareadme.com/?utm_source=chatgpt.com "Make a README"
[5]: https://www.assemblyai.com/docs/getting-started/transcribe-streaming-audio?utm_source=chatgpt.com "Transcribe streaming audio | AssemblyAI | Documentation"
[6]: https://pypi.org/project/pyperclip/?utm_source=chatgpt.com "pyperclip - PyPI"
[7]: https://github.com/othneildrew/Best-README-Template?utm_source=chatgpt.com "An awesome README template to jumpstart your projects! - GitHub"
