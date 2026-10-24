import os
import subprocess
from urllib.parse import urlparse

from utils.use_llm import generate_visuals
from config import VIDEO_ASSET


def _guess_extension(url: str) -> str:
    """Best-effort extension from a URL path; fall back to .bin."""
    path = urlparse(url).path
    ext = os.path.splitext(path)[1].lower()
    # strip query-derived junk like ".jpg?x=1" already handled by urlparse
    if ext and len(ext) <= 5:
        return ext
    return ".bin"


def get_visuals(text: str, project_name: str) -> bool:
    url_list = generate_visuals(text)

    if not url_list:
        raise ValueError("generate_visuals returned no URLs")

    os.makedirs(VIDEO_ASSET, exist_ok=True)

    for idx, url in enumerate(url_list):
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            raise ValueError(f"Invalid URL at index {idx}: {url!r}")

        ext = _guess_extension(url)
        out_path = os.path.join(VIDEO_ASSET, f"{project_name}_{idx}{ext}")

        try:
            subprocess.run(
                [
                    "curl",
                    "-L",              # follow redirects
                    "--fail",          # HTTP errors -> non-zero exit
                    "--silent",
                    "--show-error",
                    "-o", out_path,
                    url,
                ],
                check=True,
            )
        except subprocess.CalledProcessError as e:
            # Clean up partial file if any
            if os.path.exists(out_path) and os.path.getsize(out_path) == 0:
                os.remove(out_path)
            raise RuntimeError(f"Failed to download {url}: {e}") from e

    return True