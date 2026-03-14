import pytest
import time
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import Request, Response
from backend.genesis.middleware import GenesisKeyMiddleware

@pytest.fixture
def middleware():
    # We patch all the external dependencies
    with patch('backend.genesis.middleware.get_genesis_service') as mock_gk, \
         patch('backend.genesis.middleware.get_kb_integration') as mock_kb:
             
        mock_gk_inst = MagicMock()
        mock_gk_inst.create_key.return_value = MagicMock(key_id="request-gk-123")
        mock_gk_inst.generate_user_id.return_value = "GU-xyz"
        mock_gk.return_value = mock_gk_inst
        
        mock_kb.return_value = MagicMock()
        
        app = MagicMock()
        return GenesisKeyMiddleware(app), mock_gk_inst

@pytest.mark.asyncio
async def test_middleware_tracking(middleware):
    mw, gk_service = middleware
    
    # Mock request
    request = MagicMock(spec=Request)
    request.headers = {"user-agent": "test"}
    request.cookies = {}
    request.url.path = "/api/v1/test"
    request.method = "POST"
    request.query_params = {}
    
    # Need to mock the body method as async
    request.body = AsyncMock(return_value=b'{"test": "data"}')
    
    # Mock Next call
    mock_response = AsyncMock(spec=Response)
    mock_response.status_code = 200
    mock_response.headers = {}
    
    # Mock the return value of an async generator for the response body
    async def body_iter():
        yield b'{"result": "success"}'
    mock_response.body_iterator = body_iter()
    
    # Our call next mock
    async def call_next(req):
        return mock_response
        
    response = await mw.dispatch(request, call_next)
    
    assert response.status_code == 200
    # Two key creations (request, response)
    assert gk_service.create_key.call_count == 2
    
@pytest.mark.asyncio
async def test_skip_tracking(middleware):
    mw, gk_service = middleware
    
    request = MagicMock(spec=Request)
    request.headers = {}
    request.cookies = {}
    request.url.path = "/health"
    
    async def call_next(req):
        return MagicMock(status_code=200)
        
    await mw.dispatch(request, call_next)
    
    # Should skip
    gk_service.create_key.assert_not_called()

def test_get_or_create_genesis_id(middleware):
    mw, gk_service = middleware
    
    request = MagicMock()
    request.headers = {"X-Genesis-ID": "GU-123"}
    request.cookies = {}
    
    assert mw._get_or_create_genesis_id(request) == "GU-123"
    
    request.headers = {}
    request.cookies = {"genesis_id": "GU-456"}
    assert mw._get_or_create_genesis_id(request) == "GU-456"

if __name__ == "__main__":
    pytest.main(['-v', __file__])
