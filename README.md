# JARVIS Lite — the 25-skill sip of JARVIS

![license](https://img.shields.io/badge/license-MIT-green)
![platform](https://img.shields.io/badge/platform-Windows%2010%2F11-lightgrey)

Same brain family as [JARVIS](https://github.com/Youssef-Devolopment/jarvis)
(full build: 125 skills), trimmed to the essentials: **26 skills**
(time, math, notes, todos, timer, weather, wiki, crypto, translate,
dictionary, quotes, FX, web search/fetch/read, screenshots, volume,
brightness, lock, launching apps, VSCode-side helpers) behind one
minimal chat page on **port 5002**.

No overlay HUD, no councils, no app learner, no auto skill maker —
if you outgrow it, the full build is one command away.

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
`POST /api/chat` (`{text, sid}` → `{reply}`).

## Health

```bat
.venv\Scripts\python.exe -m py_compile (Get-ChildItem -Recurse -Filter *.py)
node --check static/js/lite.js
```
