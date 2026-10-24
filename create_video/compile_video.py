import itertools
import json
import os
import random
import re

from moviepy import (
    AudioFileClip,
    ColorClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    VideoFileClip,
    concatenate_videoclips,
    vfx,
)
from moviepy.audio.fx import AudioLoop, MultiplyVolume

from generate_caption import create_captioned_video  # (audio_path, project_name, video_tmpl) -> video path
from get_visuals import get_visuals  # (text, project_name) -> True, saves files in video_assets/
from config import OUTPUT_VIDEO_DIR

VIDEO_SETTINGS = "video_settings.json"
VIDEO_ASSETS_DIR = "video_assets"
DEFAULT_TMPL = "video_tmpl_1"  # used when a chunk has no "video_tmpl"
SLIDE_SECONDS = 2  # every asset (image, gif or video) is shown for 2 sec
FADE_SECONDS = 0.4  # fade/slide time at the start and end of each slide
BG_VOLUME = 0.12

IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp")
VIDEO_EXT = (".mp4", ".mov", ".webm", ".mkv", ".avi", ".gif")

bg_sound = ["audio_1", "audio_2", "audio_3"]  # paths to your background tracks


def even(n):
    """h264 needs even width/height (449 -> 448)."""
    return int(n) - int(n) % 2


# ---------- visuals ----------
def list_assets(project_name):
    """All images/gifs/videos of a project, sorted by the number in the file name (0, 1, 2 ... 10).
    Looks in video_assets/<project_name>/ first, then for video_assets/<project_name>*"""
    folder = os.path.join(VIDEO_ASSETS_DIR, project_name)
    if os.path.isdir(folder):
        files = [os.path.join(folder, f) for f in os.listdir(folder)]
    elif os.path.isdir(VIDEO_ASSETS_DIR):
        files = [
            os.path.join(VIDEO_ASSETS_DIR, f)
            for f in os.listdir(VIDEO_ASSETS_DIR)
            if f.startswith(project_name)
        ]
    else:
        files = []

    files = [f for f in files if f.lower().endswith(IMAGE_EXT + VIDEO_EXT)]

    def number(path):
        name = os.path.splitext(os.path.basename(path))[0]
        name = name.replace(project_name, "")  # so digits in the project name don't count
        found = re.findall(r"\d+", name)
        return int(found[-1]) if found else 0

    return sorted(files, key=number)


def load_asset(path, w, h, duration):
    """Image, gif or video -> clip that fills the frame and lasts `duration` sec."""
    if path.lower().endswith(VIDEO_EXT):
        clip = VideoFileClip(path, audio=False)
        clip = clip.with_effects([vfx.Loop(duration=duration)])  # loops if short, cuts if long
    else:
        clip = ImageClip(path).with_duration(duration)

    # resize so it covers the frame, then crop the middle
    scale = max(w / clip.w, h / clip.h)
    clip = clip.resized(scale)
    return clip.cropped(x_center=clip.w / 2, y_center=clip.h / 2, width=w, height=h)


def make_slideshow(assets, duration, w, h):
    """One asset every 2 sec: slides in from the right while fading in, slides out to the left while fading out."""
    slides, start, i = [], 0.0, 0
    shift = w // 4

    while assets and start < duration:
        d = min(SLIDE_SECONDS, duration - start)
        clip = load_asset(assets[i % len(assets)], w, h, d)  # fewer assets than needed -> start over
        clip = clip.with_start(start)
        clip = clip.with_effects([vfx.CrossFadeIn(FADE_SECONDS), vfx.CrossFadeOut(FADE_SECONDS)])

        def position(t, d=d):
            if t < FADE_SECONDS:  # coming from the right
                x = shift * (1 - t / FADE_SECONDS)
            elif t > d - FADE_SECONDS:  # leaving to the left
                x = -shift * (t - (d - FADE_SECONDS)) / FADE_SECONDS
            else:
                x = 0
            return (int(x), 0)

        slides.append(clip.with_position(position))
        start += SLIDE_SECONDS
        i += 1
    return slides


# ---------- one chunk ----------
def build_chunk(chunk, settings, project_name, playlist):
    tmpl = settings[chunk.get("video_tmpl") or DEFAULT_TMPL]
    w, h = even(tmpl["width"]), even(tmpl["height"])

    voice = AudioFileClip(chunk["audio"])
    duration = voice.duration

    # caption video + visuals for this chunk
    caption_path = create_captioned_video(chunk["audio"], project_name, tmpl)
    chunk["caption"] = caption_path
    get_visuals(chunk["text"], project_name)  # saves the files in video_assets/
    assets = list_assets(project_name)

    # layers, bottom to top: black -> slideshow -> caption
    layers = [ColorClip((w, h), color=(0, 0, 0), duration=duration)]
    layers += make_slideshow(assets, duration, w, h)

    # caption sits at the bottom, over the slideshow
    caption = VideoFileClip(caption_path, has_mask=bool(tmpl["bg_transparent"]))
    if caption.w != w:
        caption = caption.resized(width=w)  # fit the width, keep the shape
    caption = caption.with_duration(min(caption.duration, duration))
    layers.append(caption.with_position(("center", "bottom")))

    video = CompositeVideoClip(layers, size=(w, h)).with_duration(duration)

    # voice + (optional) background sound
    audio = voice
    if tmpl["bg_sound"] and playlist:
        bg = AudioFileClip(next(playlist)).with_effects(
            [AudioLoop(duration=duration), MultiplyVolume(BG_VOLUME)]
        )
        audio = CompositeAudioClip([voice, bg]).with_duration(duration)

    return video.with_audio(audio)


# ---------- everything ----------
def compile_video(json_path):
    project_name = os.path.splitext(os.path.basename(json_path))[0]

    with open(json_path) as f:
        data = json.load(f)
    with open(VIDEO_SETTINGS) as f:
        settings = json.load(f)

    # shuffle the background tracks and go through them in that order
    tracks = bg_sound[:]
    random.shuffle(tracks)
    playlist = itertools.cycle(tracks) if tracks else None

    clips = []
    for chunk in data.values():
        chunk["project_name"] = chunk.get("project_name") or project_name
        clips.append(build_chunk(chunk, settings, chunk["project_name"], playlist))

        with open(json_path, "w") as f:  # keeps the caption path in the json
            json.dump(data, f, indent=2)

    final = concatenate_videoclips(clips, method="compose")  # works even if templates differ in size

    os.makedirs(OUTPUT_VIDEO_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_VIDEO_DIR, f"{project_name}.mp4")
    final.write_videofile(out_path, fps=24, codec="libx264", audio_codec="aac")
    return {"dir": out_path, "status": True}