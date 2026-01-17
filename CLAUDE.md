# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Coding Guidelines

This is a **Python/PyQt5 desktop application**, not a web frontend project. Follow Python best practices:

- Use early returns whenever possible for readability
- Follow PEP 8 style guide (with 120-char line length per project standard)
- Write descriptive variable/function names (snake_case for functions, PascalCase for classes)
- Fully implement all requested functionality - no TODOs, placeholders, or missing pieces
- Include all required imports and ensure proper naming
- Focus on readable, maintainable code over premature optimization
- Use type hints for public APIs (Optional, List, Dict from typing)
- Write Google-style docstrings with Args/Returns/Raises sections
- Do not attempt to run or start the service after modification; leave this to the user

## Project Overview

AutoVoiceType is a Windows-based intelligent voice input tool written in Python. It enables "push-to-talk" voice recognition by holding the Right Ctrl key, integrating with Alibaba Cloud's DashScope API for real-time speech recognition and automatically typing the recognized text into the active window.

**Key Technologies:**
- PyQt5 for GUI and system tray integration
- Real-time speech recognition via WebSocket (DashScope, Doubao)
- pynput for global keyboard hooks
- PyAudio for microphone audio capture
- Multi-strategy text input simulation (clipboard, Win32 API, pyautogui)

## Development Commands

### Running the Application

**Development mode:**
```bash
cd src
python main.py
```

**Environment check:**
```bash
python check_environment.py
```

### Building and Packaging

**Build executable (PyInstaller):**
```bash
build.bat
# or manually:
pyinstaller AutoVoiceType.spec
```

**Build installer (Inno Setup):**
```bash
build_installer.bat
```

**Testing:**
```bash
pytest
pytest --cov=src --cov-report=html  # with coverage
```

**Code quality:**
```bash
pylint src/              # linting
autopep8 --in-place --aggressive src/  # formatting
mypy src/                # type checking
```

## Architecture

### Layered Design

The application follows a 4-layer architecture:

```
UI Layer (TrayApp, RecordingWidget, SettingsWindow)
    ↓
Business Logic Layer (HotkeyManager, VoiceRecognizer, TextSimulator)
    ↓
Data Access Layer (DashScope API, AudioCapture, ConfigStorage)
    ↓
System Interface Layer (Windows API, Global Hook, Clipboard)
```

### Critical Data Flow

1. **User presses Right Ctrl** → HotkeyManager detects via pynput keyboard hook
2. **on_hotkey_press()** → Shows RecordingWidget animation + starts VoiceRecognizer
3. **VoiceRecognizer** → Opens WebSocket to DashScope API + starts PyAudio stream
4. **Audio streaming** → Continuously sends audio chunks through WebSocket
5. **User releases Right Ctrl** → HotkeyManager triggers on_hotkey_release()
6. **VoiceRecognizer stops** → Closes WebSocket, waits for final result
7. **Recognition result** → Callback fires with transcribed text
8. **TextSimulator** → Inputs text using 3-tier fallback strategy (clipboard → Win32 → pyautogui)

### Core Modules

**ConfigManager** (src/config_manager.py)
- Singleton pattern for centralized configuration
- Loads/saves JSON config from `~/.autovoicetype/config.json`
- Supports dot-notation paths: `get('api.dashscope_api_key')`
- Merges default config with user config to handle new fields

**HotkeyManager** (src/hotkey_manager.py)
- Global keyboard listener using pynput
- Detects Right Ctrl key (VK code 0xA3) press/release
- Prevents duplicate triggers with `_is_key_pressed` flag
- Callback-based design for loose coupling

**VoiceRecognizer** (src/voice_recognizer.py)
- Legacy wrapper maintained for backward compatibility
- Delegates to recognizer implementations via factory pattern
- Uses PyAudio to capture microphone audio (16kHz, mono, PCM)
- Streams audio in 3200-byte chunks
- Handles recognition events through callback pattern

