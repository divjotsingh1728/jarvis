"""
J.A.R.V.I.S. DOCTOR
===================
Run this FIRST when something does not work:

    python doctor.py

It checks, in order:
  1. Python + packages
  2. Microphone (device, sample rate, noise floor, your speaking level)
  3. Speech-to-text  (Groq Whisper + Google fallback) - you speak, it prints
  4. Text-to-speech  (edge-tts neural voice + Windows SAPI fallback)
  5. The AI brain    (Groq: valid key? which models exist? how fast?)
  6. Windows actions (volume, brightness, screenshot, app index, contacts)

It writes a copy of the report to doctor_report.txt
"""

import os
import platform
import subprocess
import sys
import time
import traceback

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT = os.path.join(BASE_DIR, "doctor_report.txt")

REQUIRED = {
    "numpy": "numpy", "sounddevice": "sounddevice", "soundfile": "soundfile",
    "speech_recognition": "SpeechRecognition", "flask": "Flask", "openai": "openai",
}
OPTIONAL = {
    "pygame": "pygame (plays the good neural voice)",
    "edge_tts": "edge-tts (Hindi/English neural voice)",
    "pyautogui": "pyautogui (keyboard, mouse, screenshot)",
    "psutil": "psutil (close apps, battery, CPU)",
    "pycaw": "pycaw (exact volume control)",
    "screen_brightness_control": "screen-brightness-control",
    "vosk": "vosk (offline wake word, optional)",
}

LINES = []


def say(*a):
    line = " ".join(str(x) for x in a)
    print(line, flush=True)
    LINES.append(line)


def _is_admin():
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:                                       # noqa: BLE001
        return "unknown"


def head(t):
    say("\n" + "=" * 68)
    say("  " + t)
    say("=" * 68)


def ask(prompt="Press ENTER to continue (or q + ENTER to quit): "):
    try:
        v = input(prompt).strip().lower()
    except EOFError:
        return True
    if v in ("q", "quit", "exit"):
        say("\nBye.")
        with open(REPORT, "w", encoding="utf-8") as f:
            f.write("\n".join(LINES))
        sys.exit(0)
    return True


# =========================================================================
head("1. SYSTEM")
say(f"  Python     : {sys.version.split()[0]}  ({platform.architecture()[0]})")
say(f"  Platform   : {platform.system()} {platform.release()}")
say(f"  Folder     : {BASE_DIR}")
say(f"  Admin      : {_is_admin() if platform.system() == 'Windows' else 'n/a'}")

# =========================================================================
head("2. PACKAGES")
missing_required = []
for mod, pipname in list(REQUIRED.items()) + list(OPTIONAL.items()):
    try:
        m = __import__(mod)
        ver = getattr(m, "__version__", "")
        kind = "required" if mod in REQUIRED else "optional"
        say(f"  [ OK ]  {mod:<28} {ver:<12} ({kind})")
    except Exception as e:                                  # noqa: BLE001
        kind = "REQUIRED" if mod in REQUIRED else "optional"
        say(f"  [FAIL]  {mod:<28} {kind:<12} -> {e}")
        if mod in REQUIRED:
            missing_required.append(pipname)

if missing_required:
    say("\n  !! Install the missing required packages:")
    say(f"     pip install {' '.join(missing_required)}")
    say("     (or:  pip install -r requirements.txt )")
    ask()
    sys.exit(1)

# jarvis imports its own config/client, so import it after the checks
sys.path.insert(0, BASE_DIR)
try:
    import jarvis as J                                      # noqa: E402
except Exception:                                           # noqa: BLE001
    say("\n  !! jarvis.py failed to import:")
    say(traceback.format_exc(limit=6))
    ask()
    sys.exit(1)

# =========================================================================
head("3. MICROPHONE")
try:
    import sounddevice as sd
    import numpy as np
except Exception:                                           # noqa: BLE001
    say("  sounddevice/numpy missing - cannot test audio")
    ask(); sys.exit(1)

devs = J.list_input_devices()
if not devs:
    say("  [FAIL] No input device found. Check Windows sound settings /")
    say("         Settings > Privacy > Microphone (allow desktop apps).")
else:
    for d in devs:
        star = "  <- default" if d["default"] else ""
        say(f"  #{d['index']:<3} {d['name'][:52]:<54} {int(d['rate'] or 0)} Hz{star}")

