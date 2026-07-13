# API Calls & Database Connection Audit Report

**Date:** 2025-01-26  
**Project:** COSMOS Golf Betting MCP Server  
**Auditor:** AI Code Review

---

## Executive Summary

This audit reviews the API integrations and database connection setup in the COSMOS Golf Betting project. The project currently integrates with two external APIs but has **no database connections implemented yet**. The API implementations show good practices but have several security and reliability concerns that should be addressed.

---

## 🔴 Critical Issues

### 1. API Key Exposure in URL Parameters
**Location:** `mcp_server/tools/odds.py:40, 76-82`  
**Severity:** HIGH

**Issue:**
The Odds API key is passed as a query parameter (`apiKey`), which can:
- Be logged in server logs
- Appear in browser history
- Be exposed in referrer headers
- Be cached by intermediate proxies

**Current Code:**
```python
params = {"apiKey": self.api_key}
response = self.client.get(url, params=params)
```

**Recommendation:**
Move API key to request headers instead:
```python
headers = {"x-api-key": self.api_key}  # Or check API docs for header format
response = self.client.get(url, headers=headers)
```

**Note:** Some APIs require query params - verify The Odds API documentation for preferred authentication method.

---

### 2. Missing API Key Validation
**Location:** `mcp_server/config.py:10-11`  
**Severity:** MEDIUM

**Issue:**
API keys can be empty strings, which will only be caught at runtime when making API calls.

**Current Code:**
```python
ODDS_API_KEY = os.getenv("ODDS_API_KEY", "")
BALLDONTLIE_API_KEY = os.getenv("BALLDONTLIE_API_KEY", "")
```

**Recommendation:**
Validate at startup:
```python
ODDS_API_KEY = os.getenv("ODDS_API_KEY")
BALLDONTLIE_API_KEY = os.getenv("BALLDONTLIE_API_KEY")

if not ODDS_API_KEY:
    raise ValueError("ODDS_API_KEY environment variable is required")
if not BALLDONTLIE_API_KEY:
    raise ValueError("BALLDONTLIE_API_KEY environment variable is required")
```

---

### 3. No Rate Limiting Implementation
**Location:** All API client methods  
**Severity:** MEDIUM

**Issue:**
No rate limiting or throttling mechanisms to prevent hitting API limits, which could result in:
- API key suspension
- Extra costs
- Service disruption

**Recommendation:**
Implement rate limiting using a library like `ratelimit` or `tenacity`:
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def get_tournament_odds(self, ...):
    # existing code
```

Also add per-request delays to respect API rate limits.

---

## ⚠️ Important Concerns

### 4. Inefficient HTTP Client Usage
**Location:** `mcp_server/tools/odds.py:20, pga.py:19`  
**Severity:** MEDIUM

**Issue:**
Creating a new `httpx.Client` instance per client instance means:
- No connection reuse across requests
- Missing connection pooling optimizations
- Potential for connection exhaustion

**Current Code:**
```python
self.client = httpx.Client(timeout=30.0)
```

**Recommendation:**
- Use `httpx.AsyncClient` for async operations if possible
- Configure connection pool limits:
  ```python
  limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
  self.client = httpx.Client(timeout=30.0, limits=limits)
  ```
- Or use a singleton pattern for the HTTP client if multiple instances are created

---

### 5. Error Handling Inconsistencies
**Location:** Multiple methods in both API clients  
**Severity:** MEDIUM

**Issue:**
- `response.raise_for_status()` is used but errors aren't caught or handled gracefully
- No distinction between different HTTP error codes (429, 500, 401, etc.)
- No logging of failed requests

**Recommendation:**
Add comprehensive error handling:
```python
import logging

logger = logging.getLogger(__name__)

try:
    response = self.client.get(url, params=params)
    response.raise_for_status()
except httpx.HTTPStatusError as e:
    if e.response.status_code == 429:
        logger.warning("Rate limit exceeded. Retrying...")
        # Handle rate limiting
    elif e.response.status_code == 401:
        logger.error("Invalid API key")
        raise ValueError("Authentication failed - check API key")
    else:
        logger.error(f"API request failed: {e}")
        raise
except httpx.RequestError as e:
    logger.error(f"Network error: {e}")
    raise
```

---

### 6. Missing Input Validation
**Location:** All API client methods  
**Severity:** LOW

**Issue:**
No validation of input parameters (sport_key, regions, etc.) before making API calls.

**Recommendation:**
Add Pydantic validators or manual validation:
```python
from pydantic import validate_arguments

@validate_arguments
def get_tournament_odds(
    self,
    sport_key: str,  # Should validate format
    regions: Optional[list[str]] = None,
    ...
):
    if not sport_key or not sport_key.startswith("golf_"):
        raise ValueError(f"Invalid sport_key: {sport_key}. Must start with 'golf_'")
    # existing code
