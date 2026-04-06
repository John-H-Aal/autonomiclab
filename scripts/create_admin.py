"""One-time script: create the initial admin user in users.db.

Run from the project root:
    python scripts/create_admin.py

Or in an installed build, run from the folder that contains the .exe:
    python create_admin.py
"""

from __future__ import annotations

import getpass
import sys
from pathlib import Path

# Allow running from either the project root or the scripts/ folder.
sys.path.insert(0, str(Path(__file__).parent.parent))

from autonomiclab.auth.models import Role, User
from autonomiclab.auth.user_store import UserStore


def main() -> None:
    # Default to the project root (matches AppSettings.users_db_path in dev).
    db_path = Path(__file__).parent.parent / "users.db"

    print("AutonomicLab — opret første administrator")
    print(f"Database: {db_path}\n")

    store = UserStore(db_path)

    username = input("Brugernavn: ").strip()
    if not username:
        print("Brugernavn må ikke være tomt.")
        sys.exit(1)

    if store.get_user(username):
        print(f"Brugeren '{username}' eksisterer allerede.")
        sys.exit(1)

    display_name = input("Visningsnavn: ").strip() or username

    while True:
        pw1 = getpass.getpass("Adgangskode: ")
        pw2 = getpass.getpass("Gentag:      ")
        if pw1 == pw2 and pw1:
            break
        print("Adgangskoderne stemmer ikke overens, eller er tomme.  Prøv igen.\n")

    user = User(
        username=username,
        display_name=display_name,
        password_hash=UserStore.hash_password(pw1),
        role=Role.ADMIN,
    )
    store.add_user(user)
    print(f"\nBruger '{username}' (admin) oprettet i {db_path}")


if __name__ == "__main__":
    main()
