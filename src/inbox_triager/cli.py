"""Command line entry point:  python -m inbox_triager.cli"""
import argparse
import json
from pathlib import Path

from .agent import run_agent
from .config import Settings
from .mailbox import DemoMailbox, ImapMailbox


def main() -> None:
    parser = argparse.ArgumentParser(description="AI email inbox triager (labels, flags, drafts).")
    parser.add_argument("--mode", choices=["demo", "imap"], help="Mailbox: demo (sample emails) or imap (real inbox)")
    parser.add_argument("--provider", choices=["groq", "ollama", "anthropic"], help="Override LLM_PROVIDER from .env")
    parser.add_argument("--quiet", action="store_true", help="Hide per-step tool logs")
    args = parser.parse_args()

    settings = Settings()
    if args.provider:
        settings.provider = args.provider
    mode = args.mode or settings.mode

    if mode == "demo":
        mailbox = DemoMailbox()
    else:
        if not (settings.imap_user and settings.imap_password):
            raise SystemExit("IMAP_USER and IMAP_PASSWORD must be set in .env for imap mode.")
        mailbox = ImapMailbox(settings.imap_host, settings.imap_user, settings.imap_password,
                              settings.imap_is_gmail, settings.drafts_folder)

    print(f"Mailbox: {mode} | Provider: {settings.provider} | Model: {settings.model}\n")
    try:
        summary = run_agent(mailbox, settings, verbose=not args.quiet)
    finally:
        if hasattr(mailbox, "close"):
            mailbox.close()

    out = Path("output/triage_report.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(mailbox.report(), indent=2))

    print("\n=== SUMMARY ===")
    print(summary)
    print(f"\nFull report saved to {out}")


if __name__ == "__main__":
    main()