say("")
say("  Config: mic_device=%r  mic_name_contains=%r  mic_gain=%r"
    % (J.CONFIG.get("mic_device"), J.CONFIG.get("mic_name_contains"),
       J.CONFIG.get("mic_gain")))

mic = J.start_mic()
if mic is None:
    say("  [FAIL] Could not open ANY microphone.")
    say("         Fixes: close other apps using the mic (Zoom/Teams),")
    say("         Settings > Privacy > Microphone > 'Let desktop apps access'.")
    ask(); sys.exit(1)
say(f"  [ OK ] Opened device #{mic.device} @ {mic.rate} Hz (resampled to 16000)")

vad = J.Vad()
say("\n  Calibrating: please stay SILENT for 2 seconds...")
vad.calibrate(mic, 2.0)
say(f"  Noise floor        : {vad.noise:.1f}")
say(f"  Speech threshold   : {vad.threshold():.0f}")

say("\n  Now SPEAK normally for 4 seconds (say: 'jarvis youtube kholo') ...")
time.sleep(0.4)
peak, frames, t0 = 0.0, [], time.time()
while time.time() - t0 < 4.0:
    b = mic.get(0.2)
    if b is not None:
        lv = vad.rms(b)
        peak = max(peak, lv)
        frames.append(b)
        bar = "#" * min(46, int(lv / 6))
        print(f"\r    level {lv:7.1f} |{bar}", end="", flush=True)
print()
say(f"  Your speaking level: {peak:.1f}   (threshold {vad.threshold():.0f})")

if peak < vad.threshold() * 1.3:
    say("  [WARN] Your voice is BARELY above the threshold.")
    say("         Fix: in config.json set  \"mic_gain\": 2.5  (try 2 - 4)")
    say("         and/or move closer to the mic / raise input volume to 100.")
elif peak > 6000:
    say("  [WARN] Input is very hot - lower the mic volume or set mic_gain to 0.6")
else:
    say("  [ OK ] Level is healthy.")

# =========================================================================
head("4. SPEECH TO TEXT")
if J.CLIENT is None:
    say("  [WARN] No Groq key -> Whisper unavailable, Google fallback only.")
    say("         Put your key in groq_key.txt (one line, no quotes).")
else:
    say("  [ OK ] Groq key found, Whisper models: " + ", ".join(J.CONFIG["stt_models"]))

if frames:
    import numpy as np
    audio = np.concatenate(frames)
    say(f"\n  Sending {len(audio) / 16000:.1f}s of what you just said...")
    t0 = time.time()
    text = J.transcribe(audio)
    dt = time.time() - t0
    if text:
        say(f"  [ OK ] Heard ({dt:.1f}s):  \"{text}\"")
    else:
        say("  [FAIL] Nothing recognised.")
        say("         - Did the level bar above move when you spoke?")
        say("         - If not, fix the microphone first (section 3).")
        say("         - If yes, check your internet / Groq key.")
else:
    say("  (no audio captured - skipped)")

# =========================================================================
head("5. TEXT TO SPEECH")
say("  voice_hi = %s" % J.CONFIG["voice_hi"])
say("  voice_en = %s" % J.CONFIG["voice_en"])
if J.NEURAL_TTS:
    say("  [ OK ] edge-tts + pygame present -> neural voice enabled")
    spk = J.Speaker()
    say("\n  You should now hear TWO sentences (Hindi + English).")
    spk.say("नमस्ते सर, मैं जार्विस हूँ।")
    spk.say("Hello sir, this is the English test.")
    spk.wait()
    ok = input("  Did you hear both? (y/n): ").strip().lower()
    if ok.startswith("y"):
        say("  [ OK ] Neural voice works.")
    else:
        say("  [WARN] Check the Windows output device / volume mixer.")
        say("         Trying the built-in Windows voice now...")
        J.sapi_speak("यह विंडोज़ की आवाज़ है। This is the Windows voice.")
else:
    say("  [WARN] edge-tts or pygame missing - only the old Windows voice works.")
    say("         Fix:  pip install edge-tts pygame")
    say("  Playing the Windows SAPI voice now...")
    J.sapi_speak("नमस्ते सर, यह विंडोज़ की आवाज़ है। Hello sir, Windows voice test.")

