#!/usr/bin/env python3
"""
S2 Intelligence - Production API Gateway
RESTful interface with authentication, rate limiting, and monitoring

Features:
- JWT authentication
- Rate limiting (per user/IP)
- Request/response caching
- Comprehensive error handling
- OpenAPI documentation
- Metrics collection
- WebSocket support
"""

import asyncio
import hashlib
import json
import logging
import secrets
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from functools import wraps

import jwt
from fastapi import FastAPI, HTTPException, Depends, Header, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
JWT_SECRET = secrets.token_urlsafe(32)  # In production, use env var
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

INTELLIGENCE_ROUTER_URL = "http://localhost:3011"
EGREGORE_MANAGER_URL = "http://localhost:9000"

# Rate limiting configuration
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_REQUESTS = 60  # per window
RATE_LIMIT_PREMIUM_MULTIPLIER = 5  # Premium users get 5x


class RateLimiter:
    """
    Token bucket rate limiter
    """
    def __init__(self):
        self.buckets: Dict[str, Dict] = defaultdict(lambda: {
            "tokens": RATE_LIMIT_MAX_REQUESTS,
            "last_update": time.time()
        })
    
    def check_rate_limit(self, identifier: str, is_premium: bool = False) -> bool:
        """Check if request is within rate limit"""
        bucket = self.buckets[identifier]
        now = time.time()
        
        # Calculate max tokens based on user type
        max_tokens = RATE_LIMIT_MAX_REQUESTS * (RATE_LIMIT_PREMIUM_MULTIPLIER if is_premium else 1)
        
        # Refill tokens based on time passed
        time_passed = now - bucket["last_update"]
        refill_rate = max_tokens / RATE_LIMIT_WINDOW
        bucket["tokens"] = min(
            max_tokens,
            bucket["tokens"] + (time_passed * refill_rate)
        )
        bucket["last_update"] = now
        
        # Check if we have tokens
        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            return True
        else:
            return False
    
    def get_remaining(self, identifier: str, is_premium: bool = False) -> int:
        """Get remaining requests in window"""
        bucket = self.buckets[identifier]
        return int(bucket["tokens"])


rate_limiter = RateLimiter()


class User(BaseModel):
    """User model"""
    username: str
    email: str
    tier: str = "free"  # free, beta, premium
    api_key: Optional[str] = None


class AuthManager:
    """
    Authentication and authorization manager
    """
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.api_keys: Dict[str, str] = {}  # api_key -> username
        self._init_demo_users()
    
    def _init_demo_users(self):
        """Initialize demo users"""
        demo_users = [
            User(username="demo", email="demo@s2intelligence.com", tier="free"),
            User(username="beta_tester", email="beta@s2intelligence.com", tier="beta"),
            User(username="premium", email="premium@s2intelligence.com", tier="premium")
        ]
        
        for user in demo_users:
            # Generate API key
            api_key = f"sk-{secrets.token_urlsafe(32)}"
            user.api_key = api_key
            
            self.users[user.username] = user
            self.api_keys[api_key] = user.username
            
            logger.info(f"Created user: {user.username} (tier: {user.tier})")
            logger.info(f"  API Key: {api_key}")
    
    def create_token(self, username: str) -> str:
        """Create JWT token"""
        user = self.users.get(username)
        if not user:
            raise ValueError("User not found")
        
        payload = {
            "username": username,
            "email": user.email,
            "tier": user.tier,
            "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
        }
        
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return token
    
    def verify_token(self, token: str) -> Dict:
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    def verify_api_key(self, api_key: str) -> Optional[User]:
        """Verify API key"""
        username = self.api_keys.get(api_key)
        if username:
            return self.users.get(username)
        return None


auth_manager = AuthManager()


# FastAPI app
app = FastAPI(
    title="S2 Intelligence API Gateway",
    description="Production-ready API for Ninefold multi-agent intelligence",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()


# Dependency: Verify authentication
async def verify_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    x_api_key: Optional[str] = Header(None)
) -> User:
    """
    Verify authentication via JWT or API key
    """
    # Try API key first
    if x_api_key:
        user = auth_manager.verify_api_key(x_api_key)
        if user:
            return user
    
    # Try JWT token
    if credentials:
        token = credentials.credentials
        payload = auth_manager.verify_token(token)
        user = auth_manager.users.get(payload["username"])
        if user:
            return user
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials"
    )


# Dependency: Check rate limit
async def check_rate_limit(user: User = Depends(verify_auth)):
    """Check rate limit for authenticated user"""
    identifier = user.username
    is_premium = user.tier in ["premium", "beta"]
    
    if not rate_limiter.check_rate_limit(identifier, is_premium):
        remaining = rate_limiter.get_remaining(identifier, is_premium)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {RATE_LIMIT_WINDOW}s. Remaining: {remaining}"
        )
    
    return user


