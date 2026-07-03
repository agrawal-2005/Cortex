"""Mint a new API key. The plaintext key is printed ONCE — store it safely.

Run from the repo root:

    PYTHONPATH=. .venv/bin/python scripts/create_api_key.py "my key name"
"""

import asyncio
import sys

from backend.database import async_session_factory
from backend.knowledge.models import ApiKey
from backend.security.auth import generate_api_key, hash_api_key


async def main(name: str) -> None:
    key = generate_api_key()
    async with async_session_factory() as db:
        db.add(
            ApiKey(
                name=name,
                key_hash=hash_api_key(key),
                prefix=key[:8],
            )
        )
        await db.commit()
    print(f"API key created for '{name}'. This is shown ONCE:\n\n  {key}\n")
    print("Send it in the X-API-Key header.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: create_api_key.py <name>")
    asyncio.run(main(sys.argv[1]))
