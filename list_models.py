"""
Find out which AI models YOUR Groq key can actually use - and fix config.json.

    python list_models.py            # show + test every model your key can see
    python list_models.py --write    # ...and write the working ones to config.json
    python list_models.py --offline  # skip Groq, show the Ollama (local) route

Use this when doctor.py says:
    [FAIL] configured model 'xxx' does NOT exist anymore
or when JARVIS answers "brain error".
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
KEY_PATH = os.path.join(BASE_DIR, "groq_key.txt")
API = "https://api.groq.com/openai/v1"

# models worth trying, best first (Groq production line-up, Oct 2026)
PREFERRED = [
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "qwen/qwen3.8-27b",
    "qwen/qwen3.6-27b",
    "moonshotai/kimi-k2-instruct",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]
SKIP_PREFIX = ("whisper", "canopylabs", "meta-llama/llama-prompt",
               "openai/gpt-oss-safeguard")

TOOL = [{
    "type": "function",
    "function": {"name": "ping", "description": "reply ping",
                 "parameters": {"type": "object", "properties": {}}}
}]


def load_key():
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if not key and os.path.exists(KEY_PATH):
        with open(KEY_PATH, encoding="utf-8") as f:
            key = f.read().strip()
    return key


def http(url, key=None, payload=None, timeout=30):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    req.add_header("Content-Type", "application/json")
    if key:
        req.add_header("Authorization", f"Bearer {key}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="ignore")
        try:
            return e.code, json.loads(body)
        except Exception:                                   # noqa: BLE001
            return e.code, {"error": {"message": body[:300]}}
    except Exception as e:                                  # noqa: BLE001
        return 0, {"error": {"message": f"{type(e).__name__}: {e}"}}


def test_model(key, model):
    """(works, tool_calling, seconds, note)"""
    t0 = time.time()
    code, body = http(f"{API}/chat/completions", key, {
        "model": model,
        "messages": [{"role": "user", "content": "Reply with exactly: OK"}],
        "max_tokens": 10, "temperature": 0,
    })
    dt = time.time() - t0
    if code != 200:
        msg = (body.get("error") or {}).get("message", str(body))[:110]
        return False, False, dt, msg
    text = (body.get("choices", [{}])[0].get("message", {}).get("content") or "").strip()

    # does it support tool calling? (JARVIS needs this to actually do things)
    code2, body2 = http(f"{API}/chat/completions", key, {
        "model": model,
        "messages": [{"role": "user", "content": "call the ping tool"}],
        "tools": TOOL, "tool_choice": "auto", "max_tokens": 60,
    })
    tools_ok = False
    if code2 == 200:
        msg2 = body2.get("choices", [{}])[0].get("message", {})
        tools_ok = bool(msg2.get("tool_calls"))
    return True, tools_ok, dt, text[:40]


def main():
    args = [a.lower() for a in sys.argv[1:]]
    write = "--write" in args

    print("=" * 72)
    print("  GROQ MODEL FINDER")
    print("=" * 72)

    if "--offline" in args:
        show_ollama_help()
        return

    key = load_key()
    if not key:
        print("  No API key found.")
        print(f"  Put your key (one line) in:  {KEY_PATH}")
        print("  Get a free one: https://console.groq.com/keys\n")
        show_ollama_help()
        return

    print(f"  key: {key[:8]}...{key[-4:]}   ({'groq_key.txt' if not os.environ.get('GROQ_API_KEY') else 'env'})\n")

    code, body = http(f"{API}/models", key)
    if code != 200:
        msg = (body.get("error") or {}).get("message", str(body))
        print(f"  [FAIL] could not list models (HTTP {code}): {msg}\n")
        if code in (401, 403):
            print("  -> The key is wrong/expired. Make a new one at")
            print("     https://console.groq.com/keys  and overwrite groq_key.txt")
        else:
            print("  -> No internet, or a firewall/proxy is blocking api.groq.com")
        print()
        show_ollama_help()
        return

    ids = sorted(m.get("id", "") for m in body.get("data", []) if m.get("id"))
    chat = [i for i in ids if not i.startswith(SKIP_PREFIX)]
    whisper = [i for i in ids if i.startswith("whisper")]

    print(f"  Your key can see {len(ids)} model(s):\n")
    for i in ids:
        tag = " (speech-to-text)" if i.startswith("whisper") else ""
        print(f"     {i}{tag}")

    # order candidates: preferred order first, then anything else we discovered
    candidates = [m for m in PREFERRED if m in chat]
    candidates += [m for m in chat if m not in candidates]

    print("\n" + "-" * 72)
    print("  LIVE TEST  (can this model chat, and can it call JARVIS tools?)")
    print("-" * 72)
    good, basic_only = [], []
    for m in candidates:
        ok, tools_ok, dt, note = test_model(key, m)
        if ok and tools_ok:
            mark = "OK  + tools"
            good.append(m)
        elif ok:
            mark = "OK  (no tool calling)"
            basic_only.append(m)
        else:
            mark = "FAIL"
        print(f"    {mark:<22} {m:<46} {dt:5.1f}s  {note}")

    print("\n" + "=" * 72)
    if good:
        print("  RECOMMENDED (chat + tool calling, fastest first):")
        for m in good:
            print(f"     {m}")
        best = good[0]
    elif basic_only:
        print("  Only chat models work (JARVIS cannot use tools -> far less useful):")
        for m in basic_only:
            print(f"     {m}")
        best = basic_only[0]
    else:
        print("  No chat model worked with this key.")
        show_ollama_help()
        return

    stt = [m for m in ("whisper-large-v3-turbo", "whisper-large-v3") if m in whisper]
    if stt:
        print(f"\n  Speech-to-text: {', '.join(stt)}")
    else:
        print("\n  [WARN] No Whisper model on this key -> JARVIS will use the free")
        print("         Google speech recogniser instead (still works).")

    if write:
        try:
            cfg = json.load(open(CONFIG_PATH, encoding="utf-8"))
        except Exception:                                   # noqa: BLE001
            cfg = {}
        cfg["llm_provider"] = "groq"
        cfg["llm_models"] = (good + basic_only)[:3]
        if stt:
            cfg["stt_models"] = stt
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        print(f"\n  [ OK ] config.json updated -> llm_models = {cfg['llm_models']}")
    else:
        print(f"\n  To apply automatically run:   python list_models.py --write")
        print(f"  or edit config.json by hand:  \"llm_models\": [\"{best}\"]")
    print()


def show_ollama_help():
    print("""  ====================================================================
  ALTERNATIVE: run the brain on your own PC (no API key, no internet)
  ====================================================================
  Ollama is a one-click local model server.

    1. Download and install:   https://ollama.com/download
    2. Open a terminal and pull a model (pick one):
           ollama pull gpt-oss:20b        # ~14 GB, needs 16 GB RAM  <- best
           ollama pull qwen3:8b           # ~5 GB,  needs 8 GB RAM
           ollama pull gemma3:4b          # ~3 GB,  needs 8 GB RAM    <- weakest
    3. In config.json set:
           "llm_provider": "ollama",
           "ollama_model": "gpt-oss:20b"
    4. python doctor.py        (section 6 should now say OK)
       python jarvis.py

  Note: without a Groq key, speech-to-text falls back to the free Google
  recogniser, and replies are slower (a local GPU helps a lot).
  All local commands (open/close apps, volume, YouTube, files, notes...)
  keep working no matter which brain you use.
""")


if __name__ == "__main__":
    main()
