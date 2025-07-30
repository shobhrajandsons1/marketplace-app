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
app = FastAPI()
api_router = APIRouter(prefix="/api")

security = HTTPBearer()

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

# … (ALL OTHER MODELS FROM Emergent’s FILE GO HERE) …
# You pasted BuyerRegistration, PartnerRegistration, ProductMedia, ProductVariant,
# DimensionConfig, SizeConfiguration, BulkPricing, SEOData, MultiSellerListing,
# Review, ProductQuestion, AnalyticsEvent, LoyaltyProgram, Order, Coupon,
# AIContentRequest, AIImageRequest, AISettings, PaymentSettings, NotificationSettings,
# AnalyticsSettings, ShippingSettings, MarketingSettings, SystemSettings,
# CommissionSettings, Wishlist, Cart, etc., and all helper functions:
# hash_password(), verify_password(), create_jwt_token(), verify_jwt_token(),
# get_current_user(), get_optional_user(), get_current_admin_user(), calculate_pricing_tiers(),
# get_user_price(), mock_ai_content_generation(), mock_ai_image_generation(),
# send_verification_email(), notify_admin_for_partner_verification(),
# update_product_rating(), and so on…

# -----------------------------------------------------------------------------
# All Your @api_router.post / @api_router.get Definitions
# -----------------------------------------------------------------------------
# (Buyer & Partner registration, login, email verification, GST verify,
#  admin partner verify, ERP connect/sync, product CRUD & search,
#  review & Q&A routes, wishlist/cart routes, etc.)
#
# … THIS ENTIRE SECTION IS YOUR Emergent CODE, UNTOUCHED …
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# ─── ADD THESE TWO BLOCKS AT THE VERY END ─────────────────────────────────────
# -----------------------------------------------------------------------------
# 1) Enable CORS so your front-end can talk to /api from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # tighten in production to your domain(s)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2) Mount your router under /api
app.include_router(api_router)

# -----------------------------------------------------------------------------
# Optional: run with “python main.py”
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        reload=True
    )
