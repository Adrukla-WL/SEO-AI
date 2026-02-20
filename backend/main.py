"""
Main API Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# from services import sheets, parser, ai_engine

app = FastAPI(title="Magic SEO Studio API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    """Root endpoint to check API status."""
    return {"message": "Magic SEO Studio API is running"}

# Include routers or logic here