**Recognizer Architecture** (src/recognizers/)
- Factory pattern for pluggable speech recognition providers
- BaseRecognizer: Abstract base class defining common interface
- DashScopeRecognizer: Alibaba Cloud DashScope API integration
  - Models: qwen3-asr-flash-realtime, fun-asr-realtime
  - Uses dashscope SDK for WebSocket communication
- DoubaoRecognizer: ByteDance Doubao ASR integration
  - Async-to-sync bridge for aiohttp WebSocket
  - Requires app_id and access_token
  - Custom protocol implementation (doubao_protocol.py)
- RecognizerFactory: Creates appropriate recognizer based on config

**TextSimulator** (src/text_simulator.py)
- 3-tier fallback strategy for maximum app compatibility:
  1. Clipboard method: Copy text → Ctrl+V → Restore clipboard
  2. Win32 method: SendInput API with VK_PACKET for Unicode
  3. pyautogui method: Character-by-character typing (slowest, most reliable)
- Protects original clipboard content when configured
- Enforces max input length limit

**UI Components** (src/ui/)
- TrayApp: System tray icon with context menu (Settings, Quit)
- RecordingWidget: Animated floating widget shown during recording
- SettingsWindow: macOS-style settings interface with 5 configuration pages
- AutoStartManager: Windows registry integration for startup behavior

## Configuration

**Location:** `~/.autovoicetype/config.json`

**Critical Fields:**

*API Configuration (Provider-dependent):*
- `api.provider`: Recognition provider ("dashscope" | "doubao")
- For DashScope:
  - `api.dashscope_api_key`: Alibaba Cloud API key (required)
  - `api.model`: Recognition model (default: "qwen3-asr-flash-realtime")
- For Doubao:
  - `api.doubao_app_id`: ByteDance app ID (required)
  - `api.doubao_access_token`: ByteDance access token (required)

*Other Settings:*
- `audio.sample_rate`: Must be 16000 for DashScope compatibility
- `input.preferred_method`: "clipboard" | "win32" | "pyautogui"
- `recognition.semantic_punctuation_enabled`: Auto-punctuation toggle

**First Run:**
The application detects missing API key as first run and shows configuration wizard. User must configure API key before the app becomes functional.

## Important Implementation Details

### PyInstaller Packaging

**Spec file:** `AutoVoiceType.spec`

Critical considerations:
- Use directory mode (`exclude_binaries=True`) for faster startup
- UPX compression is DISABLED to avoid DLL loading errors
- Icon must be ICO format at `assets/logo.ico` for Windows taskbar
- Console is hidden (`console=False`) for GUI-only execution
- All hiddenimports must include PyQt5, numpy, dashscope, pynput submodules
- In packaged mode, logs go to `<exe_dir>/log/` instead of `~/.autovoicetype/logs/`

### Configuration Hot-Reload

When user saves settings, the app:
1. Reloads config via ConfigManager.load_config()
2. Updates logging level if changed
3. Recreates VoiceRecognizer with new model/API settings (only if not currently recording)
4. Shows notification to confirm changes applied

### Error Handling Philosophy

- All exceptions in core modules are logged with `exc_info=True` for full stack traces
- User-facing errors show notification via TrayApp.show_message()
- Recording failures trigger immediate widget hide + error notification
- Network errors during recognition are caught by VoiceRecognitionCallback.on_error()

### Logging Strategy

- Default level: INFO (configurable via `general.log_level`)
- Log rotation: Daily files named `autovoicetype_YYYYMMDD.log`
- Development: Logs to `~/.autovoicetype/logs/` + stdout
- Production (frozen): Logs to `<exe_dir>/log/` with fallback to user directory
- Sensitive data (API keys) are never logged in full

## Code Style Guidelines

**Naming Conventions:**
- Modules: `snake_case` (config_manager.py)
- Classes: `PascalCase` (ConfigManager, VoiceRecognizer)
- Functions/methods: `snake_case` (start_recording, on_hotkey_press)
- Constants: `UPPER_SNAKE_CASE` (DEFAULT_CONFIG, MAX_BUFFER_SIZE)
- Private methods: `_leading_underscore` (_merge_default_config)

