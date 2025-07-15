'''
FastAPI app initialization and configuration
'''

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers
from llmgine.api.routers import events, sessions

app = FastAPI(
    title="LLMGine API",
    description="API server for the LLMGine system",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(events.router)
app.include_router(sessions.router)

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "LLMGine API Server", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "llmgine-api"}
