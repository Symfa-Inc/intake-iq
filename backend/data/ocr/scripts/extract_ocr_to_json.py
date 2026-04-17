from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


SUPPORTED_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"}


def load_backend_env() -> None:
    """Load key=value pairs from backend/.env into os.environ."""
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def collect_files(input_dir: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(input_dir.rglob("*")):
        if not path.is_file():
            continue
        if "scripts" in path.parts:
            continue
        if path.suffix.lower() in SUPPORTED_SUFFIXES:
            files.append(path)
    return files


async def run(input_dir: Path, output_dir: Path, overwrite: bool) -> int:
    from intake_iq.processors import OCRProcessor  # noqa: E402

    load_backend_env()
    output_dir.mkdir(parents=True, exist_ok=True)

    processor = OCRProcessor()
    input_files = collect_files(input_dir)
    if not input_files:
        print(f"No supported OCR files found in {input_dir}")
        return 0

    processed = 0
    skipped = 0
    failed = 0

    for source_path in input_files:
        out_name = f"{source_path.stem}_ocr.json"
        output_path = output_dir / out_name
        if output_path.exists() and not overwrite:
            skipped += 1
            print(f"Skipping existing: {output_path}")
            continue

        try:
            result = await processor.process(source_path)
            output_path.write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            processed += 1
            print(f"Processed: {source_path} -> {output_path}")
        except Exception as exc:
            failed += 1
            print(f"Failed: {source_path} ({exc})")

    print(f"Done. processed={processed}, skipped={skipped}, failed={failed}")
    return 0 if failed == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract OCR JSON from PDF/image files with OCRProcessor."
    )
    parser.add_argument(
        "--input-dir",
        default=str(PROJECT_ROOT / "data" / "ocr"),
        help="Directory to scan for PDF/image files (default: backend/data/ocr)",
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "data" / "ocr" / "output"),
        help="Directory to write OCR JSON outputs (default: backend/data/ocr/output)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing JSON output files",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir).resolve()
    output_dir = Path(args.output_dir).resolve()

    if not input_dir.exists():
        print(f"Input directory does not exist: {input_dir}")
        return 1

    return asyncio.run(run(input_dir=input_dir, output_dir=output_dir, overwrite=args.overwrite))


if __name__ == "__main__":
    raise SystemExit(main())
