from fastapi import FastAPI, APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
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

# Enhanced user management system with new registration types

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection with production optimizations
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017/marketplace')
db_name = os.environ.get('DB_NAME', 'marketplace')

# Production-optimized MongoDB client
if os.environ.get('ENVIRONMENT') == 'production':
    # Production settings with connection pooling
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
    # Development settings
    client = AsyncIOMotorClient(mongo_url)

db = client[db_name]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security - Production-ready JWT secret
security = HTTPBearer()
JWT_SECRET = os.environ.get('JWT_SECRET_KEY', 'your-super-secret-jwt-key-change-in-production')

# Enums for user types
class UserType(str, Enum):
    # Customer types
    END_CUSTOMER = "end_customer"
    RESELLER = "reseller"
    WHOLESALER = "wholesaler"
    BULK_BUYER = "bulk_buyer"
    PREMIUM_MEMBER = "premium_member"
    
    # Seller types
    MANUFACTURER = "manufacturer"
    RETAILER = "retailer"
    ARTIST = "artist"
    DROP_SHIPPER = "drop_shipper"
    WHITE_LABEL = "white_label"
    SERVICE_PROVIDER = "service_provider"
    
    # New unified types
    SELLER = "seller"  # Unified for manufacturer, retailer, wholesaler
    
    # Admin
    ADMIN = "admin"

class RegistrationType(str, Enum):
    BUYER = "buyer"
    PARTNER = "partner"

class PartnerType(str, Enum):
    SELLER = "seller"
    SERVICE_PROVIDER = "service_provider"

class VerificationStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"

class SizeType(str, Enum):
    STANDARD = "standard"
    CUSTOM = "custom"
    BOTH = "both"

class AIProvider(str, Enum):
    OPENAI = "openai"
    GEMINI = "gemini"

class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURNED = "returned"

# Enhanced User Models
class StatutoryDetails(BaseModel):
    gst_number: Optional[str] = None
    gst_verified: bool = False
    gst_verification_date: Optional[datetime] = None
    pan_number: Optional[str] = None
    business_registration_number: Optional[str] = None
    business_type: Optional[str] = None  # private_limited, llp, partnership, sole_proprietor
    annual_turnover: Optional[float] = None

class BillingAddress(BaseModel):
    company_name: str
    contact_person: str
    address_line_1: str
    address_line_2: Optional[str] = None
    city: str
    state: str
    postal_code: str
    country: str = "India"
    phone: str
    email: str

class ERPIntegration(BaseModel):
    erp_type: str  # tally_prime, busy, sap, zoho, etc.
    integration_enabled: bool = False
    api_credentials: Dict[str, Any] = {}
    last_sync: Optional[datetime] = None
    sync_settings: Dict[str, bool] = {
        "orders": True,
        "invoices": True,
        "inventory": True,
        "customers": False,
        "products": False
    }

class ShippingPartner(BaseModel):
    partner_name: str
    integration_enabled: bool = False
    api_credentials: Dict[str, Any] = {}
    supported_services: List[str] = []

class SocialMediaConnection(BaseModel):
    platform: str
    connected: bool = False
    access_token: Optional[str] = None
    profile_id: Optional[str] = None
    connected_at: Optional[datetime] = None

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    password_hash: str
    user_type: UserType
    registration_type: Optional[RegistrationType] = None
    partner_type: Optional[PartnerType] = None
    
    # Basic Information
    business_name: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    gstin: Optional[str] = None  # Keep for backward compatibility
    
    # Verification
    email_verified: bool = False
    email_verification_token: Optional[str] = None
    verification_status: Optional[Any] = VerificationStatus.PENDING  # Can be enum or dict for backward compatibility
    admin_verified: bool = False
    admin_verified_by: Optional[str] = None
    admin_verified_at: Optional[datetime] = None
    verification_notes: Optional[str] = None
    is_verified: bool = False  # Keep for backward compatibility
    
    # Statutory Details (for partners)
    statutory_details: Optional[StatutoryDetails] = None
    billing_address: Optional[BillingAddress] = None
    address: Optional[Dict] = None  # Keep for backward compatibility
    addresses: List[Dict] = []
    
    # ERP Integration
    erp_integrations: List[ERPIntegration] = []
    
    # Shipping Partners (for sellers)
    shipping_partners: List[ShippingPartner] = []
    
    # Social Media Connections (for sellers)
    social_media_connections: List[SocialMediaConnection] = []
    
    # Service Provider Specific
    portfolio_items: List[Dict] = []  # For service providers
    services_offered: List[Dict] = []  # For service providers
    
    # Performance Metrics
    performance_rating: float = 5.0
    total_ratings: int = 0
    total_sales: float = 0.0
    response_time_hours: float = 24.0
    
    # Loyalty and Status
    loyalty_points: int = 0
    total_orders: int = 0
    is_active: bool = True
    is_featured: bool = False
    commission_rate: Optional[float] = None
    
    # Team Management
    team_members: List[Dict] = []
    roles_assigned: List[str] = []
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None

class UserCreate(BaseModel):
    email: str
    password: str
    user_type: UserType
    business_name: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    gstin: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str  # No user_type needed - auto-detect

class BuyerRegistration(BaseModel):
    email: str
    password: str
    full_name: str
    phone: Optional[str] = None

class PartnerRegistration(BaseModel):
    email: str
    password: str
    partner_type: PartnerType
    business_name: str
    contact_person: str
    phone: str
    business_type: str
    gst_number: Optional[str] = None
    
    # Billing Address
    address_line_1: str
    address_line_2: Optional[str] = None
    city: str
    state: str
    postal_code: str
    country: str = "India"

class ProductMedia(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    media_type: str  # image, video, brochure, manual
    url: str
    filename: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)

