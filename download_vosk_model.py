"""
Optional: download a small offline wake-word model for JARVIS.

JARVIS works WITHOUT this (it uses Groq/Google speech-to-text to spot the
wake word). A local Vosk model just means zero network traffic while it
waits for you to say "Jarvis".

    python download_vosk_model.py

It downloads ~45 MB into a folder next to jarvis.py. When it is done,
restart JARVIS - the boot log will say "Vosk offline wake word ready".

If the download fails, do it by hand:
    https://alphacephei.com/vosk/models
  -> vosk-model-small-en-in-0.4.zip      (best for the English word "Jarvis")
  -> vosk-model-small-hi-0.22.zip        (Hindi wake word "जार्विस")
  -> unzip into this folder, then set "vosk_model_dir" in config.json
"""

import os
import sys
import zipfile
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CANDIDATES = [
    ("https://alphacephei.com/vosk/models/vosk-model-small-en-in-0.4.zip",
     "vosk-model-small-en-in-0.4",  "Indian-English, best for the word 'Jarvis'"),
    ("https://alphacephei.com/vosk/models/vosk-model-small-hi-0.22.zip",
     "vosk-model-small-hi-0.22",    "Hindi, for 'जार्विस'"),
]


def already_have():
    for d in sorted(os.listdir(BASE_DIR)):
        if d.lower().startswith("vosk-model") and os.path.isdir(os.path.join(BASE_DIR, d)):
            return d
    return None


def main():
    have = already_have()
    if have:
        print(f"You already have a model folder: {have}")
        print("Delete it first if you want a different one.")
        return

    print("Pick a model:")
    for i, (url, name, desc) in enumerate(CANDIDATES, 1):
        print(f"  {i}) {name:<28} {desc}")
    choice = input("Enter 1 or 2 (default 1): ").strip() or "1"
    try:
        url, name, _ = CANDIDATES[int(choice) - 1]
    except Exception:                                       # noqa: BLE001
        url, name, _ = CANDIDATES[0]

    zip_path = os.path.join(BASE_DIR, name + ".zip")
    print(f"\nDownloading {url}")
    print("(this is ~45 MB and can take a minute...)\n")
    try:
        urllib.request.urlretrieve(url, zip_path)
    except Exception as e:                                  # noqa: BLE001
        print(f"Download failed: {e}")
        print("Open the link in your browser instead and unzip it here.")
        sys.exit(1)

    print("Extracting...")
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(BASE_DIR)
    os.remove(zip_path)
    print(f"\nDone. Model folder: {name}")                              
    print("Restart JARVIS  ->  python jarvis.py")


if __name__ == "__main__":
    main()
