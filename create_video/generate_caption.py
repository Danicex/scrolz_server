import os
import json
import whisper
from moviepy import AudioFileClip, ColorClip, TextClip, CompositeVideoClip
from config import CAPTION_DIR

SETTINGS_PATH = os.path.join(os.path.dirname(__file__), "video_settings.json")


def load_video_settings(video_tmpl):
    with open(SETTINGS_PATH, "r") as f:
        settings = json.load(f)
    if video_tmpl not in settings:
        raise ValueError(f"Unknown video_tmpl: {video_tmpl}")
    return settings[video_tmpl]


def save_captions(project_name, segments):
    """Write each caption segment to CAPTION_DIR/{project_name}_{i}.txt"""
    os.makedirs(CAPTION_DIR, exist_ok=True)
    saved_paths = []
    for i, seg in enumerate(segments):
        path = os.path.join(CAPTION_DIR, f"{project_name}_{i}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(seg["text"].strip())
        saved_paths.append(path)
    return saved_paths


def create_captioned_video(audio_path, project_name, video_tmpl ):
    # 1. Load video template settings
    tmpl = load_video_settings(video_tmpl)
    width, height = tmpl["width"], tmpl["height"]
    bg_transparent = tmpl.get("bg_transparent", False)

    # 2. Load audio and get its duration
    print("Loading audio file...")
    audio = AudioFileClip(audio_path)
    duration = audio.duration

    # 3. Generate captions via Whisper
    print("Transcribing audio...")
    model = whisper.load_model("base", device="cpu")
    result = model.transcribe(audio_path)
    segments = result.get("segments", [])

    # 3a. Persist captions to CAPTION_DIR
    caption_paths = save_captions(project_name, segments)
    print(f"Saved {len(caption_paths)} caption files to {CAPTION_DIR}")

    # 4. Create background
    print("Creating video background...")
    if bg_transparent:
        # Fully transparent background
        background = ColorClip(size=(width, height), color=(0, 0, 0), duration=duration)
        background = background.with_opacity(0)
    else:
        background = ColorClip(size=(width, height), color=(0, 0, 0), duration=duration)

    # 5. Build caption overlays
    text_clips = []
    print("Rendering captions...")
    for seg in segments:
        text = seg["text"].strip()
        start_time = seg["start"]
        end_time = seg["end"]

        if start_time > duration:
            continue
        if end_time > duration:
            end_time = duration

        txt_clip = (
            TextClip(
                text=text,
                font_size=24,
                color="white",
                font="/home/tegabytes/Downloads/Urbanist/static/Urbanist-Bold.ttf",
                method="caption",
                size=(width - 40, None),
            )
            .with_start(start_time)
            .with_end(end_time)
            .with_position(("center", "center"))
        )
        text_clips.append(txt_clip)

    # 6. Composite
    video = CompositeVideoClip([background] + text_clips)
    video = video.with_audio(audio)

    # 7. Render
    print("Compiling final video file...")
    video.write_videofile(
        fps=24,
        codec="libx264",
        audio_codec="aac",
    )

    audio.close()
    video.close()
    return caption_paths

# if __name__ == "__main__":
#     audio_file = "/home/tegabytes/Documents/projects/scrolz-server/create_video/sample/test_tts_001.mp3"
#     create_captioned_video(
#         audio_path=audio_file,
#         project_name="test_tts_001",
#         video_tmpl="video_tmpl_2",
#     )