**Line Length:** 120 characters (project standard, not PEP 8's 79)

**Import Order:**
1. Standard library (logging, sys, pathlib)
2. Third-party (PyQt5, dashscope, numpy)
3. Local modules (config_manager, hotkey_manager)

**Docstrings:** Google style with Args/Returns/Raises sections

**Type Hints:** Prefer explicit typing for public APIs; use Optional, List, Dict from typing

## Common Gotchas

1. **PyAudio installation on Windows:** Direct pip install often fails. Download precompiled wheel from https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio

2. **Icon not showing in taskbar:** Windows prioritizes the ICO embedded in the EXE. Must build with `icon='assets/logo.ico'` in spec file. QApplication.setWindowIcon() is secondary.

3. **DLL loading errors:** If PyInstaller build fails with "python dll" errors, ensure UPX is disabled (`upx=False`) and Visual C++ Redistributable is installed.

4. **First run detection:** Relies on API key validation. If user manually edits config.json with empty/invalid key, wizard appears again.

5. **Model switching:** Changing recognition model in settings only applies after current recording session completes. UI shows warning if recording is active.

6. **Clipboard protection:** The `input.restore_clipboard` setting must be enabled to avoid overwriting user's clipboard. Disabled only for testing.

## Development Workflow

**Adding a new configuration field:**
1. Add to `DEFAULT_CONFIG` in ConfigManager
2. Create getter method (e.g., `get_xxx_config()`)
3. Add UI controls in appropriate SettingsPage
4. Update docs/SETTINGS_GUIDE.md

**Adding a new speech recognition provider:**
1. Create new recognizer class in `src/recognizers/` inheriting from BaseRecognizer
2. Implement required methods: `start_recognition()`, `stop_recognition()`, `is_recording()`
3. Add provider configuration to `DEFAULT_CONFIG` in ConfigManager
4. Register provider in RecognizerFactory.create_recognizer()
5. Add UI selection in Settings → Recognition page
6. Test with target applications

**Modifying recognition behavior:**
1. Update BaseRecognizer interface if needed (affects all providers)
2. Update specific recognizer implementation
3. Ensure callback signature remains compatible
4. Add new fields to `api_config` dict
5. Test with all supported models/providers

**Supporting new input methods:**
1. Add to InputMethod enum in text_simulator.py
2. Implement `_input_via_<method>()` private method
3. Add to fallback chain in `input_text()`
4. Test across target applications (VS Code, browsers, Office apps)

## Dependencies

**Runtime:**
- PyQt5 >= 5.15.0 (GUI framework)
- pynput >= 1.7.6 (keyboard hooks)
- PyAudio >= 0.2.11 (audio capture)
- dashscope >= 1.10.0 (Alibaba Cloud API)
- websocket-client >= 1.3.0 (WebSocket communication)
- pyperclip >= 1.8.2 (clipboard operations)
- pyautogui >= 0.9.53 (input simulation)
- pywin32 >= 305 (Windows API, auto-start)
- numpy >= 1.21.0 (audio processing)

**Development:**
- pytest, pytest-cov (testing)
- pylint (linting)
- autopep8 (formatting)
- mypy (type checking)

**Build:**
- PyInstaller >= 5.0 (packaging)
- Inno Setup 6 (installer creation, Windows only)

## Testing Strategy

Unit tests are in `tests/` directory but minimal coverage currently. Integration testing relies on manual verification checklist:
- Right Ctrl press/release detection
- Recording animation display
- Recognition result accuracy
- Text input across apps (Notepad, Chrome, Word, VS Code, WeChat)
- Settings persistence
- Auto-start registry modification

Performance targets:
- Startup < 3 seconds
- Memory < 150MB
- CPU (idle) < 2%
- CPU (recording) < 25%
- Recognition latency < 500ms
