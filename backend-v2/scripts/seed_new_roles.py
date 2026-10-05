"""
Idempotent seed for the organizational roles added on top of the base four.

Inserts one user per new role (GL, TL, Scientist) if that username does not
already exist. Safe to run repeatedly and — unlike scripts/seed_data.py — it
NEVER drops or recreates tables, so it can be run against a populated database.

Usage:  python -m scripts.seed_new_roles   (run from backend-v2/)
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from src.infrastructure.database.session import async_session_factory
from src.infrastructure.database.models.user_model import UserModel
from src.infrastructure.security.password_encoder import hash_password

#  (username, password, full_name, role, department)
NEW_USERS = [
    ("gl", "gl123", "Grace Leader", "GL", "R&D"),
    ("tl", "tl123", "Tom Teamlead", "TL", "R&D"),
    ("scientist", "scientist123", "Sam Scientist", "Scientist", "R&D"),
    ("fdgl", "fdgl123", "Fiona FDGL", "FDGL", "R&D"),
    ("adgl", "adgl123", "Adam ADGL", "ADGL", "QA"),
    ("approver2", "approver2123", "Second Approver", "Approver2", "QA"),
]


async def seed_new_roles() -> None:
    async with async_session_factory() as session:
        created, skipped = [], []
        for username, password, full_name, role, department in NEW_USERS:
            existing = await session.scalar(
                select(UserModel).where(UserModel.username == username)
            )
            if existing:
                skipped.append(username)
                continue
            session.add(UserModel(
                username=username,
                password_hash=hash_password(password),
                full_name=full_name,
                role=role,
                department=department,
                is_active=True,
                created_by="system",
                modified_by="system",
            ))
            created.append(f"{username}/{password} ({role})")
        await session.commit()

    print("Created:", ", ".join(created) if created else "(none)")
    print("Skipped (already present):", ", ".join(skipped) if skipped else "(none)")


if __name__ == "__main__":
    asyncio.run(seed_new_roles())
