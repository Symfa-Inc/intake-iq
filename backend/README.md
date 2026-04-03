# 🐍 Intake IQ Backend

FastAPI backend for the Intake IQ insurance claim intake assistant.

## 📁 Structure

```
backend/
├── Dockerfile                  # Container configuration
├── src/intake_iq/              # Python package (API code)
│   ├── __init__.py
│   └── main.py                 # FastAPI application
├── data/                       # Sample/synthetic datasets
├── models/                     # Model artifacts
└── pyproject.toml              # Package dependencies
```

## 🚀 Quick Start

```bash
# From project root
uv sync                     # Install dependencies

# Run the API
uv run uvicorn intake_iq.main:app --reload --port 8000
```

- API: http://localhost:8000
- Docs: http://localhost:8000/docs

## 🐳 Docker

```bash
# From backend/ directory
docker build -t intake-iq-backend .
docker run -p 8000:8000 intake-iq-backend
```

## 📦 Package Management

```bash
# Add a dependency
uv add <package> --package intake-iq

# Add a dev dependency
uv add <package> --package intake-iq --dev

# Remove a dependency
uv remove <package> --package intake-iq
```

## 🧪 Development

```bash
# Run tests
uv run pytest

# Type checking
uv run mypy src/

# Linting & formatting
uv run ruff check src/
uv run ruff format src/
```

## 🔌 API Endpoints

| Method | Endpoint   | Description       |
|--------|------------|-------------------|
| GET    | `/health`  | Health check      |
