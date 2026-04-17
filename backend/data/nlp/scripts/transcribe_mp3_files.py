from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from intake_iq.processors import AudioProcessor  # noqa: E402


TARGET_DIRS = [
    Path(__file__).resolve().parent / "calls_w_agent",
    Path(__file__).resolve().parent / "calls_wout_agent",
]


def load_backend_env() -> None:
    """Load key=value pairs from backend/.env into environment."""
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def collect_mp3_files() -> list[Path]:
    files: list[Path] = []
    for directory in TARGET_DIRS:
        if directory.exists():
            files.extend(sorted(directory.glob("*.mp3")))
    return files


async def main() -> int:
    load_backend_env()

    mp3_files = collect_mp3_files()
    if not mp3_files:
        print("No MP3 files found.")
        return 0

    processor = AudioProcessor()
    generated = 0

    for mp3_path in mp3_files:
        output_path = mp3_path.with_name(f"{mp3_path.stem}_transcribed.txt")
        try:
            result = await processor.process(mp3_path)
            output_path.write_text(result["text"] + "\n", encoding="utf-8")
            generated += 1
            print(f"Transcribed: {mp3_path} -> {output_path}")
        except Exception as exc:
            print(f"Failed: {mp3_path} ({exc})")

    print(f"Done. Transcribed files: {generated}/{len(mp3_files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
