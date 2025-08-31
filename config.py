import os
from pathlib import Path
from dotenv import load_dotenv
from peewee import SqliteDatabase

# .envファイルの読み込み
load_dotenv()

# データベース接続
db_file = os.getenv("DATABASE", "spotter.db")
db = SqliteDatabase(db_file)

# 画像のアップロード先を指定
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 秘密鍵設定
SECRET_KEY = os.getenv("SECRET_KEY")
