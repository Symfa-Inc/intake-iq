from __future__ import annotations

from abc import ABC, abstractmethod
import base64
from enum import Enum
class StrEnum(str, Enum):
    """Compatibility fallback for Python versions without enum.StrEnum."""

from pathlib import Path
from typing import Any
import os

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from openai import AsyncOpenAI
from pydantic import validate_call


class Processor(ABC):
    """Base contract for all modality processors."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable processor name."""

    @abstractmethod
    async def process(
        self,
        source: str | Path,
    ) -> dict[str, Any]:
        """
        Process one input source and return structured output.

        Implementations should validate input format and raise a clear exception
        when the source cannot be processed.
        """


class AudioProcessor(Processor):
    """Processor that transcribes one MP3 file into text."""

    def __init__(self, model: str = "gpt-4o-transcribe") -> None:
        self._model = model
        self._client = AsyncOpenAI()

    @property
    def name(self) -> str:
        return "OpenAI Audio Processor. Transcribes one MP3 file into text."

    @validate_call
    async def process(
        self,
        source: str | Path,
    ) -> dict[str, Any]:

        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY is not set.")

        if isinstance(source, bytes):
            raise TypeError("AudioProcessor expects a single MP3 file path, not raw bytes.")

        audio_path = Path(source)
        if audio_path.suffix.lower() != ".mp3":
            raise ValueError("AudioProcessor only accepts .mp3 files.")
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        with audio_path.open("rb") as audio_file:
            transcript = await self._client.audio.transcriptions.create(
                model=self._model,
                file=audio_file,
            )

        text = getattr(transcript, "text", None)
        if not text:
            raise ValueError("Transcription completed but no text was returned.")

        return {
            "processor": self.name,
            "modality": "audio",
            "source": str(audio_path),
            "model": self._model,
            "text": text.strip(),
        }


class OCRProcessor(Processor):
    """Processor that extracts text from image/PDF via Azure Document Intelligence."""

    SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"}
    SUPPORTED_PDF_EXTENSIONS = {".pdf"}

    def __init__(self, model: str = "prebuilt-read") -> None:
        self._model = model
        endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
        api_key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_API_KEY")
        if not endpoint:
            raise ValueError("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT is not set.")
        if not api_key:
            raise ValueError("AZURE_DOCUMENT_INTELLIGENCE_API_KEY is not set.")
        self._client = DocumentIntelligenceClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(api_key),
        )

    @property
    def name(self) -> str:
        return "Azure OCR Processor. Extracts text from image and PDF files."

    @staticmethod
    def _detect_modality(path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix in OCRProcessor.SUPPORTED_PDF_EXTENSIONS:
            return "pdf"
        if suffix in OCRProcessor.SUPPORTED_IMAGE_EXTENSIONS:
            return "image"
        raise ValueError("OCRProcessor only accepts image files or .pdf files.")

    @staticmethod
    def _extract_pages(pages: Any) -> list[dict[str, Any]]:
        extracted: list[dict[str, Any]] = []
        for page in pages or []:
            lines = []
            for line in getattr(page, "lines", []) or []:
                lines.append(
                    {
                        "text": getattr(line, "content", ""),
                        "polygon": getattr(line, "polygon", None),
                    }
                )

            words = []
            for word in getattr(page, "words", []) or []:
                words.append(
                    {
                        "text": getattr(word, "content", ""),
                        "confidence": getattr(word, "confidence", None),
                        "polygon": getattr(word, "polygon", None),
                    }
                )

            extracted.append(
                {
                    "page_number": getattr(page, "page_number", None),
                    "width": getattr(page, "width", None),
                    "height": getattr(page, "height", None),
                    "unit": getattr(page, "unit", None),
                    "lines": lines,
                    "words": words,
                }
            )
        return extracted

    @validate_call
    async def process(
        self,
        source: str | Path,
    ) -> dict[str, Any]:
        source_path = Path(source)
        if not source_path.exists():
            raise FileNotFoundError(f"Input file not found: {source_path}")

        modality = self._detect_modality(source_path)

        with source_path.open("rb") as document_file:
            file_bytes = document_file.read()
        base64_source = base64.b64encode(file_bytes).decode("utf-8")

        # Azure SDK/service variants use different call signatures and payload
        # shapes. Try multiple known variants before failing.
        attempts = [
            lambda: self._client.begin_analyze_document(
                model_id=self._model,
                body=file_bytes,
            ),
            lambda: self._client.begin_analyze_document(
                self._model,
                file_bytes,
            ),
            lambda: self._client.begin_analyze_document(
                model_id=self._model,
                analyze_request=file_bytes,
            ),
            lambda: self._client.begin_analyze_document(
                model_id=self._model,
                analyze_request={"base64Source": base64_source},
            ),
            lambda: self._client.begin_analyze_document(
                model_id=self._model,
                analyze_request={"base64_source": base64_source},
            ),
        ]

        poller = None
        last_error: Exception | None = None
        for attempt in attempts:
            try:
                poller = attempt()
                break
            except Exception as exc:
                last_error = exc

        if poller is None:
            raise RuntimeError(
                "Unable to start Azure Document Intelligence analysis with supported request formats."
            ) from last_error

        result = poller.result()

        content = getattr(result, "content", "") or ""
        pages = self._extract_pages(getattr(result, "pages", []) or [])
        paragraphs = [
            {"text": getattr(paragraph, "content", "")}
            for paragraph in (getattr(result, "paragraphs", []) or [])
        ]

        return {
            "processor": self.name,
            "source": str(source_path),
            "modality": modality,
            "model": self._model,
            "text": content.strip(),
            "pages": pages,
            "paragraphs": paragraphs,
        }

