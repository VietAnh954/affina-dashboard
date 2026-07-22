"""
Generate bcrypt password hashes for Affina Dashboard auth.

Usage:
  python scripts/generate_password_hash.py

Paste the output into Streamlit Cloud Secrets under [auth.users.USERNAME].
"""
import getpass
import sys

try:
    import bcrypt
except ImportError:
    print("bcrypt not installed. Run: pip install bcrypt")
    sys.exit(1)


def generate_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def main():
    print("=== Affina Dashboard — Password Hash Generator ===\n")

    username = input("Username: ").strip()
    if not username:
        print("Username required.")
        return

    role = input("Role (admin/head/sale) [sale]: ").strip() or "sale"
    if role not in ("admin", "head", "sale"):
        print(f"Invalid role: {role}")
        return

    display_name = input("Display name: ").strip() or username

    password = getpass.getpass("Password: ")
    if not password:
        print("Password required.")
        return
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Passwords do not match.")
        return

    pwd_hash = generate_hash(password)

    print(f"\n--- Add this to Streamlit Secrets ---\n")
    print(f'[auth.users.{username}]')
    print(f'password_hash = "{pwd_hash}"')
    print(f'role = "{role}"')
    print(f'display_name = "{display_name}"')
    print()


if __name__ == "__main__":
    main()
