import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# 🔥 FORCE absolute path (no guessing)
env_path = os.path.join(BASE_DIR, ".env")

print("📂 Looking for .env at:", env_path)
print("📂 Exists?", os.path.exists(env_path))

load_dotenv(env_path)

print("✅ MONGO_URI:", os.getenv("MONGO_URI"))


