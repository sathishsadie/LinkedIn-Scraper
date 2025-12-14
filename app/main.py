"""
main.py - FastAPI Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from contextlib import asynccontextmanager
import os

from api.routes import router

# MongoDB connection settings
MONGODB_HOST = os.getenv("MONGODB_HOST", "localhost")
MONGODB_PORT = int(os.getenv("MONGODB_PORT", "27017"))
DATABASE_NAME = "linkedin_insights"

app_state = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to MongoDB using pymongo
    app_state["db_client"] = MongoClient(MONGODB_HOST, MONGODB_PORT)
    app_state["db"] = app_state["db_client"][DATABASE_NAME]
    print(f"Connected to MongoDB: {MONGODB_HOST}:{MONGODB_PORT}/{DATABASE_NAME}")
    
    # Create indexes
    app_state["db"].pages.create_index("page_id", unique=True)
    app_state["db"].pages.create_index("followers_count")
    app_state["db"].pages.create_index("industry")
    app_state["db"].posts.create_index("page_id")
    app_state["db"].posts.create_index("linkedin_post_id", unique=True)
    app_state["db"].employees.create_index("page_id")
    
    yield
    
    # Shutdown: Close MongoDB connection
    app_state["db_client"].close()
    print("MongoDB connection closed")

app = FastAPI(
    title="LinkedIn Insights Microservice",
    description="Fetch and manage LinkedIn company page insights",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router, prefix="/api/v1", tags=["LinkedIn Insights"])

@app.get("/")
async def root():
    return {
        "message": "LinkedIn Insights Microservice",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

def get_database():
    """Dependency to get database instance"""
    return app_state.get("db")

# Make get_database available to routes
app.state.get_database = get_database

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)