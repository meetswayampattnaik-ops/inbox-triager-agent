"""Loads settings from environment variables (.env supported)."""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

LABELS = ["Urgent", "Action Required", "FYI", "Newsletter", "Promotions", "Personal", "Spam"]


@dataclass
class Settings:
    provider: str = os.getenv("LLM_PROVIDER", "groq").lower()
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.1")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")

    mode: str = os.getenv("MAILBOX_MODE", "demo").lower()
    max_emails: int = int(os.getenv("MAX_EMAILS", "10"))
    imap_host: str = os.getenv("IMAP_HOST", "imap.gmail.com")
    imap_user: str = os.getenv("IMAP_USER", "")
    imap_password: str = os.getenv("IMAP_PASSWORD", "")
    imap_is_gmail: bool = os.getenv("IMAP_IS_GMAIL", "true").lower() == "true"
    drafts_folder: str = os.getenv("IMAP_DRAFTS_FOLDER", "[Gmail]/Drafts")
    user_name: str = os.getenv("USER_NAME", "Me")

    @property
    def model(self) -> str:
        return {"groq": self.groq_model, "ollama": self.ollama_model}.get(self.provider, self.anthropic_model)
