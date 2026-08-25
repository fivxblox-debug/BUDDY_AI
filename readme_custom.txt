Based on the provided README, here is a structured breakdown of the assistant’s capabilities, limitations, and executable installation/setup commands.

---

### 1. Capabilities

* **Voice & Audio Interaction:**
  * Real-time, ultra-low latency conversational voice (powered by Gemini Live API).
  * **Affective Dialog:** Adapts response tone based on the user’s vocal emotion (fatigue, excitement, etc.).
  * **Proactive Audio (Selective Listening):** Differentiates between speech directed at the assistant versus ambient/background conversations or TV noise without needing a wake word.
  * **Unlimited Sessions:** Sliding-window context compression allows hours of continuous conversation without context-overflow disconnects.
  * Multi-language support with automatic spoken language detection.

* **Extensibility & Plugins:**
  * Drop-in modular plugin system via the `plugins/` directory.
  * Auto-discovery, safety isolation (broken plugins will not crash the assistant), and per-plugin ON/OFF toggle via UI.

* **System & Hardware Control:**
  * App launcher, desktop/window management, mouse/keyboard shortcuts.
  * Control volume, screen brightness, Wi-Fi, and power settings.
  * Telemetry monitoring for CPU, RAM, GPU, and temperature with voice alerts.
  * Auto-start on boot across supported operating systems (Task Scheduler / LaunchAgent / .desktop).

* **Vision & Context Awareness:**
  * Screen capture and webcam vision fed into the live session.
  * Proactive contextual check-ins (time-of-day awareness, morning briefings, yesterday's recap).

* **Web & Search Features:**
  * Multi-mode search: `news`, `research`, `price`, `compare`, and general search (Gemini Grounded first, DuckDuckGo fallback).
  * Flight price/availability search, live local weather updates, and daily background headline monitoring for custom topics.

* **Productivity, Media & Tasks:**
  * File processing: reading, summarizing, and answering questions about local documents.
  * Coding assistant: inline code review, debugging, and generation.
  * Autonomous agent mode for multi-step task planning.
  * Clipboard intelligence tool (floating panel for Translate / Summarise / Explain / Fix).
  * Browser navigation, YouTube playback control, and messaging (WhatsApp, Telegram).
  * Game update triggers (Steam, Epic Games) and OS-native reminders.
  * Mobile control via QR code pairing.

---

### 2. Limitations

* **API & Hardware Dependency:**
  * Requires a working Gemini API key (`config/api_keys.json`).
  * Requires a functioning physical microphone.
  * Dependent on Gemini Live preview APIs (though it contains fallback reconnection logic if preview features fail).
* **Licensing & Usage:**
  * Restricted to personal, non-commercial use under **Creative Commons BY-NC 4.0**.
* **Dependencies:**
  * `requirements.txt` does not bundle every OS-specific dependency; users may need manual installations for certain platform-specific modules.
* **Runtime Environment:**
  * Limited to Python 3.11 or 3.12 on Windows 10/11, macOS, or Linux.

---

### 3. Executable Commands

#### **Setup & Execution**
```bash
# 1. Clone the repository
git clone https://github.com/FatihMakes/Mark-LI.git

# 2. Navigate into the project folder
cd Mark-LI

# 3. Install core dependencies
pip install -r requirements.txt

# 4. Run the main assistant application
python main.py
```

#### **Conditional / Troubleshooting Commands**
```bash
# Install any missing OS-specific dependencies if ModuleNotFoundError occurs
pip install <module_name>
```