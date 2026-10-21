# CLI to create the superuser (or reset its password); registration is off.
import argparse
import asyncio

from fastapi_users.password import PasswordHelper
from sqlmodel import select

from app.auth.models import User
from app.core.db import async_session_maker


async def create_superuser(email: str, password: str) -> bool:
    """Create the user, or reset its password. Returns True when created."""
    async with async_session_maker() as session:
        user = (await session.exec(select(User).where(User.email == email))).first()
        created = user is None
        if created:
            user = User(email=email, hashed_password="")
        user.hashed_password = PasswordHelper().hash(password)
        user.is_active = True
        user.is_superuser = True
        user.is_verified = True
        session.add(user)
        await session.commit()
    return created


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.auth.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    cmd = sub.add_parser("create-superuser", help="create or reset the superuser")
    cmd.add_argument("email")
    cmd.add_argument("password")
    args = parser.parse_args()
    created = asyncio.run(create_superuser(args.email, args.password))
    print(f"{'created' if created else 'updated'} superuser {args.email}")


if __name__ == "__main__":
    main()