# =========================================================================
head("6. AI BRAIN (Groq)")
if J.CLIENT is None:
    say("  [FAIL] No client. Add groq_key.txt, then re-run.")
else:
    try:
        t0 = time.time()
        models = J.CLIENT.models.list()
        ids = sorted(m.id for m in models.data)
        dt = time.time() - t0
        say(f"  [ OK ] {len(ids)} models available ({dt:.1f}s)")
        chat = [i for i in ids if not i.startswith(("whisper", "canopylabs", "meta-llama/llama-prompt"))]
        say("  Chat models you can use:")
        for i in chat[:14]:
            mark = "<= in use" if i in J.CONFIG["llm_models"] else ""
            say(f"        {i:<45} {mark}")
        whisp = [i for i in ids if i.startswith("whisper")]
        say(f"  Whisper models: {', '.join(whisp) or 'NONE'}")
        for m in J.CONFIG["llm_models"]:
            if m not in ids:
                say(f"  [FAIL] configured model '{m}' does NOT exist anymore ->")
                say("         edit config.json and pick one from the list above.")
        for m in J.CONFIG["stt_models"]:
            if m not in ids:
                say(f"  [WARN] whisper model '{m}' not available.")
    except Exception as e:                                  # noqa: BLE001
        say(f"  [FAIL] Could not list models: {e}")
        say("         Check the API key and your internet connection.")

    say("\n  Sending a live chat request...")
    try:
        t0 = time.time()
        r = J.CLIENT.chat.completions.create(
            model=J.CONFIG["llm_models"][0],
            messages=[{"role": "user", "content": "Reply with exactly: JARVIS ONLINE"}],
            max_tokens=20, timeout=25)
        say(f"  [ OK ] {time.time() - t0:.1f}s -> "
            f"{r.choices[0].message.content.strip()!r}")
    except Exception as e:                                  # noqa: BLE001
        say(f"  [FAIL] Chat failed: {type(e).__name__}: {str(e)[:200]}")

# =========================================================================
head("7. WINDOWS ACTIONS")
def probe(name, fn):
    try:
        out = str(fn())
        say(f"  [ OK ] {name:<22} -> {out[:70]}")
    except Exception as e:                                  # noqa: BLE001
        say(f"  [FAIL] {name:<22} -> {type(e).__name__}: {str(e)[:70]}")

probe("volume",       lambda: f"{J.t_get_volume()}")
probe("brightness",   lambda: J.t_set_brightness(max(20, 50)))
probe("screenshot",   J.t_screenshot)
probe("system_info",  J.t_system_info)
probe("weather",      lambda: J.t_get_weather("auto"))

say("")
try:
    J.load_app_index()
    J.APP_READY.wait(15)
    say(f"  [ OK ] app index          -> {len(J.APP_INDEX)} apps")
except Exception as e:                                      # noqa: BLE001
    say(f"  [FAIL] app index          -> {e}")
try:
    c = J._load_contacts()
    say(f"  [ OK ] contacts           -> {', '.join(c) or 'none saved'}")
except Exception as e:                                      # noqa: BLE001
    say(f"  [FAIL] contacts           -> {e}")

# =========================================================================
head("SUMMARY / NEXT STEPS")
say("""  If everything above is [ OK ], start JARVIS with:

        python jarvis.py

  Then open  http://127.0.0.1:5000  and use the TYPE BOX first.

  Quick decision table
  --------------------
  Typed command works, spoken does not   -> microphone / STT  (sections 3-4)
  JARVIS understands but stays silent    -> TTS              (section 5)
  JARVIS says "brain error"              -> API key / model  (section 6)
  JARVIS does the wrong action           -> see README_FIXES.md, section 4

  Useful config.json knobs
  ------------------------
  "mic_gain": 2.5          it cannot hear you
  "always_listen": true    wake word is not triggering
  "reply_lang": "en"       force English replies ("hi" forces Hindi)
  "stt_lang": "en"         if Hinglish is being mis-transcribed
  "cues": true             beep when it starts listening
""")

with open(REPORT, "w", encoding="utf-8") as f:
    f.write("\n".join(LINES))
say(f"  Report saved to {REPORT}")
ask("\n  Press ENTER to close: ")
