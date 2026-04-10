from pathlib import Path
import argparse
import os
import sys
import tempfile
import re

from openai import OpenAI


DEFAULT_DIRS = [
    Path("backend/data/nlp/calls_w_agent"),
    Path("backend/data/nlp/calls_wout_agent"),
]

VOICE_POOL = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
FEMALE_VOICES = ["nova", "shimmer"]
MALE_VOICES = ["onyx", "echo", "alloy", "fable"]
FEMALE_NAMES = {
    "erica",
    "alana",
    "priya",
    "tiana",
    "maya",
    "janet",
    "priyanka",
    "serena",
}
MALE_NAMES = {
    "marcus",
    "leo",
    "daniel",
    "jose",
    "evan",
    "luis",
    "noah",
    "andre",
    "brandon",
    "caleb",
}


def build_tts_input(text: str, source_name: str) -> str:
    """Normalize content and strip metadata labels for smoother speech."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    filtered = []
    skip_prefixes = {
        "Title:",
        "Outcome:",
        "Caller Name:",
        "Employer:",
        "Event Datetime:",
        "Injury Type:",
        "Urgency:",
        "Voicemail:",
    }

    for line in lines:
        if any(line.startswith(prefix) for prefix in skip_prefixes):
            continue
        filtered.append(line)

    if not filtered:
        raise ValueError(f"No spoken content found in {source_name}")

    return "\n".join(filtered)


def synthesize_to_mp3_file(client: OpenAI, text: str, voice: str, model: str, output_path: Path) -> None:
    synthesize_to_mp3_file_with_style(
        client=client,
        text=text,
        voice=voice,
        model=model,
        output_path=output_path,
        instructions=None,
        speed=0.97,
    )


def synthesize_to_mp3_file_with_style(
    client: OpenAI,
    text: str,
    voice: str,
    model: str,
    output_path: Path,
    instructions: str | None,
    speed: float,
) -> None:
    # Some SDK/API versions may not support instructions/speed for speech.create.
    # Fall back gracefully to the baseline call when unsupported.
    try:
        with client.audio.speech.with_streaming_response.create(
            model=model,
            voice=voice,
            input=text,
            response_format="mp3",
            instructions=instructions,
            speed=speed,
        ) as response:
            response.stream_to_file(str(output_path))
    except TypeError:
        with client.audio.speech.with_streaming_response.create(
            model=model,
            voice=voice,
            input=text,
            response_format="mp3",
        ) as response:
            response.stream_to_file(str(output_path))


def parse_dialogue_turns(text: str) -> list[tuple[str, str]]:
    turns: list[tuple[str, str]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("Agent:"):
            turns.append(("Agent", line.removeprefix("Agent:").strip()))
        elif line.startswith("Caller:"):
            turns.append(("Caller", line.removeprefix("Caller:").strip()))
    return [(speaker, utterance) for speaker, utterance in turns if utterance]


def extract_agent_name(turns: list[tuple[str, str]]) -> str | None:
    for speaker, utterance in turns:
        if speaker != "Agent":
            continue
        lowered = utterance.lower()
        markers = ["my name is ", "this is "]
        for marker in markers:
            if marker in lowered:
                start = lowered.index(marker) + len(marker)
                candidate = utterance[start:].strip().split()[0].strip(".,!?")
                if candidate:
                    return candidate
    return None


def extract_caller_name_from_dialogue(turns: list[tuple[str, str]]) -> str | None:
    for speaker, utterance in turns:
        if speaker != "Caller":
            continue
        # Prefer explicit "my name is X" pattern.
        explicit = re.search(r"my name is\s+([A-Z][a-z]+)", utterance)
        if explicit:
            return explicit.group(1)
        # Match "I'm First Last" while avoiding "I'm calling..." style phrases.
        im_name = re.search(r"\bI(?:'| a)m\s+([A-Z][a-z]+)\s+([A-Z][a-z]+)\b", utterance)
        if im_name:
            return im_name.group(1)
    return None


def extract_metadata_value(text: str, key: str) -> str | None:
    prefix = f"{key}:"
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix):
            value = stripped[len(prefix):].strip()
            return value if value else None
    return None


def name_gender(name: str | None) -> str:
    if not name:
        return "unknown"
    token = name.strip().split()[0].lower()
    if token in FEMALE_NAMES:
        return "female"
    if token in MALE_NAMES:
        return "male"
    return "unknown"


def pick_voice(gender: str, seed: int) -> str:
    if gender == "female":
        pool = FEMALE_VOICES
    elif gender == "male":
        pool = MALE_VOICES
    else:
        pool = VOICE_POOL
    return pool[seed % len(pool)]


def merge_mp3_segments(segment_paths: list[Path], output_path: Path) -> None:
    with output_path.open("wb") as out:
        for path in segment_paths:
            out.write(path.read_bytes())


def generate_mp3_for_file(client: OpenAI, txt_path: Path, model: str, voice_index: int) -> tuple[Path, str]:
    output_path = txt_path.with_suffix(".mp3")
    raw_text = txt_path.read_text(encoding="utf-8")
    is_dialogue = "calls_w_agent" in txt_path.parts

    if not is_dialogue:
        caller_name = extract_metadata_value(raw_text, "Caller Name")
        caller_gender = name_gender(caller_name)
        voicemail_voice = pick_voice(caller_gender, voice_index)
        speech_input = build_tts_input(raw_text, txt_path.name)
        voicemail_style = (
            "Speak naturally like a real voicemail: conversational, clear, and human. "
            "Use light emotion that matches a workplace injury report (concerned but composed), "
            "with brief pauses at punctuation and steady pacing."
        )
        synthesize_to_mp3_file_with_style(
            client,
            speech_input,
            voicemail_voice,
            model,
            output_path,
            instructions=voicemail_style,
            speed=0.97,
        )
        return output_path, f"caller={caller_name or 'unknown'}({caller_gender}), voice={voicemail_voice}"

    turns = parse_dialogue_turns(raw_text)
    if not turns:
        raise ValueError(f"No Agent/Caller turns found in {txt_path.name}")

    agent_name = extract_agent_name(turns)
    caller_name = extract_caller_name_from_dialogue(turns)
    agent_gender = name_gender(agent_name)
    caller_gender = name_gender(caller_name)

    agent_voice = pick_voice(agent_gender, voice_index)
    caller_voice = pick_voice(caller_gender, voice_index + 3)
    if caller_voice == agent_voice:
        caller_voice = pick_voice(caller_gender, voice_index + 1)

    with tempfile.TemporaryDirectory(prefix="tts_segments_") as tmpdir:
        tmpdir_path = Path(tmpdir)
        segment_paths: list[Path] = []
        for idx, (speaker, utterance) in enumerate(turns, start=1):
            voice = agent_voice if speaker == "Agent" else caller_voice
            # Keep natural speech without spoken role labels.
            segment_text = utterance
            segment_path = tmpdir_path / f"segment_{idx:03d}.mp3"
            if speaker == "Agent":
                style = (
                    "Customer service agent tone: warm, professional, empathetic, and calm. "
                    "Speak naturally with subtle pauses and clear enunciation."
                )
                speed = 0.96
            else:
                style = (
                    "Injured worker caller tone: natural and conversational, mildly stressed but clear. "
                    "Keep realistic pacing and emotion, without exaggeration."
                )
                speed = 0.98
            synthesize_to_mp3_file_with_style(
                client,
                segment_text,
                voice,
                model,
                segment_path,
                instructions=style,
                speed=speed,
            )
            segment_paths.append(segment_path)
        merge_mp3_segments(segment_paths, output_path)

    return output_path, (
        f"agent={agent_name or 'unknown'}({agent_gender}) voice={agent_voice}, "
        f"caller={caller_name or 'unknown'}({caller_gender}) voice={caller_voice}"
    )


def collect_txt_files(target_dirs: list[Path]) -> list[Path]:
    files: list[Path] = []
    for directory in target_dirs:
        if directory.exists():
            files.extend(sorted(directory.glob("*.txt")))
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate MP3 files from workers comp text samples.")
    parser.add_argument("--model", default="gpt-4o-mini-tts", help="OpenAI TTS model (default: gpt-4o-mini-tts)")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing mp3 files if they already exist",
    )
    args = parser.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY is not set in the environment.", file=sys.stderr)
        return 1

    txt_files = collect_txt_files(DEFAULT_DIRS)
    if not txt_files:
        print("No .txt files found in expected directories.")
        return 0

    client = OpenAI()
    generated = 0
    skipped = 0

    for idx, txt_path in enumerate(txt_files):
        mp3_path = txt_path.with_suffix(".mp3")
        if mp3_path.exists() and not args.overwrite:
            skipped += 1
            print(f"Skipping existing: {mp3_path}")
            continue

        try:
            out, voice_info = generate_mp3_for_file(client, txt_path, args.model, idx)
            generated += 1
            print(f"Generated: {out} ({voice_info})")
        except Exception as exc:
            print(f"Failed for {txt_path}: {exc}", file=sys.stderr)

    print(f"Done. Generated={generated}, Skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
