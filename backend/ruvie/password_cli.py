"""Set the initial password for an existing domain user."""

import argparse
import getpass

from ruvie.config import load_settings
from ruvie.database import create_database_engine, create_session_factory
from ruvie.services.auth import AuthService


def main() -> int:
    parser = argparse.ArgumentParser(description="Provision a password for an existing user")
    parser.add_argument("email", help="Email of an existing user (does not create accounts)")
    args = parser.parse_args()
    password = getpass.getpass("New password (minimum 12 characters): ")
    confirmation = getpass.getpass("Confirm password: ")
    if len(password) < 12 or len(password) > 1024:
        parser.error("password must contain between 12 and 1024 characters")
    if password != confirmation:
        parser.error("passwords do not match")

    engine = create_database_engine(load_settings().database_url)
    try:
        with create_session_factory(engine)() as session:
            if not AuthService(session).set_existing_user_password(args.email, password):
                parser.error("no existing user has that email")
    finally:
        engine.dispose()
    print("Password configured for existing user.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
