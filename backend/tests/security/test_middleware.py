import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi import Request, Response
from security.middleware import RateLimitMiddleware, RequestValidationMiddleware, SecurityHeadersMiddleware

@pytest.mark.asyncio
async def test_security_headers_middleware():
    app = MagicMock()
    middleware = SecurityHeadersMiddleware(app)
    
    request = MagicMock(spec=Request)
    call_next = AsyncMock(return_value=Response())
    
    response = await middleware.dispatch(request, call_next)
    
    assert "X-Content-Type-Options" in response.headers
    assert "X-XSS-Protection" in response.headers
    assert "server" not in response.headers

@pytest.mark.asyncio
async def test_request_validation_block_xss():
    app = MagicMock()
    middleware = RequestValidationMiddleware(app)
    
    request = MagicMock(spec=Request)
    request.url = MagicMock()
    request.url.__str__.return_value = "http://localhost/api?q=<script>alert("
    request.method = "GET"
    
    call_next = AsyncMock(return_value=Response())
    
    response = await middleware.dispatch(request, call_next)
    
    # Should block XSS pattern and return 400
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_request_validation_block_path_traversal():
    app = MagicMock()
    middleware = RequestValidationMiddleware(app)
    
    request = MagicMock(spec=Request)
    request.url = MagicMock()
    request.url.__str__.return_value = "http://localhost/api?file=../../etc/passwd"
    request.method = "GET"
    
    call_next = AsyncMock(return_value=Response())
    
    response = await middleware.dispatch(request, call_next)
    
    # Needs to block directory traversal
    assert response.status_code == 400

def test_rate_limit_parsing():
    middleware = RateLimitMiddleware(MagicMock())
    count, seconds = middleware._parse_limit("50/minute")
    assert count == 50
    assert seconds == 60

@pytest.mark.asyncio
async def test_rate_limit_exemptions():
    app = MagicMock()
    middleware = RateLimitMiddleware(app)
    
    request = MagicMock(spec=Request)
    request.url.path = "/health"
    request.method = "GET"
    
    call_next = AsyncMock(return_value=Response(status_code=200))
    response = await middleware.dispatch(request, call_next)
    
    # Static and health paths bypass rate limiting
    assert response.status_code == 200

if __name__ == "__main__":
    pytest.main(['-v', __file__])
