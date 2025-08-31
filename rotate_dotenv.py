# .envファイル内のsecret_keyを更新
import re
import secrets

new_secret_key = secrets.token_urlsafe(48)

with open(".env", "r", encoding="utf-8") as f:
    content = f.read()

content = re.sub(r"(?m)^\s*SECRET_KEY\s*=.*$", f"SECRET_KEY={new_secret_key}", content, count=1)

with open(".env", "w", encoding="utf-8") as f:
    f.write(content)
