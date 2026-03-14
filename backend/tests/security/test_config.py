import pytest
import os
from unittest.mock import patch
from security.config import SecurityConfig, get_security_config

def test_config_singleton():
    c1 = get_security_config()
    c2 = get_security_config()
    assert c1 is c2

def test_default_config_values():
    config = SecurityConfig()
    assert config.PRODUCTION_MODE is False
    assert config.SESSION_MAX_AGE_HOURS == 24
    assert config.CORS_MAX_AGE == 600
    assert len(config.CORS_ALLOWED_ORIGINS) > 0

@patch.dict(os.environ, {"PRODUCTION_MODE": "true", "CORS_ALLOWED_ORIGINS": "https://foo.com"})
def test_config_env_overrides():
    config = SecurityConfig()
    config.__post_init__()
    
    assert config.PRODUCTION_MODE is True
    assert config.SESSION_COOKIE_SECURE is True
    assert config.HSTS_ENABLED is True
    assert config.CORS_ALLOWED_ORIGINS == ["https://foo.com"]

def test_csp_header_generation():
    config = SecurityConfig()
    csp = config.get_csp_header()
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp

def test_hsts_header_generation():
    config = SecurityConfig()
    
    config.HSTS_ENABLED = False
    assert config.get_hsts_header() == ""
    
    config.HSTS_ENABLED = True
    config.HSTS_MAX_AGE = 1000
    config.HSTS_INCLUDE_SUBDOMAINS = True
    config.HSTS_PRELOAD = False
    
    hsts = config.get_hsts_header()
    assert "max-age=1000" in hsts
    assert "includeSubDomains" in hsts

if __name__ == "__main__":
    pytest.main(['-v', __file__])