```

---

### 7. Timeout Configuration
**Location:** `mcp_server/tools/odds.py:20, pga.py:19`  
**Severity:** LOW

**Issue:**
Fixed 30-second timeout may be too long for simple requests or too short for complex operations.

**Recommendation:**
Use different timeouts for different operations or make it configurable:
```python
TIMEOUT_QUICK = 10.0  # For simple GET requests
TIMEOUT_STANDARD = 30.0  # For standard operations
TIMEOUT_LONG = 60.0  # For bulk operations

self.client = httpx.Client(timeout=TIMEOUT_STANDARD)
```

---

## ✅ Good Practices Found

1. **Environment Variables:** API keys are loaded from `.env` files (good security practice)
2. **Context Managers:** Both API clients implement `__enter__` and `__exit__` for proper resource cleanup
3. **Type Hints:** Good use of type hints throughout the codebase
4. **Pydantic Models:** Proper data validation with Pydantic schemas
5. **Structured Response Parsing:** Clear parsing of API responses into typed models

---

## 📊 Database Connection Status

### Current State: **NO DATABASE CONNECTIONS IMPLEMENTED**

The codebase shows:
- Cache directory structure in `config.py` (lines 18-22)
- `CachedData` model in `schemas.py` for storing cached data
- **No actual database client or connection code found**

### Recommendations for Database Setup:

1. **Choose a Database:**
   - **PostgreSQL** - Recommended for production (robust, feature-rich)
   - **SQLite** - Good for development/testing (simple, file-based)
   - **Supabase** - Good option if you want managed PostgreSQL with additional features

2. **Connection Management:**
   ```python
   # Example with SQLAlchemy
   from sqlalchemy import create_engine
   from sqlalchemy.orm import sessionmaker
   from sqlalchemy.pool import QueuePool
   
   DATABASE_URL = os.getenv("DATABASE_URL")
   
   engine = create_engine(
       DATABASE_URL,
       poolclass=QueuePool,
       pool_size=5,
       max_overflow=10,
       pool_pre_ping=True,  # Verify connections before using
       echo=False  # Set to True for SQL debugging
   )
   
   SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
   ```

3. **Security Considerations:**
   - Use connection pooling to prevent connection exhaustion
   - Enable SSL/TLS for production connections
   - Store database credentials in environment variables (never in code)
   - Use parameterized queries (SQLAlchemy does this automatically)
   - Set up proper database user permissions (least privilege principle)

4. **Environment Configuration:**
   ```python
   # Add to config.py
   DATABASE_URL = os.getenv("DATABASE_URL")
   DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
   DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
   ```

---

## 🔒 Security Checklist

- [ ] API keys stored in environment variables ✅
- [ ] API keys not exposed in logs ⚠️ (query params might be logged)
- [ ] API keys validated at startup ❌
- [ ] HTTPS used for all API calls ✅
- [ ] Input validation implemented ❌
- [ ] Error messages don't leak sensitive info ⚠️ (needs review)
- [ ] Rate limiting implemented ❌
- [ ] Database credentials in environment variables ✅ (when implemented)
- [ ] Database connection uses SSL/TLS ❌ (when implemented)
- [ ] SQL injection protection ✅ (via Pydantic, but ensure parameterized queries)

---

## 📝 Action Items

### High Priority:
1. **Move API keys from query params to headers** (if API supports it)
2. **Add API key validation at startup**
3. **Implement rate limiting for API calls**
4. **Add comprehensive error handling with logging**

### Medium Priority:
5. **Optimize HTTP client with connection pooling**
6. **Add input validation for all API method parameters**
7. **Create database connection module** (if database is needed)
8. **Add request/response logging**

### Low Priority:
9. **Make timeout values configurable**
10. **Add retry logic with exponential backoff**
11. **Add monitoring/metrics for API call success rates**

---

## 📚 Additional Recommendations

1. **Create `.env.example` file:**
   ```
   ODDS_API_KEY=your_odds_api_key_here
   BALLDONTLIE_API_KEY=your_balldontlie_api_key_here
   DATABASE_URL=postgresql://user:pass@localhost:5432/cosmos_golf
   ```

2. **Add to `.gitignore`:**
   ```
   .env
   *.db
   *.sqlite
   __pycache__/
   ```

3. **Add logging configuration:**
   ```python
   import logging
   
   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
   )
   ```

4. **Consider adding health checks:**
   - Endpoint to verify API connectivity
   - Database connection health check
   - API key validity check

---

## 🧪 Testing Recommendations

1. **Unit Tests:**
   - Test API client initialization with missing keys
   - Test error handling for various HTTP status codes
   - Test input validation

2. **Integration Tests:**
   - Test actual API calls (with mocked responses or test API keys)
   - Test database connections (with test database)

3. **Security Tests:**
   - Verify API keys aren't logged
   - Test SQL injection prevention (when database is added)
   - Test rate limiting behavior

---

**Report Generated:** 2025-01-26  
**Next Review:** Recommended after implementing critical fixes
