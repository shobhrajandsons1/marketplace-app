from fastapi import FastAPI, APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import bcrypt
import json
import base64
from enum import Enum
import jwt

# -----------------------------------------------------------------------------
# Load environment
# -----------------------------------------------------------------------------
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017/marketplace')
db_name  = os.environ.get('DB_NAME',    'marketplace')
JWT_SECRET = os.environ.get('JWT_SECRET_KEY', 'your-super-secret-jwt-key-change-in-production')

# -----------------------------------------------------------------------------
# MongoDB client
# -----------------------------------------------------------------------------
if os.environ.get('ENVIRONMENT') == 'production':
    client = AsyncIOMotorClient(
        mongo_url,
        maxPoolSize=50,
        minPoolSize=10,
        maxIdleTimeMS=30000,
        waitQueueTimeoutMS=5000,
        connectTimeoutMS=10000,
        serverSelectionTimeoutMS=10000
    )
else:
    client = AsyncIOMotorClient(mongo_url)

db = client[db_name]

# -----------------------------------------------------------------------------
# App + Router
# -----------------------------------------------------------------------------
app = FastAPI(
    title="Marketplace API",
    description="A comprehensive marketplace API with user registration, product management, and more",
    version="1.0.0"
)
api_router = APIRouter(prefix="/api")

security = HTTPBearer()

# -----------------------------------------------------------------------------
# CORS Configuration - MUST BE ADDED BEFORE ROUTES
# -----------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # In production, replace with your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# ROOT ROUTE - This fixes the 404 error!
# -----------------------------------------------------------------------------
@app.get("/")
async def root():
    """Root endpoint to confirm the API is running"""
    return {
        "message": "🚀 Marketplace API is running successfully!",
        "status": "healthy",
        "version": "1.0.0",
        "endpoints": {
            "api_docs": "/docs",
            "api_base": "/api",
            "health": "/health"
        },
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Test database connection
        await client.admin.command('ping')
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat()
    }

# -----------------------------------------------------------------------------
# Enums & Pydantic Models
# -----------------------------------------------------------------------------
class UserType(str, Enum):
    END_CUSTOMER    = "end_customer"
    RESELLER        = "reseller"
    WHOLESALER      = "wholesaler"
    BULK_BUYER      = "bulk_buyer"
    PREMIUM_MEMBER  = "premium_member"
    MANUFACTURER    = "manufacturer"
    RETAILER        = "retailer"
    ARTIST          = "artist"
    DROP_SHIPPER    = "drop_shipper"
    WHITE_LABEL     = "white_label"
    SERVICE_PROVIDER= "service_provider"
    SELLER          = "seller"
    ADMIN           = "admin"

class RegistrationType(str, Enum):
    BUYER   = "buyer"
    PARTNER = "partner"

class PartnerType(str, Enum):
    SELLER           = "seller"
    SERVICE_PROVIDER = "service_provider"

class VerificationStatus(str, Enum):
    PENDING  = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"

# -----------------------------------------------------------------------------
# ADD ALL YOUR OTHER PYDANTIC MODELS HERE
# -----------------------------------------------------------------------------
# (BuyerRegistration, PartnerRegistration, ProductMedia, ProductVariant, etc.)
# Copy all your existing models from your original file

# -----------------------------------------------------------------------------
# ADD ALL YOUR HELPER FUNCTIONS HERE
# -----------------------------------------------------------------------------
# (hash_password, verify_password, create_jwt_token, etc.)
# Copy all your existing helper functions from your original file

# -----------------------------------------------------------------------------
# ADD ALL YOUR API ROUTES HERE
# -----------------------------------------------------------------------------
# Copy all your @api_router.post and @api_router.get routes from your original file
# For example:
# @api_router.post("/register/buyer")
# @api_router.post("/register/partner")
# @api_router.post("/login")
# etc.

# -----------------------------------------------------------------------------
# Mount the API router
# -----------------------------------------------------------------------------
app.include_router(api_router)

# -----------------------------------------------------------------------------
# Error handling
# -----------------------------------------------------------------------------
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {
        "error": "Endpoint not found",
        "message": f"The requested endpoint does not exist. Try visiting /docs for API documentation.",
        "available_endpoints": ["/", "/health", "/docs", "/api"]
    }

# -----------------------------------------------------------------------------
# For development - run with "python server.py"
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",  # Fixed: should be "server:app" not "main:app"
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        reload=True
    )
