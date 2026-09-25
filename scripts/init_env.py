"""Create private local configuration without printing generated credentials."""

import secrets
from pathlib import Path

path = Path(__file__).resolve().parents[1] / ".env"
if path.exists():
    print("Existing .env preserved.")
else:
    path.write_text(
        "EICC_DEMO_MODE=true\nEICC_SECURE_COOKIES=false\nEICC_POSTGRES_PASSWORD="
        + secrets.token_hex(32)
        + "\n",
        encoding="utf-8",
    )
    path.chmod(0o600)
    print("Created private .env with a generated database password. No credential was printed.")
