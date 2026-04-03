<div align="center">

<img src=".assets/logo.png" width="100" alt="Intake IQ Logo">

# Intake IQ

[![Python 3.13](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/downloads/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178c6.svg)](https://www.typescriptlang.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-19-61dafb.svg)](https://react.dev/)
[![Azure](https://img.shields.io/badge/Azure-Document%20Intelligence-0078D4.svg)](https://azure.microsoft.com/en-us/products/ai-services/ai-document-intelligence)
[![OpenAI](https://img.shields.io/badge/OpenAI-Whisper-10a37f.svg)](https://platform.openai.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)

AI-powered insurance claim intake assistant that processes multi-modal submissions — email, PDF, image, and audio — and maps extracted data to standardized FNOL fields.

**[Live Demo](https://intake-iq.symfa.ai)** · **[GitHub](https://github.com/Symfa-Inc/intake-iq)** · **[Confluence](https://symfa.atlassian.net/wiki/x/XgCENgE)**

</div>

## Preview

<p align="center">
<img src=".assets/intake-iq.png" width="80%" alt="Intake IQ Preview">
</p>

## Features

- **Multi-modal Input Processing** – Handles email text, PDF attachments, scanned images, and audio recordings from any intake channel (phone, email, portal)
- **Document Intelligence** – OCR-based extraction from PDFs and images using Azure Document Intelligence
- **Speech-to-Text Transcription** – Audio transcription via OpenAI Whisper for phone-based claim submissions
- **Relevance Filtering** – LLM-powered classification to distinguish valid insurance claims from spam, misdirected emails, and off-topic messages
- **FNOL Data Mapping** – Extracts and maps unstructured claim data to standardized First Notice of Loss fields ready for adjuster review
- **Field Highlighting** – Traces each mapped field back to its source span in the original document or transcript for full auditability

## How It Works

Insurance claim submissions arrive through multiple channels (email, PDF attachments, scanned documents, audio recordings). Each modality is routed to the appropriate processor — Azure Document Intelligence for PDFs and images, OpenAI Whisper for audio. The extracted text is merged, then an LLM classifier filters irrelevant content (spam, wrong-address emails) before the remaining data is mapped to standardized FNOL fields. Each extracted field is linked back to its source position in the original document, giving intake staff a transparent audit trail before the structured record is forwarded to adjusters.

## Tech Stack

| Category | Technologies |
|----------|-------------|
| Backend | Python 3.13, FastAPI, Uvicorn |
| Frontend | TypeScript, Next.js, React, Tailwind CSS |
| AI/ML | Azure Document Intelligence, OpenAI, Whisper |
| Data | Pydantic |
| Package Management | uv (backend), pnpm (frontend) |
| Deployment | Docker, GitHub Actions, Google Artifact Registry |

## Getting Started

### Prerequisites

- Python 3.13+ / [uv](https://docs.astral.sh/uv/)
- Node.js 24+ / [pnpm](https://pnpm.io/)

### Installation & Running

```bash
# Backend
cd backend
cp .env.example .env          # Add your API keys
uv sync
uv run uvicorn intake_iq.main:app --reload

# Frontend
cd frontend
pnpm install
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000) (frontend) and [http://localhost:8000/docs](http://localhost:8000/docs) (API docs).

## License

[MIT](LICENSE)