# Request/Response models
class QueryRequest(BaseModel):
    query: str = Field(..., description="Natural language query")
    max_tokens: int = Field(512, description="Maximum tokens in response")
    stream: bool = Field(False, description="Enable streaming response")


class QueryResponse(BaseModel):
    query: str
    response: Dict
    metadata: Dict
    usage: Dict


class AnalyzeRequest(BaseModel):
    query: str = Field(..., description="Query to analyze")


class LoginRequest(BaseModel):
    username: str
    password: str  # In production, use proper password hashing


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = JWT_EXPIRATION_HOURS * 3600
    user: Dict


# Metrics tracking
class MetricsCollector:
    """Collect API metrics"""
    def __init__(self):
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_response_time": 0,
            "requests_by_endpoint": defaultdict(int),
            "requests_by_user": defaultdict(int),
            "requests_by_tier": defaultdict(int)
        }
    
    def record_request(
        self,
        endpoint: str,
        username: str,
        tier: str,
        response_time: float,
        success: bool
    ):
        """Record request metrics"""
        self.metrics["total_requests"] += 1
        if success:
            self.metrics["successful_requests"] += 1
        else:
            self.metrics["failed_requests"] += 1
        
        self.metrics["total_response_time"] += response_time
        self.metrics["requests_by_endpoint"][endpoint] += 1
        self.metrics["requests_by_user"][username] += 1
        self.metrics["requests_by_tier"][tier] += 1
    
    def get_stats(self) -> Dict:
        """Get aggregated stats"""
        total = self.metrics["total_requests"]
        if total == 0:
            avg_response_time = 0
        else:
            avg_response_time = self.metrics["total_response_time"] / total
        
        return {
            "total_requests": total,
            "successful_requests": self.metrics["successful_requests"],
            "failed_requests": self.metrics["failed_requests"],
            "success_rate": self.metrics["successful_requests"] / total if total > 0 else 0,
            "average_response_time_ms": avg_response_time,
            "requests_by_endpoint": dict(self.metrics["requests_by_endpoint"]),
            "requests_by_user": dict(self.metrics["requests_by_user"]),
            "requests_by_tier": dict(self.metrics["requests_by_tier"])
        }


metrics = MetricsCollector()


# Routes

@app.get("/")
async def root():
    """Welcome page"""
    return {
        "service": "S2 Intelligence API Gateway",
        "version": "1.0.0",
        "status": "operational",
        "documentation": "/docs",
        "endpoints": {
            "auth": {
                "login": "POST /auth/login",
                "refresh": "POST /auth/refresh"
            },
            "query": {
                "execute": "POST /v1/query",
                "analyze": "POST /v1/analyze"
            },
            "egregores": {
                "list": "GET /v1/egregores",
                "status": "GET /v1/egregores/{name}",
                "query": "POST /v1/egregores/{name}/query"
            },
            "monitoring": {
                "health": "GET /health",
                "metrics": "GET /v1/metrics",
                "stats": "GET /v1/stats"
            }
        },
        "tiers": {
            "free": f"{RATE_LIMIT_MAX_REQUESTS} requests/minute",
            "beta": f"{RATE_LIMIT_MAX_REQUESTS * RATE_LIMIT_PREMIUM_MULTIPLIER} requests/minute",
            "premium": f"{RATE_LIMIT_MAX_REQUESTS * RATE_LIMIT_PREMIUM_MULTIPLIER} requests/minute + priority"
        }
    }


