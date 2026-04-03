from fastapi import FastAPI

app = FastAPI(
    title="Intake IQ",
    description="AI-powered insurance claim intake assistant",
    version="0.1.0",
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
