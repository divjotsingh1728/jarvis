"""
Environment check - pure standard library, needs nothing installed.

Run it with ANY python you can find:
    python python_env.py
    py -3.12 python_env.py

It writes its report to python_check.txt  -> paste that file when you ask for help.
"""

import importlib.util
import os
import platform
import subprocess
import sys

LINES = []


def p(s=""):
    print(s)
    LINES.append(str(s))


def run(cmd, timeout=90):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           errors="ignore", timeout=timeout)
        return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()
    except Exception as e:                                  # noqa: BLE001
        return -1, "", f"{type(e).__name__}: {e}"


p("=" * 72)
p("  JARVIS PYTHON ENVIRONMENT CHECK")
p("=" * 72)
p(f"  python executable : {sys.executable}")
p(f"  version           : {sys.version.split()[0]}"
  f"   ({platform.architecture()[0]})")
p(f"  install folder    : {os.path.dirname(sys.executable)}")
p(f"  working folder    : {os.getcwd()}")
p(f"  inside a venv     : {'yes' if sys.prefix != sys.base_prefix else 'no'}"
  f"  ({sys.prefix})")
p(f"  jarvis.py here    : {os.path.exists(os.path.join(os.getcwd(), 'jarvis.py'))}")

exe = (sys.executable or "").replace("/", "\\")
if "WindowsApps" in exe:
    p("")
    p("  *** PROBLEM: this is the Microsoft Store 'python' stub, not real Python.")
    p("      Fix:  Settings > Apps > Advanced app settings > App execution")
    p("            aliases  -> turn OFF  python.exe  and  python3.exe")
    p("      then install Python from https://www.python.org/downloads/")
    p("      (tick 'Add python.exe to PATH')  and use  py -3.12  to run things.")

p("")
p("--- pip " + "-" * 63)
rc, out, err = run([sys.executable, "-m", "pip", "--version"])
if rc == 0 and out:
    p(f"  {out}")
else:
    p(f"  pip NOT WORKING (rc={rc})  {err[:200]}")
    p("  try:  python -m ensurepip --upgrade --default-pip")

p("")
p("--- packages " + "-" * 58)
NEEDED = {
    "numpy": "numpy",
    "sounddevice": "sounddevice",
    "soundfile": "soundfile",
    "speech_recognition": "SpeechRecognition",
    "flask": "Flask",
    "openai": "openai",
    "edge_tts": "edge-tts",
    "pygame": "pygame",
    "pyautogui": "pyautogui",
    "psutil": "psutil",
    "pycaw": "pycaw",
    "comtypes": "comtypes",
    "screen_brightness_control": "screen-brightness-control",
    "vosk": "vosk",
    "pyperclip": "pyperclip",
}
missing = []
for imp, pipname in NEEDED.items():
    try:
        found = importlib.util.find_spec(imp) is not None
    except Exception:                                       # noqa: BLE001
        found = False
    if found:
        try:
            m = importlib.import_module(imp)
            ver = getattr(m, "__version__", "")
        except Exception as e:                              # noqa: BLE001
            ver = f"import error: {str(e)[:50]}"
        p(f"  [ OK ] {pipname:<28} {ver}")
    else:
        p(f"  [FAIL] {pipname:<28} not installed")
        missing.append(pipname)

if missing:
    p("")
    p("  Install the missing ones with THIS python:")
    p(f"      \"{sys.executable}\" -m pip install " + " ".join(missing))
    p("  or simply:   python install.py")

p("")
p("--- microphones " + "-" * 55)
try:
    import sounddevice as sd
    devs = sd.query_devices()
    n = 0
    for i, d in enumerate(devs):
        if d.get("max_input_channels", 0) > 0:
            n += 1
            p(f"  #{i} {d.get('name', '?')}  ({int(d.get('default_samplerate') or 0)} Hz)")
    if n == 0:
        p("  [FAIL] no input device - check Windows privacy settings")
except Exception as e:                                      # noqa: BLE001
    p(f"  (skipped: {type(e).__name__}: {str(e)[:120]})")

p("")
p("--- other pythons on this PC " + "-" * 42)
for cmd in (["py", "-0"], ["where", "python"]):
    rc, out, err = run(cmd)
    if rc == 0 and out:
        p(f"  > {' '.join(cmd)}")
        for line in out.splitlines():
            p(f"      {line.strip()}")
    else:
        p(f"  > {' '.join(cmd)}  -> not found")

p("")
p("=" * 72)
if missing:
    p("  NEXT:  python install.py     (then  python doctor.py)")
else:
    p("  NEXT:  python doctor.py      (then  python jarvis.py)")
p("=" * 72)
p("")
p("  (this report was saved to python_check.txt - paste it when asking for help)")

try:
    with open(os.path.join(os.getcwd(), "python_check.txt"), "w",
              encoding="utf-8") as f:
        f.write("\n".join(LINES))
except OSError:
    pass

try:
    input("\n  Press ENTER to close...")
except EOFError:
    pass
