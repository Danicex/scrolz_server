import os

from dotenv import load_dotenv

load_dotenv()  # reads .env (ANTHROPIC_API_KEY, POSTGRES_URL)

POSTGRES_URL = os.getenv("POSTGRES_URL")
LLM_MODEL = "claude-sonnet-5-5"

AUDIO_DIR = "audio"
JSON_DIR = "json"
IMAGES_DIR = "images"
CAPTION_DIR = "captions"
VIDEO_ASSET = "video_asset"
OUTPUT_VIDEO_DIR = "videos"
PROCESS_PDF_DIR = "process_pdf"
for folder in (AUDIO_DIR, JSON_DIR, IMAGES_DIR, CAPTION_DIR, VIDEO_ASSET):
    os.makedirs(folder, exist_ok=True)
