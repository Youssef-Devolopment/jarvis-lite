# JARVIS Lite — the 28-skill sip of JARVIS

![license](https://img.shields.io/badge/license-MIT-green)
![platform](https://img.shields.io/badge/platform-Windows%2010%2F11-lightgrey)

Same brain family as [JARVIS](https://github.com/Youssef-Devolopment/jarvis)
(full build: 133 skills), trimmed to the essentials: **28 skills**
(time, math, notes, todos, timer, weather, wiki, crypto, translate,
dictionary, quotes, FX, web search/fetch/read, screenshots, volume,
brightness, lock, launching apps, VSCode-side helpers, plus one
community plugin) behind one minimal chat page on **port 5002**.

No councils, no app learner, no MCP layer — if you outgrow it,
the full build is one command away.

## Install (Windows)

```bat
git clone https://github.com/Youssef-Devolopment/jarvis-lite.git
cd jarvis-lite
py -3.10 -m venv .venv
.venv\Scripts\activate
pip install -r requirements-lite.txt
copy .env.example .env   :: then fill in DEEPSEEK_API_KEY
python run.py            :: http://127.0.0.1:5002
```

Needs a real `DEEPSEEK_API_KEY` (any OpenAI-compatible base URL);
without one the server refuses to boot — that's by design here,
skills-only mode lives in the full build.

## Use it

Open `http://127.0.0.1:5002`, click a skill chip or type:

- `tell me the time` · `2+2*2` · `set a timer for 5 minutes`
- `open notepad` · `search for quantum dots` · `note remember milk`

API: `GET /api/info` (mood, skill list + groups),
`POST /api/chat` (`{text, sid}` → `{reply}`),
`GET /api/command` (SSE — streams the same reply live).

## HUD

The head-up display from the full build, included here: press
**Ctrl+Alt+J** (or the **HUD** button, or `Alt+Space`) to summon a
frameless always-on-top bar that streams answers as they are written,
flashes green on alerts (timers, reminders), and hides on Esc.
`GET /api/overlay/state` / `POST /api/overlay/toggle` drive it from
the page.

## Library

The **Library** panel installs extra skill packs without touching the
shipped set: 18 packs (ROT13/caesar ciphers, anagrams, weekday math,
leet speak, word counter, and more) with live search, one-click
install/remove, and **Import** — drop in your own pack `.py` (it is
validated first: `valve`, `subprocess`, `shutil` and friends are
rejected before anything is written).

API: `GET /api/library`, `POST /api/library/skill`
(`{id, remove}`), `POST /api/library/import` (multipart file).

## Health

```bat
.venv\Scripts\python.exe -m py_compile (Get-ChildItem -Recurse -Filter *.py)
node --check static/js/lite.js
```
