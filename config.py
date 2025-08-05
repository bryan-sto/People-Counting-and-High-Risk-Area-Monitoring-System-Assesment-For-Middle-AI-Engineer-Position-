import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL: str = os.getenv("DATABASE_URL")
if DATABASE_URL is None:
    raise ValueError("FATAL: DATABASE_URL environment variable is not set.")

MODEL_PATH: str = 'yolo11n.pt'