# 📬 Inbox Triager Agent

A **tool-using AI agent** that reads your unread email, labels each message, flags urgent ones, and writes draft replies for you to review.

- **Runs for free** using Groq (free cloud API, no credit card) or Ollama (fully local on your laptop).
- Optionally works with the paid Claude API.
- **Safety:** the agent can only create **drafts**. There is no "send" tool.

## What it does

| Step | Tool the agent calls | Result |
|------|----------------------|--------|
| 1 | `list_unread_emails` | Gets unread messages |
| 2 | `read_email` | Reads each body |
| 3 | `apply_label` | Urgent / Action Required / FYI / Newsletter / Promotions / Personal / Spam |
| 4 | `flag_urgent` | Stars time-sensitive emails with a reason |
| 5 | `create_draft_reply` | Saves a draft in your Drafts folder |

The model decides which tools to call and in what order. The code executes them and feeds results back (the agent loop).

## Architecture

```
cli.py -> agent.py (loop) <-> LLM (Groq | Ollama | Claude)
              |
           tools.py (schemas + safe dispatcher)
              |
         mailbox.py -> DemoMailbox (JSON) | ImapMailbox (Gmail/IMAP)
```

## Setup (Windows PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

### Option A: Groq (free, recommended)
1. Sign up at https://console.groq.com (email only, no card).
2. Create a key at https://console.groq.com/keys.
3. Put it in `.env` as `GROQ_API_KEY=...` and keep `LLM_PROVIDER=groq`.

### Option B: Ollama (free, offline)
1. Install from https://ollama.com/download and run `ollama pull llama3.1`.
2. In `.env` set `LLM_PROVIDER=ollama`.
Needs roughly 8 GB RAM; small local models are less reliable than Groq's.

## Run

```powershell
$env:PYTHONPATH="src"
python -m inbox_triager.cli --mode demo
```
Mac/Linux: `PYTHONPATH=src python -m inbox_triager.cli --mode demo`

Output: live tool logs, a summary, and `output/triage_report.json`.

### Real Gmail
1. Turn on 2-Step Verification, create an **App Password**, and enable IMAP in Gmail.
2. In `.env` set `MAILBOX_MODE=imap`, `IMAP_USER`, `IMAP_PASSWORD`.
3. Run `python -m inbox_triager.cli --mode imap` (test on a throwaway account first).

## Tests (no API key or internet needed)

```powershell
python -m pytest -q
```
Includes a full agent-loop test using a fake model.

## Security notes

- Never commit `.env` (already in `.gitignore`).
- Email content is untrusted: the prompt tells the model to ignore instructions inside emails, and the toolset is limited to labels, flags and drafts.
- Email text is sent to your chosen LLM provider (not with Ollama, which stays local).
- Free tiers have rate limits; the agent waits and retries automatically.

## Ideas to extend
Human approval before saving drafts, a calendar tool, Telegram/Slack alerts, scheduled runs, an accuracy eval set.

## License
MIT
