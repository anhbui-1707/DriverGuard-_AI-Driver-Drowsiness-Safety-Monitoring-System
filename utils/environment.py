import os
from config import ROOT


def load_local_env():
    """Small optional .env reader; does not overwrite existing environment."""
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.lstrip().startswith("#") and "=" in line:
                name, value = line.split("=", 1)
                if name.strip() in ("GEMINI_API_KEY", "GEMINI_MODEL"):
                    os.environ.setdefault(name.strip(), value.strip().strip("\"'"))
