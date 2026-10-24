import json
import os
import re
from datetime import datetime
import asyncio
import fitz  # pymupdf

from config import IMAGES_DIR, JSON_DIR
from utils.convert_tts import convert_to_speech
from utils.use_llm import convert_to_quiz, summarize_text
import crud
from sqlmodel import Session
from database import engine

def make_name(title):
    """pdf title + current time, safe for filenames."""
    safe = re.sub(r"[^a-zA-Z0-9]+", "_", title).strip("_") or "untitled"
    return f"{safe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


async def process_pdf(pdf_path, filename, user_id: int):
    """Extract cover, title, text, images -> chunk -> fill json. Returns a dict."""
    # FIX 1: open the actual file path, not an undefined `pdf_bytes`
    doc = fitz.open(pdf_path)

    title = doc.metadata.get("title") or os.path.splitext(filename)[0]
    name = make_name(title)

    # FIX 2: ensure the output dir exists before writing
    os.makedirs(IMAGES_DIR, exist_ok=True)

    # cover image = first page rendered as png
    cover_path = os.path.join(IMAGES_DIR, f"{name}_cover.png")
    doc[0].get_pixmap(dpi=100).save(cover_path)

    # text + embedded images
    text, image_paths = "", []
    for page_num, page in enumerate(doc, start=1):
        text += page.get_text() + "\n"
        for i, img in enumerate(page.get_images(full=True), start=1):
            data = doc.extract_image(img[0])
            path = os.path.join(IMAGES_DIR, f"{name}_p{page_num}_{i}.{data['ext']}")
            with open(path, "wb") as f:
                f.write(data["image"])
            image_paths.append(path)

    # FIX 3: always close the document
    doc.close()

    json_path = convert_to_chunk(text, name)
    # ---- persist everything at the end ----
    with Session(engine) as session:
        project = crud.create_project(session, title, json_path, user_id, cover_path)
        project_id = project.id
        
    await loop_through_chunk(json_path, name, project_id)


        
    return {
        "title": title,
        "cover": cover_path,
        "images": image_paths,
        "json_path": json_path,
        "project_id": project_id,
    }


def convert_to_chunk(text, name):
    """Split text into 500-word chunks and save to json."""
    words = text.split()
    chunks = {}
    for i in range(0, len(words), 500):
        chunks[f"chunk_{i // 500 + 1}"] = {"text": " ".join(words[i : i + 500])}

    json_path = f"{JSON_DIR}/{name}.json"
    with open(json_path, "w") as f:
        json.dump(chunks, f, indent=2)
    return json_path





async def loop_through_chunk(json_path: str, name: str, project_id: int) -> int:
    """Enrich every chunk with summary/quiz/audio, save JSON, then insert into DB.
    Returns the number of chunks inserted."""

    with open(json_path, encoding="utf-8") as f:
        chunks = json.load(f)

    # 1. Enrich every chunk in memory first
    for key, chunk in chunks.items():
        text = chunk["text"]
        chunk["summarized_text"] = await summarize_text(text)
        chunk["quiz"] = await convert_to_quiz(text)
        chunk["audio"] = await convert_to_speech(text, f"{name}_{key}")
        chunk["project_name"] = name

    # 2. Persist enriched JSON once
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2)

    # 3. Insert all chunks in one DB transaction
    with Session(engine) as session:
        inserted = crud.insert_chunks(
            session=session,
            project_id=project_id,
            chunks=chunks,
        )

    return inserted
    
    
