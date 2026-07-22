"""
Test Telegram Bot connection.

Usage:
  python scripts/test_telegram.py <BOT_TOKEN> <CHAT_ID>

Example:
  python scripts/test_telegram.py 123456:ABC-DEF 987654321
"""
import json
import sys
import urllib.request


def test_telegram(bot_token: str, chat_id: str) -> None:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    message = "Affina Dashboard — Telegram alert da ket noi thanh cong!"
    data = json.dumps({
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
    }).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            if result.get("ok"):
                print("OK — Tin nhan da gui thanh cong!")
                print(f"Chat ID: {chat_id}")
                print(f"\nThem vao GitHub Secrets:")
                print(f"  TELEGRAM_BOT_TOKEN = {bot_token}")
                print(f"  TELEGRAM_CHAT_ID = {chat_id}")
            else:
                print(f"ERROR: {result}")
    except Exception as e:
        print(f"ERROR: {e}")
        print("Kiem tra lai BOT_TOKEN va CHAT_ID.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scripts/test_telegram.py <BOT_TOKEN> <CHAT_ID>")
        print("\nCach lay BOT_TOKEN:")
        print("  1. Mo Telegram, tim @BotFather")
        print("  2. Gui /newbot")
        print("  3. Dat ten bot (VD: Affina Dashboard Alert)")
        print("  4. Dat username (VD: affina_dashboard_bot)")
        print("  5. Copy token nhan duoc")
        print("\nCach lay CHAT_ID:")
        print("  1. Gui tin nhan bat ky cho bot cua ban")
        print("  2. Mo URL: https://api.telegram.org/bot<TOKEN>/getUpdates")
        print("  3. Tim 'chat':{'id': 123456789} trong JSON")
        print("  4. So do chinh la CHAT_ID")
        sys.exit(1)

    test_telegram(sys.argv[1], sys.argv[2])