class ProductVariant(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sku: str
    variant_name: Optional[str] = None
    variant_attributes: Dict[str, str] = {}  # Dynamic attributes like color: red, size: large
    price_modifier: float = 0.0
    final_price: Optional[float] = None  # New field for final variant price
    media: List[ProductMedia] = []
    inventory_count: int = 0
    weight: Optional[float] = None
    dimensions: Optional[Dict] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Enhanced Size/Variant System with Complex Pricing
class DimensionType(str, Enum):
    FIXED = "fixed"
    VARIABLE = "variable"

class PricingMethod(str, Enum):
    PER_CUBIC_INCH = "per_cubic_inch"
    PER_SQUARE_FOOT = "per_square_foot"
    PER_LINEAR_FOOT = "per_linear_foot"
    FLAT_RATE = "flat_rate"

class DimensionConfig(BaseModel):
    type: DimensionType = DimensionType.FIXED
    value: Optional[float] = None  # For fixed dimensions
    min_value: Optional[float] = None  # For variable dimensions
    max_value: Optional[float] = None  # For variable dimensions
    unit: str = "inches"  # inches, cm, feet, meters

class SizeOption(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    size_name: str
    display_value: str
    length: DimensionConfig = DimensionConfig()
    width: DimensionConfig = DimensionConfig()
    height: DimensionConfig = DimensionConfig()
    pricing_method: PricingMethod = PricingMethod.FLAT_RATE
    base_price: float = 0.0
    price_per_unit: float = 0.0  # For per cubic inch/square foot pricing
    sort_order: int = 0
    is_active: bool = True

class SizeConfiguration(BaseModel):
    size_type: SizeType = SizeType.STANDARD
    standard_sizes: List[Dict] = []  # Changed to Dict to support price field
    custom_sizing_enabled: bool = False
    custom_pricing_method: PricingMethod = PricingMethod.PER_SQUARE_FOOT
    custom_price_per_unit: float = 0.0
    custom_min_dimensions: Dict[str, float] = {"length": 1.0, "width": 1.0, "height": 1.0}
    custom_max_dimensions: Dict[str, float] = {"length": 100.0, "width": 100.0, "height": 100.0}
    dimension_unit: str = "inches"
    
    # Enhanced dimension configuration
    length_type: DimensionType = DimensionType.VARIABLE
    width_type: DimensionType = DimensionType.VARIABLE
    height_type: DimensionType = DimensionType.VARIABLE
    
    # Fixed dimension values
    fixed_length: Optional[float] = None
    fixed_width: Optional[float] = None
    fixed_height: Optional[float] = None
    
    # Dimension options for dropdown selection - enhanced with pricing
    length_options: List[Dict] = []  # [{"value": 12, "price_per_unit": 20}]
    width_options: List[Dict] = []
    height_options: List[Dict] = []

# Keep backward compatibility
class CustomSizing(BaseModel):
    enabled: bool = False
    unit: str = "sqft"  # sqft, cubic_ft, linear_ft, pieces
    base_unit_price: float = 0.0
    min_quantity: float = 1.0
    max_quantity: Optional[float] = None
    thickness_variants: List[Dict] = []  # Different thicknesses with price modifiers
    calculation_formula: str = "area"  # area, volume, linear, custom

class BulkPricing(BaseModel):
    tier_name: str
    min_quantity: int
    max_quantity: Optional[int] = None
    discount_percentage: float = 0.0
    discount_amount: float = 0.0
    user_types: List[str] = []  # Which user types get this pricing

class StandardSizeOption(BaseModel):
    size_name: str
    display_value: str
    sort_order: int = 0

class ShippingDimensions(BaseModel):
    length_cm: Optional[float] = None
    width_cm: Optional[float] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    volumetric_weight: Optional[float] = None

class SEOData(BaseModel):
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    keywords: List[str] = []
    canonical_url: Optional[str] = None
    structured_data: Optional[Dict] = None
    ai_generated: bool = False
    last_optimized: Optional[datetime] = None

class MultiSellerListing(BaseModel):
    seller_id: str
    seller_name: str
    price: float
    inventory_count: int
    condition: str = "new"
    shipping_time_days: int = 3
    seller_rating: float = 5.0
    total_seller_reviews: int = 0
    is_featured: bool = False
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class CategoryFilter(BaseModel):
    filter_name: str
    filter_type: str  # dropdown, checkbox, range, text
    possible_values: List[str] = []
    is_required: bool = False
    created_by_seller: bool = False

class ProductCategory(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    parent_category_id: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    filters: List[CategoryFilter] = []
    commission_rate: float = 5.0
    is_active: bool = True
    created_by_admin: bool = True
    created_by_seller: bool = False
    approval_status: str = "approved"  # pending, approved, rejected
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Product(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    seller_id: str
    title: str
    description: str
    category_id: Optional[str] = None
    category_name: Optional[str] = None  # For display purposes
    subcategory: Optional[str] = None
    brand: Optional[str] = None
    model_number: Optional[str] = None
    
    # Media
    media: List[ProductMedia] = []
    primary_image_url: Optional[str] = None
    
    # Pricing System
    base_price: float
    gst_percentage: float = 18.0
    pricing_tiers: Dict[str, float] = {}
    bulk_pricing: List[BulkPricing] = []
    
    # Multi-seller Support
    is_multi_seller_product: bool = False
    master_product_id: Optional[str] = None
    multi_seller_listings: List[MultiSellerListing] = []
    lowest_price: Optional[float] = None  # Auto-calculated
    
    # Size Configuration
    size_configuration: SizeConfiguration = SizeConfiguration()
    
    # Variants and Inventory
    variants: List[ProductVariant] = []
    has_variants: bool = False
    inventory_count: int = 0
    low_stock_threshold: int = 10
    
    # Shipping
    shipping_dimensions: Optional[ShippingDimensions] = None
    free_shipping: bool = False
    shipping_weight_kg: Optional[float] = None
    
    # Product Details
    specifications: Dict[str, Any] = {}
    custom_fields: Dict[str, str] = {}
    moq: int = 1
    
    # SEO and Marketing
    seo_data: SEOData = SEOData()
    tags: List[str] = []
    
    # Performance Metrics
    average_rating: float = 0.0
    total_reviews: int = 0
    total_sold: int = 0
    view_count: int = 0
    wishlist_count: int = 0
    
    # Status and Visibility
    is_active: bool = True
    is_featured: bool = False
    is_trending: bool = False
    approval_status: str = "pending"  # pending, approved, rejected
    rejection_reason: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    approved_at: Optional[datetime] = None

class BulkProductUpload(BaseModel):
    products: List[Dict[str, Any]]
    upload_format: str = "json"  # json, csv, excel
    validate_only: bool = False

class ProductCreate(BaseModel):
    title: str
    description: str
    category_id: str
    subcategory: Optional[str] = None
    brand: Optional[str] = None
    model_number: Optional[str] = None
    base_price: float
    gst_percentage: float = 18.0
    pricing_tiers: Optional[Dict[str, float]] = {}
    bulk_pricing: Optional[List[BulkPricing]] = []
    size_configuration: Optional[SizeConfiguration] = SizeConfiguration()
    
    # Currency and pricing configuration
    currency: str = "INR"
    base_currency: str = "INR"
    price_inclusive_tax: bool = False
    price_inclusive_shipping: bool = False
    tax_rate: float = 0.0
    shipping_cost: float = 0.0
    
    specifications: Optional[Dict[str, Any]] = {}
    custom_fields: Optional[Dict[str, str]] = {}
    variants: Optional[List[ProductVariant]] = []
    has_variants: bool = False
    inventory_count: int = 0
    moq: int = 1
    shipping_dimensions: Optional[ShippingDimensions] = None
    free_shipping: bool = False
    seo_data: Optional[SEOData] = SEOData()
    tags: Optional[List[str]] = []
    is_multi_seller_product: bool = False
    master_product_id: Optional[str] = None

class Review(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product_id: str
    user_id: str
    order_id: Optional[str] = None
    rating: int = Field(..., ge=1, le=5)
    title: str
    comment: str
    images: List[str] = []
    videos: List[str] = []
    is_verified_purchase: bool = False
    is_featured: bool = False
    helpful_count: int = 0
    unhelpful_count: int = 0
    seller_response: Optional[str] = None
    seller_response_date: Optional[datetime] = None
    sentiment_score: float = 0.0  # AI-analyzed sentiment (-1 to 1)
    sentiment_label: str = "neutral"  # positive, negative, neutral
    moderation_status: str = "approved"  # pending, approved, rejected
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ReviewCreate(BaseModel):
    product_id: str
    rating: int = Field(..., ge=1, le=5)
    title: str
    comment: str
    images: Optional[List[str]] = []
    videos: Optional[List[str]] = []

class ProductQuestion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product_id: str
    user_id: str
    question: str
    answer: Optional[str] = None
    answered_by: Optional[str] = None  # user_id of answerer
    answered_at: Optional[datetime] = None
    is_seller_answer: bool = False
    helpful_count: int = 0
    is_featured: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ProductQuestionCreate(BaseModel):
    product_id: str
    question: str

class AnswerCreate(BaseModel):
    answer: str

class SocialMediaPost(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    product_id: Optional[str] = None
    platform: str  # facebook, instagram, twitter, linkedin, tiktok
    post_type: str  # product_promotion, brand_story, sale_announcement
    content: str
    media_urls: List[str] = []
    hashtags: List[str] = []
    post_id: Optional[str] = None  # ID from social platform
    post_url: Optional[str] = None
    status: str = "draft"  # draft, scheduled, published, failed
    scheduled_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    engagement_stats: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class SocialMediaPostCreate(BaseModel):
    product_id: Optional[str] = None
    platforms: List[str]  # Multiple platforms
    post_type: str
    content: str
    media_urls: Optional[List[str]] = []
    hashtags: Optional[List[str]] = []
    schedule_for: Optional[datetime] = None

class AnalyticsEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    session_id: str
    event_type: str  # page_view, product_view, cart_add, purchase, search
    event_data: Dict[str, Any] = {}
    page_url: Optional[str] = None
    referrer: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    location: Optional[Dict] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class PredictiveAnalytics(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    model_type: str  # demand_forecast, price_optimization, customer_lifetime_value
    product_id: Optional[str] = None
    user_id: Optional[str] = None
    predictions: Dict[str, Any] = {}
    confidence_score: float = 0.0
    model_version: str = "v1.0"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    valid_until: datetime = Field(default_factory=lambda: datetime.utcnow() + timedelta(days=7))

class LoyaltyProgram(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    points_balance: int = 0
    tier: str = "bronze"  # bronze, silver, gold, platinum
    tier_progress: float = 0.0
    lifetime_points_earned: int = 0
    lifetime_points_redeemed: int = 0
    achievements: List[str] = []
    badges: List[str] = []
    referral_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class LoyaltyTransaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    transaction_type: str  # earned, redeemed, expired
    points: int
    description: str
    order_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_verified_purchase: bool = False
    helpful_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ReviewCreate(BaseModel):
    product_id: str
    rating: int = Field(..., ge=1, le=5)
    title: str
    comment: str
    images: Optional[List[str]] = []

class Wishlist(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    product_ids: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Cart(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    items: List[Dict] = []  # [{product_id, quantity, variant_id, price}]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Order(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order_number: str = Field(default_factory=lambda: f"ORD-{str(uuid.uuid4())[:8].upper()}")
    customer_id: str
    items: List[Dict] = []
    subtotal: float
    gst_amount: float
    shipping_cost: float = 0.0
    discount_amount: float = 0.0
    loyalty_points_used: int = 0
    total_amount: float
    status: OrderStatus = OrderStatus.PENDING
    payment_status: str = "pending"
    payment_method: Optional[str] = None
    shipping_address: Dict
    billing_address: Dict
    tracking_number: Optional[str] = None
    estimated_delivery: Optional[datetime] = None
    notes: Optional[str] = None
    order_date: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Coupon(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    code: str
    description: str
    discount_type: str  # percentage, fixed
    discount_value: float
    min_order_amount: float = 0.0
    max_uses: Optional[int] = None
    used_count: int = 0
    valid_from: datetime
    valid_until: datetime
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AIContentRequest(BaseModel):
    product_title: str
    category: str
    key_features: List[str] = []
    target_audience: Optional[str] = None
    brand_voice: Optional[str] = "professional"

class AIImageRequest(BaseModel):
    product_name: str
    description: str
    style: Optional[str] = "product photography"
    provider: AIProvider = AIProvider.OPENAI

class AISettings(BaseModel):
    id: str = Field(default="ai_settings")
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    default_text_model: str = "gpt-4.1"
    default_image_provider: AIProvider = AIProvider.OPENAI
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class PaymentSettings(BaseModel):
    id: str = Field(default="payment_settings")
    # International Payment Gateways
    stripe_publishable_key: Optional[str] = None
    stripe_secret_key: Optional[str] = None
    paypal_client_id: Optional[str] = None
    paypal_client_secret: Optional[str] = None
    
    # Indian Payment Gateways
    razorpay_key_id: Optional[str] = None
    razorpay_key_secret: Optional[str] = None
    payu_merchant_key: Optional[str] = None
    payu_salt: Optional[str] = None
    paytm_merchant_id: Optional[str] = None
    paytm_merchant_key: Optional[str] = None
    ccavenue_merchant_id: Optional[str] = None
    ccavenue_working_key: Optional[str] = None
    ccavenue_access_code: Optional[str] = None
    instamojo_api_key: Optional[str] = None
    instamojo_auth_token: Optional[str] = None
    cashfree_app_id: Optional[str] = None
    cashfree_secret_key: Optional[str] = None
    phonepe_merchant_id: Optional[str] = None
    phonepe_salt_key: Optional[str] = None
    
    # Settings
    default_currency: str = "INR"
    test_mode: bool = True
    min_order_amount: float = 100.0
    transaction_fee_percent: float = 2.5
    cod_enabled: bool = True
    auto_refunds_enabled: bool = False
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class NotificationSettings(BaseModel):
    id: str = Field(default="notification_settings")
    sendgrid_api_key: Optional[str] = None
    sendgrid_from_email: Optional[str] = None
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_phone_number: Optional[str] = None
    email_notifications_enabled: bool = True
    sms_notifications_enabled: bool = False
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class AnalyticsSettings(BaseModel):
    id: str = Field(default="analytics_settings")
    google_analytics_id: Optional[str] = None
    facebook_pixel_id: Optional[str] = None
    hotjar_site_id: Optional[str] = None
    mixpanel_token: Optional[str] = None
    tracking_enabled: bool = True
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ShippingSettings(BaseModel):
    id: str = Field(default="shipping_settings")
    # Indian Shipping Partners
    shiprocket_email: Optional[str] = None
    shiprocket_password: Optional[str] = None
    delhivery_token: Optional[str] = None
    delhivery_center_code: Optional[str] = None
    delhivery_cod_enabled: bool = True
    bluedart_api_key: Optional[str] = None
    bluedart_login_id: Optional[str] = None
    bluedart_password: Optional[str] = None
    dtdc_customer_code: Optional[str] = None
    dtdc_api_key: Optional[str] = None
    
    # Shipping Rates
    local_shipping_rate: float = 40.0
    regional_shipping_rate: float = 60.0
    national_shipping_rate: float = 100.0
    free_shipping_threshold: float = 500.0
    default_shipping_cost: float = 50.0
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class MarketingSettings(BaseModel):
    id: str = Field(default="marketing_settings")
    # Email Marketing
    sendgrid_api_key: Optional[str] = None
    sendgrid_from_email: Optional[str] = None
    sendgrid_from_name: Optional[str] = None
    
    # SMS Marketing
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_phone_number: Optional[str] = None
    
    # Social Media Marketing
    google_ads_customer_id: Optional[str] = None
    google_ads_api_key: Optional[str] = None
    facebook_app_id: Optional[str] = None
    facebook_app_secret: Optional[str] = None
    facebook_access_token: Optional[str] = None
    
    # Campaign Settings
    welcome_discount_percent: float = 10.0
    referral_bonus_amount: float = 100.0
    auto_email_campaigns_enabled: bool = True
    loyalty_program_enabled: bool = True
    loyalty_points_per_rupee: float = 1.0
    referral_bonus_points: int = 100
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class SystemSettings(BaseModel):
    id: str = Field(default="system_settings")
    site_name: str = "MarketPlace Pro"
    site_description: str = "World's Most Advanced Marketplace"
    admin_email: Optional[str] = None
    support_email: Optional[str] = None
    company_phone: Optional[str] = None
    company_address: Optional[str] = None
    tax_rate: float = 18.0
    platform_commission_rate: float = 5.0
    maintenance_mode: bool = False
    cache_enabled: bool = True
    two_factor_auth_enabled: bool = True
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class CommissionSettings(BaseModel):
    id: str = Field(default="commission_settings")
    # Default commission rates
    default_commission_rate: float = 5.0
    
    # Category-wise commission rates
    electronics_commission: float = 3.5
    fashion_commission: float = 7.0
    home_garden_commission: float = 4.5
    sports_commission: float = 5.0
    books_commission: float = 8.0
    beauty_commission: float = 6.0
    
    # Vendor tier-based commission rates
    bronze_tier_commission: float = 8.0  # Monthly sales < 100,000 INR
    silver_tier_commission: float = 6.0  # 100,000 - 500,000 INR
    gold_tier_commission: float = 4.0    # 500,000 - 2,000,000 INR
    platinum_tier_commission: float = 2.5 # > 2,000,000 INR
    
    # Tier thresholds (monthly sales in INR)
    bronze_threshold: float = 100000.0
    silver_threshold: float = 500000.0
    gold_threshold: float = 2000000.0
    
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# Helper functions
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_jwt_token(user_id: str, user_type: str) -> str:
    payload = {
        "user_id": user_id,
        "user_type": user_type,
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def verify_jwt_token(token: str) -> Dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = verify_jwt_token(token)
    user = await db.users.find_one({"id": payload["user_id"]})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return User(**user)

async def get_optional_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        if not credentials:
            return None
        token = credentials.credentials
        payload = verify_jwt_token(token)
        user = await db.users.find_one({"id": payload["user_id"]})
        if user:
            return User(**user)
    except:
        pass
    return None

async def get_current_admin_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user and verify admin access"""
    token = credentials.credentials
    payload = verify_jwt_token(token)
    user = await db.users.find_one({"id": payload["user_id"]})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.get("user_type") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return user

def calculate_pricing_tiers(base_price: float) -> Dict[str, float]:
    """Calculate dynamic pricing based on user types"""
    return {
        "end_customer": base_price,
        "reseller": base_price * 0.85,  # 15% discount
        "wholesaler": base_price * 0.75,  # 25% discount
        "bulk_buyer": base_price * 0.70,  # 30% discount
        "premium_member": base_price * 0.90  # 10% discount
    }

def get_user_price(product: Product, user_type: str = "end_customer") -> float:
    """Get price for specific user type"""
    if user_type in product.pricing_tiers:
        return product.pricing_tiers[user_type]
    return product.base_price

def mock_ai_content_generation(request: AIContentRequest) -> Dict[str, Any]:
    """Mock AI content generation - will be replaced with real AI when API keys are provided"""
    return {
        "description": f"Premium {request.product_title} designed for {request.target_audience or 'discerning customers'}. "
                      f"This exceptional {request.category.lower()} combines quality, durability, and style. "
                      f"Perfect for both personal and professional use. Key features include: "
                      f"{', '.join(request.key_features) if request.key_features else 'superior quality and design'}.",
        "seo_tags": [request.product_title.lower(), request.category.lower(), "premium", "quality", "durable"],
        "social_media_posts": {
            "facebook": f"🌟 Introducing our amazing {request.product_title}! Perfect for your {request.category.lower()} needs. #Premium #Quality",
            "instagram": f"✨ {request.product_title} ✨\nElevate your {request.category.lower()} game!\n#Premium #Style #Quality",
            "twitter": f"New arrival: {request.product_title} - Where quality meets style! 🚀 #{request.category}"
        }
    }

def mock_ai_image_generation(request: AIImageRequest) -> str:
    """Mock AI image generation - returns a placeholder base64 image"""
    placeholder_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    return placeholder_image

# Enhanced Authentication Routes
@api_router.post("/auth/register/buyer")
async def register_buyer(buyer_data: BuyerRegistration):
    """Register a new buyer"""
    existing_user = await db.users.find_one({"email": buyer_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create buyer user
    hashed_password = hash_password(buyer_data.password)
    user = User(
        email=buyer_data.email,
        password_hash=hashed_password,
        user_type=UserType.END_CUSTOMER,
        registration_type=RegistrationType.BUYER,
        contact_person=buyer_data.full_name,
        phone=buyer_data.phone,
        email_verification_token=str(uuid.uuid4()),
        verification_status=VerificationStatus.PENDING
    )
    
    await db.users.insert_one(user.dict())
    
    # Send verification email (mock)
    await send_verification_email(buyer_data.email, user.email_verification_token)
    
    return {"message": "Buyer registered successfully. Please verify your email.", "user_id": user.id}

@api_router.post("/auth/register/partner")
async def register_partner(partner_data: PartnerRegistration):
    """Register a new partner (seller/service provider)"""
    existing_user = await db.users.find_one({"email": partner_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create partner user
    hashed_password = hash_password(partner_data.password)
    
    # Create statutory details
    statutory_details = StatutoryDetails(
        gst_number=partner_data.gst_number,
        business_type=partner_data.business_type
    )
    
    # Create billing address
    billing_address = BillingAddress(
        company_name=partner_data.business_name,
        contact_person=partner_data.contact_person,
        address_line_1=partner_data.address_line_1,
        address_line_2=partner_data.address_line_2,
        city=partner_data.city,
        state=partner_data.state,
        postal_code=partner_data.postal_code,
        country=partner_data.country,
        phone=partner_data.phone,
        email=partner_data.email
    )
    
    user = User(
        email=partner_data.email,
        password_hash=hashed_password,
        user_type=UserType.SELLER if partner_data.partner_type == PartnerType.SELLER else UserType.SERVICE_PROVIDER,
        registration_type=RegistrationType.PARTNER,
        partner_type=partner_data.partner_type,
        business_name=partner_data.business_name,
        contact_person=partner_data.contact_person,
        phone=partner_data.phone,
        statutory_details=statutory_details,
        billing_address=billing_address,
        email_verification_token=str(uuid.uuid4()),
        verification_status=VerificationStatus.PENDING
    )
    
    await db.users.insert_one(user.dict())
    
    # Send verification email
    await send_verification_email(partner_data.email, user.email_verification_token)
    
    # Notify admin for partner verification
    await notify_admin_for_partner_verification(user.id, partner_data.business_name)
    
    return {"message": "Partner registered successfully. Please verify your email and wait for admin approval.", "user_id": user.id}

@api_router.post("/auth/verify-email")
async def verify_email(email: str, token: str):
    """Verify email address"""
    user = await db.users.find_one({"email": email, "email_verification_token": token})
    if not user:
        raise HTTPException(status_code=400, detail="Invalid verification token")
    
    await db.users.update_one(
        {"email": email},
        {
            "$set": {
                "email_verified": True,
                "email_verification_token": None,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return {"message": "Email verified successfully"}

@api_router.post("/auth/resend-verification")
async def resend_verification_email(email: str):
    """Resend verification email"""
    user = await db.users.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.get("email_verified"):
        raise HTTPException(status_code=400, detail="Email already verified")
    
    new_token = str(uuid.uuid4())
    await db.users.update_one(
        {"email": email},
        {"$set": {"email_verification_token": new_token}}
    )
    
    await send_verification_email(email, new_token)
    return {"message": "Verification email sent"}

@api_router.post("/auth/login")
async def login(login_data: UserLogin):
    """Enhanced login with auto account type detection"""
    user = await db.users.find_one({"email": login_data.email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not verify_password(login_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not user.get("email_verified", False):
        raise HTTPException(status_code=401, detail="Please verify your email first")
    
    if user.get("registration_type") == "partner" and not user.get("admin_verified", False):
        raise HTTPException(status_code=401, detail="Account pending admin approval")
    
    # Update last login
    await db.users.update_one(
        {"email": login_data.email},
        {"$set": {"last_login": datetime.utcnow()}}
    )
    
    # Create JWT token
    token_data = {
        "user_id": user["id"],
        "email": user["email"],
        "user_type": user["user_type"],
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    
    token = jwt.encode(token_data, JWT_SECRET, algorithm="HS256")
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "user_type": user["user_type"],
            "business_name": user.get("business_name"),
            "contact_person": user.get("contact_person"),
            "verification_status": user.get("verification_status", "pending")
        }
    }

# GST Verification Routes
@api_router.post("/gst/verify")
async def verify_gst_number(gst_number: str, current_user: User = Depends(get_current_user)):
    """Verify GST number from GST portal"""
    # Mock GST verification - in production, integrate with actual GST API
    if len(gst_number) != 15:
        raise HTTPException(status_code=400, detail="Invalid GST number format")
    
    # Mock verification response
    verification_result = {
        "gst_number": gst_number,
        "business_name": "Mock Business Pvt Ltd",
        "status": "Active",
        "registration_date": "2020-01-01",
        "verified": True
    }
    
    # Update user's GST verification status
    await db.users.update_one(
        {"id": current_user.id},
        {
            "$set": {
                "statutory_details.gst_verified": True,
                "statutory_details.gst_verification_date": datetime.utcnow()
            }
        }
    )
    
    return verification_result

# Admin Partner Verification Routes
@api_router.get("/admin/partners/pending")
async def get_pending_partners(current_user: User = Depends(get_current_user)):
    """Get list of partners pending verification"""
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    pending_partners = await db.users.find({
        "registration_type": "partner",
        "verification_status": "pending"
    }).to_list(100)
    
    return {"pending_partners": pending_partners}

@api_router.post("/admin/partners/{partner_id}/verify")
async def verify_partner(
    partner_id: str,
    approved: bool,
    commission_rate: float,
    notes: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Verify/approve a partner"""
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    status = VerificationStatus.VERIFIED if approved else VerificationStatus.REJECTED
    
    await db.users.update_one(
        {"id": partner_id},
        {
            "$set": {
                "verification_status": status,
                "admin_verified": approved,
                "admin_verified_by": current_user.id,
                "admin_verified_at": datetime.utcnow(),
                "commission_rate": commission_rate if approved else None,
                "verification_notes": notes,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return {"message": f"Partner {'approved' if approved else 'rejected'} successfully"}

# ERP Integration Routes
@api_router.post("/erp/connect")
async def connect_erp_system(
    erp_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Connect ERP system to user account"""
    erp_integration = ERPIntegration(
        erp_type=erp_data["erp_type"],
        integration_enabled=True,
        api_credentials=erp_data["api_credentials"],
        sync_settings=erp_data.get("sync_settings", {
            "orders": True,
            "invoices": True,
            "inventory": True,
            "customers": False,
            "products": False
        })
    )
    
    # Update user's ERP integrations
    await db.users.update_one(
        {"id": current_user.id},
        {
            "$push": {"erp_integrations": erp_integration.dict()},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    return {"message": f"{erp_data['erp_type']} integration connected successfully"}

@api_router.post("/erp/sync")
async def sync_erp_data(
    erp_type: str,
    sync_type: str,
    current_user: User = Depends(get_current_user)
):
    """Sync data with ERP system"""
    # Find user's ERP integration
    user = await db.users.find_one({"id": current_user.id})
    erp_integration = None
    
    for integration in user.get("erp_integrations", []):
        if integration["erp_type"] == erp_type:
            erp_integration = integration
            break
    
    if not erp_integration:
        raise HTTPException(status_code=404, detail="ERP integration not found")
    
    # Mock sync process
    sync_result = {
        "erp_type": erp_type,
        "sync_type": sync_type,
        "status": "completed",
        "records_synced": 150,
        "last_sync": datetime.utcnow().isoformat()
    }
    
    # Update last sync time
    await db.users.update_one(
        {"id": current_user.id, "erp_integrations.erp_type": erp_type},
        {"$set": {"erp_integrations.$.last_sync": datetime.utcnow()}}
    )
    
    return sync_result

@api_router.get("/erp/supported-systems")
async def get_supported_erp_systems():
    """Get list of supported ERP systems"""
    erp_systems = [
        {
            "id": "tally_prime",
            "name": "Tally Prime",
            "description": "Complete business management solution",
            "features": ["Inventory", "Accounting", "GST", "Payroll"],
            "integration_type": "API",
            "setup_complexity": "Medium"
        },
        {
            "id": "busy",
            "name": "BUSY Accounting Software",
            "description": "GST ready accounting software",
            "features": ["Accounting", "Inventory", "GST", "Banking"],
            "integration_type": "API",
            "setup_complexity": "Medium"
        },
        {
            "id": "sap",
            "name": "SAP Business One",
            "description": "Enterprise resource planning",
            "features": ["Complete ERP", "CRM", "Analytics", "Reporting"],
            "integration_type": "API",
            "setup_complexity": "High"
        },
        {
            "id": "zoho_books",
            "name": "Zoho Books",
            "description": "Online accounting software",
            "features": ["Accounting", "Invoicing", "Inventory", "Reports"],
            "integration_type": "API",
            "setup_complexity": "Low"
        },
        {
            "id": "quickbooks",
            "name": "QuickBooks Online",
            "description": "Cloud-based accounting",
            "features": ["Accounting", "Invoicing", "Payments", "Reports"],
            "integration_type": "API",
            "setup_complexity": "Low"
        }
    ]
    
    return {"supported_erp_systems": erp_systems}

# Helper functions
async def send_verification_email(email: str, token: str):
    """Send verification email (mock implementation)"""
    # In production, integrate with actual email service
    verification_link = f"https://marketplace.com/verify-email?email={email}&token={token}"
    print(f"Verification email sent to {email}: {verification_link}")

async def notify_admin_for_partner_verification(user_id: str, business_name: str):
    """Notify admin about new partner registration"""
    # In production, send notification to admin
    print(f"Admin notification: New partner '{business_name}' registered with ID: {user_id}")

# Product Routes
@api_router.post("/products")
async def create_product(product_data: ProductCreate, current_user: User = Depends(get_current_user)):
    # Updated seller types - support both old and new types for backward compatibility
    seller_types = [UserType.MANUFACTURER, UserType.RETAILER, UserType.ARTIST, 
                   UserType.DROP_SHIPPER, UserType.WHITE_LABEL, UserType.SERVICE_PROVIDER,
                   UserType.SELLER]  # New unified seller type
    
    if current_user.user_type not in seller_types and current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Only sellers can create products")
    
    product_dict = product_data.dict()
    product_dict["seller_id"] = current_user.id
    
    if not product_dict["pricing_tiers"]:
        product_dict["pricing_tiers"] = calculate_pricing_tiers(product_data.base_price)
    
    product = Product(**product_dict)
    await db.products.insert_one(product.dict())
    
    return {"message": "Product created successfully", "product_id": product.id}

@api_router.get("/products")
async def get_products(
    # Basic Filters
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    seller_id: Optional[str] = None,
    brand: Optional[str] = None,
    
    # Price Filters
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    
    # Rating and Review Filters
    min_rating: Optional[float] = None,
    min_reviews: Optional[int] = None,
    
    # Availability Filters
    in_stock: Optional[bool] = None,
    has_variants: Optional[bool] = None,
    
    # Feature Filters
    is_featured: Optional[bool] = None,
    is_trending: Optional[bool] = None,
    custom_sizing: Optional[bool] = None,
    
    # Search Query
    search: Optional[str] = None,
    
    # Advanced Filters
    location: Optional[str] = None,
    gst_available: Optional[bool] = None,
    moq_max: Optional[int] = None,
    
    # Sorting Options
    sort_by: Optional[str] = "created_at",  # created_at, price_low, price_high, rating, popularity, relevance
    
    # Pagination
    limit: int = 20,
    skip: int = 0
):
    query = {"is_active": True}
    
    # Basic filters
    if category:
        query["category"] = category
    if subcategory:
        query["subcategory"] = subcategory
    if seller_id:
        query["seller_id"] = seller_id
    if brand:
        query["brand"] = {"$regex": brand, "$options": "i"}
    
    # Price filters
    if min_price is not None:
        query["base_price"] = {"$gte": min_price}
    if max_price is not None:
        if "base_price" in query:
            query["base_price"]["$lte"] = max_price
        else:
            query["base_price"] = {"$lte": max_price}
    
    # Rating and review filters
    if min_rating is not None:
        query["average_rating"] = {"$gte": min_rating}
    if min_reviews is not None:
        query["total_reviews"] = {"$gte": min_reviews}
    
    # Availability filters
    if in_stock is not None:
        if in_stock:
            query["inventory_count"] = {"$gt": 0}
        else:
            query["inventory_count"] = {"$eq": 0}
    
    if has_variants is not None:
        query["has_variants"] = has_variants
    
    # Feature filters
    if is_featured is not None:
        query["is_featured"] = is_featured
    if is_trending is not None:
        query["is_trending"] = is_trending
    if custom_sizing is not None:
        query["custom_sizing.enabled"] = custom_sizing
    
    # Advanced filters
    if gst_available is not None:
        if gst_available:
            query["gst_percentage"] = {"$gt": 0}
        else:
            query["gst_percentage"] = {"$eq": 0}
    
    if moq_max is not None:
        query["moq"] = {"$lte": moq_max}
    
    # Search functionality
    if search:
        search_regex = {"$regex": search, "$options": "i"}
        query["$or"] = [
            {"title": search_regex},
            {"description": search_regex},
            {"brand": search_regex},
            {"category": search_regex},
            {"seo_tags": {"$in": [search_regex]}},
            {"meta_keywords": {"$in": [search_regex]}}
        ]
    
    # Sorting
    sort_options = {
        "created_at": [("created_at", -1)],
        "price_low": [("base_price", 1)],
        "price_high": [("base_price", -1)],
        "rating": [("average_rating", -1)],
        "popularity": [("total_sold", -1)],
        "relevance": [("view_count", -1), ("total_sold", -1)],
        "trending": [("is_trending", -1), ("social_shares", -1)]
    }
    sort_criteria = sort_options.get(sort_by, [("created_at", -1)])
    
    products = await db.products.find(query).sort(sort_criteria).skip(skip).limit(limit).to_list(limit)
    total_count = await db.products.count_documents(query)
    
    return {
        "products": [Product(**product) for product in products],
        "total_count": total_count,
        "current_page": skip // limit + 1,
        "total_pages": (total_count + limit - 1) // limit,
        "has_next": skip + limit < total_count,
        "has_previous": skip > 0
    }

@api_router.get("/products/search/suggestions")
async def get_search_suggestions(q: str):
    """Get search suggestions for autocomplete"""
    if len(q) < 2:
        return {"suggestions": []}
    
    search_regex = {"$regex": q, "$options": "i"}
    
    # Get suggestions from products
    pipeline = [
        {"$match": {"is_active": True, "title": search_regex}},
        {"$group": {"_id": "$title", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]
    
    title_suggestions = await db.products.aggregate(pipeline).to_list(5)
    
    # Get brand suggestions
    brand_pipeline = [
        {"$match": {"is_active": True, "brand": search_regex}},
        {"$group": {"_id": "$brand", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 3}
    ]
    
    brand_suggestions = await db.products.aggregate(brand_pipeline).to_list(3)
    
    # Get category suggestions
    category_pipeline = [
        {"$match": {"is_active": True, "category": search_regex}},
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 3}
    ]
    
    category_suggestions = await db.products.aggregate(category_pipeline).to_list(3)
    
    suggestions = []
    
    # Add title suggestions
    for item in title_suggestions:
        suggestions.append({
            "text": item["_id"],
            "type": "product",
            "count": item["count"]
        })
    
    # Add brand suggestions
    for item in brand_suggestions:
        suggestions.append({
            "text": item["_id"],
            "type": "brand",
            "count": item["count"]
        })
    
    # Add category suggestions
    for item in category_suggestions:
        suggestions.append({
            "text": item["_id"],
            "type": "category",
            "count": item["count"]
        })
    
    return {"suggestions": suggestions[:10]}

@api_router.get("/products/{product_id}")
async def get_product(product_id: str):
    product = await db.products.find_one({"id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return Product(**product)

@api_router.get("/products/categories/list")
async def get_categories():
    """Get all unique categories"""
    categories = await db.products.distinct("category", {"is_active": True})
    return {"categories": categories}

@api_router.get("/products/brands/list")
async def get_brands():
    """Get all unique brands"""
    brands = await db.products.distinct("brand", {"is_active": True, "brand": {"$ne": None}})
    return {"brands": brands}

# Review Routes
@api_router.post("/reviews")
async def create_review(review_data: ReviewCreate, current_user: User = Depends(get_current_user)):
    # Check if user has purchased this product
    order = await db.orders.find_one({
        "customer_id": current_user.id,
        "items.product_id": review_data.product_id,
        "status": {"$in": ["delivered", "completed"]}
    })
    
    review_dict = review_data.dict()
    review_dict["user_id"] = current_user.id
    review_dict["is_verified_purchase"] = bool(order)
    if order:
        review_dict["order_id"] = order["id"]
    
    review = Review(**review_dict)
    await db.reviews.insert_one(review.dict())
    
    # Update product rating
    await update_product_rating(review_data.product_id)
    
    return {"message": "Review created successfully", "review_id": review.id}

@api_router.get("/reviews/product/{product_id}")
async def get_product_reviews(
    product_id: str,
    rating_filter: Optional[int] = None,
    verified_only: bool = False,
    limit: int = 10,
    skip: int = 0
):
    query = {"product_id": product_id}
    
    if rating_filter:
        query["rating"] = rating_filter
    if verified_only:
        query["is_verified_purchase"] = True
    
    reviews = await db.reviews.find(query).sort([("created_at", -1)]).skip(skip).limit(limit).to_list(limit)
    
    # Get user info for each review
    for review in reviews:
        user = await db.users.find_one({"id": review["user_id"]})
        if user:
            review["user_name"] = user.get("contact_person") or user["email"].split("@")[0]
        else:
            review["user_name"] = "Anonymous"
    
    return reviews

async def update_product_rating(product_id: str):
    """Update product's average rating and review count"""
    pipeline = [
        {"$match": {"product_id": product_id}},
        {"$group": {
            "_id": None,
            "average_rating": {"$avg": "$rating"},
            "total_reviews": {"$sum": 1}
        }}
    ]
    
    result = await db.reviews.aggregate(pipeline).to_list(1)
    if result:
        await db.products.update_one(
            {"id": product_id},
            {"$set": {
                "average_rating": round(result[0]["average_rating"], 2),
                "total_reviews": result[0]["total_reviews"]
            }}
        )

# Enhanced Review Routes
@api_router.post("/reviews/{review_id}/helpful")
async def mark_review_helpful(review_id: str, helpful: bool, current_user: User = Depends(get_current_user)):
    """Mark a review as helpful or unhelpful"""
    field = "helpful_count" if helpful else "unhelpful_count"
    await db.reviews.update_one(
        {"id": review_id},
        {"$inc": {field: 1}}
    )
    return {"message": f"Review marked as {'helpful' if helpful else 'unhelpful'}"}

@api_router.post("/reviews/{review_id}/seller-response")
async def add_seller_response(review_id: str, response: str, current_user: User = Depends(get_current_user)):
    """Add seller response to a review"""
    # Verify user is seller of the product
    review = await db.reviews.find_one({"id": review_id})
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    product = await db.products.find_one({"id": review["product_id"]})
    if not product or product["seller_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Only the seller can respond to reviews")
    
    await db.reviews.update_one(
        {"id": review_id},
        {
            "$set": {
                "seller_response": response,
                "seller_response_date": datetime.utcnow()
            }
        }
    )
    return {"message": "Seller response added successfully"}

@api_router.get("/reviews/analytics/{product_id}")
async def get_review_analytics(product_id: str, current_user: User = Depends(get_current_user)):
    """Get detailed review analytics for a product"""
    # Verify user is seller of the product
    product = await db.products.find_one({"id": product_id})
    if not product or product["seller_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    pipeline = [
        {"$match": {"product_id": product_id}},
        {"$facet": {
            "rating_distribution": [
                {"$group": {"_id": "$rating", "count": {"$sum": 1}}},
                {"$sort": {"_id": 1}}
            ],
            "sentiment_analysis": [
                {"$group": {
                    "_id": "$sentiment_label",
                    "count": {"$sum": 1},
                    "avg_sentiment": {"$avg": "$sentiment_score"}
                }}
            ],
            "monthly_reviews": [
                {"$group": {
                    "_id": {
                        "year": {"$year": "$created_at"},
                        "month": {"$month": "$created_at"}
                    },
                    "count": {"$sum": 1},
                    "avg_rating": {"$avg": "$rating"}
                }},
                {"$sort": {"_id.year": -1, "_id.month": -1}},
                {"$limit": 12}
            ]
        }}
    ]
    
    result = await db.reviews.aggregate(pipeline).to_list(1)
    return result[0] if result else {}

# Product Q&A Routes
@api_router.post("/products/questions")
async def create_question(question_data: ProductQuestionCreate, current_user: User = Depends(get_current_user)):
    """Create a new product question"""
    question_dict = question_data.dict()
    question_dict["user_id"] = current_user.id
    
    question = ProductQuestion(**question_dict)
    await db.product_questions.insert_one(question.dict())
    
    return {"message": "Question submitted successfully", "question_id": question.id}

@api_router.get("/products/{product_id}/questions")
async def get_product_questions(
    product_id: str,
    answered_only: bool = False,
    limit: int = 10,
    skip: int = 0
):
    """Get questions for a product"""
    query = {"product_id": product_id}
    
    if answered_only:
        query["answer"] = {"$ne": None}
    
    questions = await db.product_questions.find(query).sort([("created_at", -1)]).skip(skip).limit(limit).to_list(limit)
    
    # Get user info for each question
    for question in questions:
        user = await db.users.find_one({"id": question["user_id"]})
        if user:
            question["user_name"] = user.get("contact_person") or user["email"].split("@")[0]
        else:
            question["user_name"] = "Anonymous"
        
        # Get answerer info if available
        if question.get("answered_by"):
            answerer = await db.users.find_one({"id": question["answered_by"]})
            if answerer:
                question["answerer_name"] = answerer.get("contact_person") or answerer["email"].split("@")[0]
    
    return questions

@api_router.post("/questions/{question_id}/answer")
async def answer_question(question_id: str, answer_data: AnswerCreate, current_user: User = Depends(get_current_user)):
    """Answer a product question"""
    question = await db.product_questions.find_one({"id": question_id})
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Check if user is seller of the product
    product = await db.products.find_one({"id": question["product_id"]})
    is_seller = product and product["seller_id"] == current_user.id
    
    await db.product_questions.update_one(
        {"id": question_id},
        {
            "$set": {
                "answer": answer_data.answer,
                "answered_by": current_user.id,
                "answered_at": datetime.utcnow(),
                "is_seller_answer": is_seller
            }
        }
    )
    
    return {"message": "Answer submitted successfully"}

@api_router.post("/questions/{question_id}/helpful")
async def mark_question_helpful(question_id: str, current_user: User = Depends(get_current_user)):
    """Mark a question as helpful"""
    await db.product_questions.update_one(
        {"id": question_id},
        {"$inc": {"helpful_count": 1}}
    )
    return {"message": "Question marked as helpful"}

# Wishlist Routes
@api_router.post("/wishlist/add/{product_id}")
async def add_to_wishlist(product_id: str, current_user: User = Depends(get_current_user)):
    # Check if product exists
    product = await db.products.find_one({"id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get or create wishlist
    wishlist = await db.wishlists.find_one({"user_id": current_user.id})
    if not wishlist:
        wishlist = Wishlist(user_id=current_user.id, product_ids=[product_id])
        await db.wishlists.insert_one(wishlist.dict())
    else:
        if product_id not in wishlist["product_ids"]:
            await db.wishlists.update_one(
                {"user_id": current_user.id},
                {"$addToSet": {"product_ids": product_id}, "$set": {"updated_at": datetime.utcnow()}}
            )
    
    return {"message": "Product added to wishlist"}

@api_router.delete("/wishlist/remove/{product_id}")
async def remove_from_wishlist(product_id: str, current_user: User = Depends(get_current_user)):
    await db.wishlists.update_one(
        {"user_id": current_user.id},
        {"$pull": {"product_ids": product_id}, "$set": {"updated_at": datetime.utcnow()}}
    )
    return {"message": "Product removed from wish"<response clipped>}<NOTE>To save on context only part of this file has been shown to you. You should retry this tool after you have searched inside the file with `grep -n` in order to find the line numbers of what you are looking for.</NOTE>
    