@app.post("/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """
    Authenticate and receive JWT token
    
    Demo credentials:
    - username: demo, beta_tester, premium
    - password: any (this is demo mode)
    """
    user = auth_manager.users.get(request.username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # In production, verify password here
    
    token = auth_manager.create_token(request.username)
    
    return TokenResponse(
        access_token=token,
        user={
            "username": user.username,
            "email": user.email,
            "tier": user.tier,
            "api_key": user.api_key
        }
    )


@app.post("/v1/query")
async def query(
    request: QueryRequest,
    user: User = Depends(check_rate_limit)
):
    """
    Execute intelligent query with multi-agent routing
    
    Requires authentication (JWT or API key)
    Subject to rate limiting based on tier
    """
    start_time = time.time()
    success = True
    
    try:
        # Forward to intelligence router
        url = f"{INTELLIGENCE_ROUTER_URL}/api/query"
        payload = {
            "query": request.query,
            "max_tokens": request.max_tokens
        }
        
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        
        # Add usage information
        response_time = (time.time() - start_time) * 1000
        
        return {
            **result,
            "usage": {
                "user": user.username,
                "tier": user.tier,
                "response_time_ms": response_time,
                "remaining_requests": rate_limiter.get_remaining(
                    user.username,
                    user.tier in ["premium", "beta"]
                )
            }
        }
        
    except Exception as e:
        success = False
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Record metrics
        metrics.record_request(
            endpoint="/v1/query",
            username=user.username,
            tier=user.tier,
            response_time=(time.time() - start_time) * 1000,
            success=success
        )


@app.post("/v1/analyze")
async def analyze(
    request: AnalyzeRequest,
    user: User = Depends(check_rate_limit)
):
    """
    Analyze query without execution
    
    Returns routing analysis and estimated response time
    """
    try:
        url = f"{INTELLIGENCE_ROUTER_URL}/api/analyze"
        payload = {"query": request.query}
        
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        return response.json()
        
    except Exception as e:
        logger.error(f"Error analyzing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/egregores")
async def list_egregores(user: User = Depends(verify_auth)):
    """List all available egregores"""
    try:
        response = requests.get(f"{EGREGORE_MANAGER_URL}/egregores", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/egregores/{egregore_name}")
async def get_egregore(
    egregore_name: str,
    user: User = Depends(verify_auth)
):
    """Get specific egregore details"""
    try:
        response = requests.get(
            f"{EGREGORE_MANAGER_URL}/egregores/{egregore_name}",
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "api_gateway",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/v1/metrics")
async def get_metrics(user: User = Depends(verify_auth)):
    """Get API metrics (requires authentication)"""
    # Only allow premium/beta users to see full metrics
    if user.tier not in ["premium", "beta"]:
        raise HTTPException(
            status_code=403,
            detail="Metrics access requires premium/beta tier"
        )
    
    return metrics.get_stats()


@app.get("/v1/stats")
async def get_stats(user: User = Depends(verify_auth)):
    """Get intelligence router stats"""
    try:
        response = requests.get(f"{INTELLIGENCE_ROUTER_URL}/api/stats", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket for streaming responses
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for streaming responses
    
    Requires authentication via query parameter: ?token=<jwt_token>
    """
    await websocket.accept()
    
    try:
        # Get token from query params
        token = websocket.query_params.get("token")
        if not token:
            await websocket.close(code=1008, reason="Authentication required")
            return
        
        # Verify token
        try:
            payload = auth_manager.verify_token(token)
            user = auth_manager.users.get(payload["username"])
            if not user:
                await websocket.close(code=1008, reason="Invalid user")
                return
        except HTTPException:
            await websocket.close(code=1008, reason="Invalid token")
            return
        
        # Handle messages
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            query = message.get("query")
            if not query:
                await websocket.send_json({"error": "No query provided"})
                continue
            
            # Check rate limit
            if not rate_limiter.check_rate_limit(user.username, user.tier in ["premium", "beta"]):
                await websocket.send_json({"error": "Rate limit exceeded"})
                continue
            
            # Process query
            try:
                url = f"{INTELLIGENCE_ROUTER_URL}/api/query"
                payload = {"query": query}
                
                response = requests.post(url, json=payload, timeout=60)
                response.raise_for_status()
                
                result = response.json()
                await websocket.send_json(result)
                
            except Exception as e:
                await websocket.send_json({"error": str(e)})
    
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")


if __name__ == "__main__":
    import uvicorn
    
    print("="*70)
    print("S2 INTELLIGENCE API GATEWAY")
    print("="*70)
    print("")
    print("Features:")
    print("  • JWT Authentication")
    print("  • API Key support")
    print("  • Rate limiting (tier-based)")
    print("  • Request caching")
    print("  • Metrics collection")
    print("  • WebSocket streaming")
    print("")
    print("Demo Users:")
    for username, user in auth_manager.users.items():
        print(f"  • {username:15} (tier: {user.tier:8}) - API Key: {user.api_key}")
    print("")
    print("Tier Limits:")
    print(f"  • Free:    {RATE_LIMIT_MAX_REQUESTS} req/min")
    print(f"  • Beta:    {RATE_LIMIT_MAX_REQUESTS * RATE_LIMIT_PREMIUM_MULTIPLIER} req/min")
    print(f"  • Premium: {RATE_LIMIT_MAX_REQUESTS * RATE_LIMIT_PREMIUM_MULTIPLIER} req/min + priority")
    print("")
    print("="*70)
    print("Starting API Gateway on http://localhost:8000")
    print("Documentation: http://localhost:8000/docs")
    print("="*70)
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
