import subprocess

from config import AUDIO_DIR


def convert_to_speech(text, filename):
    """Run the VoxCPM2 CLI on text. Saves a wav in audio/ and returns its path."""
    out_path = f"{AUDIO_DIR}/{filename}.wav"
    # adjust the command/flags to match your VoxCPM2 install
    subprocess.run(["voxcpm", "--text", text, "--output", out_path], check=True)
    return out_path
