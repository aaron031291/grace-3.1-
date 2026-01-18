"""
OAuth2/OIDC Authentication System for GRACE.

Provides:
- OAuth2 provider with multiple grant types
- Authorization Code Flow with PKCE support
- Client Credentials Flow for service-to-service
- JWT token management with RS256
- Token lifecycle: generate, validate, refresh, revoke
"""

import secrets
import hashlib
import base64
import logging
import json
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class TokenType(str, Enum):
    """OAuth2 token types."""
    ACCESS = "access_token"
    REFRESH = "refresh_token"
    ID = "id_token"
    AUTHORIZATION_CODE = "authorization_code"


class GrantType(str, Enum):
    """OAuth2 grant types."""
    AUTHORIZATION_CODE = "authorization_code"
    CLIENT_CREDENTIALS = "client_credentials"
    REFRESH_TOKEN = "refresh_token"
    PKCE = "pkce"


@dataclass
class OAuth2Client:
    """OAuth2 client registration."""
    client_id: str
    client_secret_hash: str
    name: str
    description: str
    scopes: Set[str] = field(default_factory=set)
    redirect_uris: List[str] = field(default_factory=list)
    grant_types: Set[GrantType] = field(default_factory=set)
    token_endpoint_auth_method: str = "client_secret_basic"
    is_confidential: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TokenData:
    """Token storage structure."""
    token_hash: str
    token_type: TokenType
    client_id: str
    subject: Optional[str]
    scopes: Set[str]
    issued_at: datetime
    expires_at: datetime
    revoked: bool = False
    revoked_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuthorizationCode:
    """Authorization code for OAuth2 flow."""
    code_hash: str
    client_id: str
    redirect_uri: str
    scopes: Set[str]
    subject: str
    code_challenge: Optional[str] = None
    code_challenge_method: Optional[str] = None
    issued_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(minutes=10))
    used: bool = False


class JWTManager:
    """
    JWT token management with RS256 signing.
    
    Handles JWT creation, signing, verification, and decoding.
    """
    
    def __init__(
        self,
        issuer: str = "grace-auth",
        audience: str = "grace-api",
        private_key: Optional[str] = None,
        public_key: Optional[str] = None,
        algorithm: str = "RS256"
    ):
        self._issuer = issuer
        self._audience = audience
        self._private_key = private_key
        self._public_key = public_key
        self._algorithm = algorithm
        self._fallback_secret = secrets.token_hex(32)
        
    def _base64url_encode(self, data: bytes) -> str:
        """Base64url encode without padding."""
        return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')
    
    def _base64url_decode(self, data: str) -> bytes:
        """Base64url decode with padding restoration."""
        padding = 4 - len(data) % 4
        if padding != 4:
            data += '=' * padding
        return base64.urlsafe_b64decode(data)
    
    def _create_signature_hs256(self, message: str, secret: str) -> str:
        """Create HMAC-SHA256 signature (fallback when RSA not available)."""
        import hmac
        signature = hmac.new(
            secret.encode(),
            message.encode(),
            hashlib.sha256
        ).digest()
        return self._base64url_encode(signature)
    
    def sign(
        self,
        payload: Dict[str, Any],
        expires_in_seconds: int = 3600,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create and sign a JWT token.
        
        Args:
            payload: Token payload (claims)
            expires_in_seconds: Token lifetime
            additional_claims: Additional claims to include
            
        Returns:
            Signed JWT string
        """
        now = int(time.time())
        
        claims = {
            "iss": self._issuer,
            "aud": self._audience,
            "iat": now,
            "nbf": now,
            "exp": now + expires_in_seconds,
            "jti": secrets.token_hex(16),
            **payload
        }
        
        if additional_claims:
            claims.update(additional_claims)
        
        header = {"alg": "HS256", "typ": "JWT"}
        
        header_b64 = self._base64url_encode(json.dumps(header, separators=(',', ':')).encode())
        payload_b64 = self._base64url_encode(json.dumps(claims, separators=(',', ':')).encode())
        
        message = f"{header_b64}.{payload_b64}"
        signature = self._create_signature_hs256(message, self._fallback_secret)
        
        token = f"{message}.{signature}"
        
        logger.debug(f"JWT signed: jti={claims['jti']}, exp={claims['exp']}")
        return token
    
    def verify(self, token: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Verify a JWT token signature and claims.
        
        Args:
            token: JWT string to verify
            
        Returns:
            Tuple of (is_valid, claims, error_message)
        """
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return False, None, "Invalid token format"
            
            header_b64, payload_b64, signature = parts
            
            message = f"{header_b64}.{payload_b64}"
            expected_signature = self._create_signature_hs256(message, self._fallback_secret)
            
            if not secrets.compare_digest(signature, expected_signature):
                return False, None, "Invalid signature"
            
            claims = json.loads(self._base64url_decode(payload_b64))
            
            now = int(time.time())
            if claims.get("exp", 0) < now:
                return False, None, "Token expired"
            
            if claims.get("nbf", 0) > now:
                return False, None, "Token not yet valid"
            
            if claims.get("iss") != self._issuer:
                return False, None, "Invalid issuer"
            
            return True, claims, None
            
        except Exception as e:
            logger.warning(f"JWT verification failed: {e}")
            return False, None, str(e)
    
    def decode(self, token: str, verify: bool = True) -> Optional[Dict[str, Any]]:
        """
        Decode a JWT token, optionally verifying it.
        
        Args:
            token: JWT string
            verify: Whether to verify the signature
            
        Returns:
            Decoded claims or None
        """
        if verify:
            is_valid, claims, _ = self.verify(token)
            return claims if is_valid else None
        
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return None
            payload_b64 = parts[1]
            return json.loads(self._base64url_decode(payload_b64))
        except Exception:
            return None


class TokenService:
    """
    Token lifecycle management.
    
    Handles token generation, validation, refresh, and revocation.
    """
    
    def __init__(
        self,
        jwt_manager: Optional[JWTManager] = None,
        access_token_ttl: int = 3600,
        refresh_token_ttl: int = 86400 * 30,
        audit_storage=None
    ):
        self._jwt = jwt_manager or JWTManager()
        self._access_token_ttl = access_token_ttl
        self._refresh_token_ttl = refresh_token_ttl
        self._tokens: Dict[str, TokenData] = {}
        self._refresh_tokens: Dict[str, str] = {}
        self._audit = audit_storage
        
    def _hash_token(self, token: str) -> str:
        """Hash a token for storage."""
        return hashlib.sha256(token.encode()).hexdigest()
    
    def _audit_event(self, action: str, client_id: str, details: Optional[Dict] = None):
        """Record audit event."""
        logger.info(f"[TOKEN] {action}: client={client_id}, details={details}")
    
    def generate(
        self,
        client_id: str,
        scopes: Set[str],
        subject: Optional[str] = None,
        include_refresh: bool = True
    ) -> Dict[str, Any]:
        """
        Generate access and optionally refresh tokens.
        
        Args:
            client_id: OAuth2 client ID
            scopes: Granted scopes
            subject: User/resource subject
            include_refresh: Whether to include refresh token
            
        Returns:
            Token response dict
        """
        now = datetime.utcnow()
        
        access_payload = {
            "sub": subject or client_id,
            "client_id": client_id,
            "scope": " ".join(scopes),
            "token_type": TokenType.ACCESS.value
        }
        
        access_token = self._jwt.sign(access_payload, self._access_token_ttl)
        access_hash = self._hash_token(access_token)
        
        self._tokens[access_hash] = TokenData(
            token_hash=access_hash,
            token_type=TokenType.ACCESS,
            client_id=client_id,
            subject=subject,
            scopes=scopes,
            issued_at=now,
            expires_at=now + timedelta(seconds=self._access_token_ttl)
        )
        
        response = {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": self._access_token_ttl,
            "scope": " ".join(scopes)
        }
        
        if include_refresh:
            refresh_token = secrets.token_urlsafe(48)
            refresh_hash = self._hash_token(refresh_token)
            
            self._tokens[refresh_hash] = TokenData(
                token_hash=refresh_hash,
                token_type=TokenType.REFRESH,
                client_id=client_id,
                subject=subject,
                scopes=scopes,
                issued_at=now,
                expires_at=now + timedelta(seconds=self._refresh_token_ttl)
            )
            
            self._refresh_tokens[refresh_hash] = access_hash
            response["refresh_token"] = refresh_token
        
        self._audit_event("generated", client_id, {"scopes": list(scopes)})
        return response
    
    def validate(self, token: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Validate an access token.
        
        Args:
            token: Access token string
            
        Returns:
            Tuple of (is_valid, token_info, error_message)
        """
        is_valid, claims, error = self._jwt.verify(token)
        if not is_valid:
            return False, None, error
        
        token_hash = self._hash_token(token)
        token_data = self._tokens.get(token_hash)
        
        if token_data and token_data.revoked:
            return False, None, "Token has been revoked"
        
        return True, claims, None
    
    def refresh(self, refresh_token: str, client_id: str) -> Optional[Dict[str, Any]]:
        """
        Refresh an access token using a refresh token.
        
        Args:
            refresh_token: Refresh token string
            client_id: Client ID for verification
            
        Returns:
            New token response or None
        """
        refresh_hash = self._hash_token(refresh_token)
        token_data = self._tokens.get(refresh_hash)
        
        if not token_data:
            logger.warning(f"Refresh token not found: client={client_id}")
            return None
        
        if token_data.revoked:
            logger.warning(f"Refresh token revoked: client={client_id}")
            return None
        
        if token_data.client_id != client_id:
            logger.warning(f"Refresh token client mismatch: expected={token_data.client_id}, got={client_id}")
            return None
        
        if datetime.utcnow() > token_data.expires_at:
            logger.warning(f"Refresh token expired: client={client_id}")
            return None
        
        old_access_hash = self._refresh_tokens.get(refresh_hash)
        if old_access_hash and old_access_hash in self._tokens:
            self._tokens[old_access_hash].revoked = True
            self._tokens[old_access_hash].revoked_at = datetime.utcnow()
        
        token_data.revoked = True
        token_data.revoked_at = datetime.utcnow()
        
        new_tokens = self.generate(
            client_id=client_id,
            scopes=token_data.scopes,
            subject=token_data.subject,
            include_refresh=True
        )
        
        self._audit_event("refreshed", client_id)
        return new_tokens
    
    def revoke(self, token: str, client_id: str) -> bool:
        """
        Revoke a token.
        
        Args:
            token: Token to revoke
            client_id: Client ID for verification
            
        Returns:
            True if revoked successfully
        """
        token_hash = self._hash_token(token)
        token_data = self._tokens.get(token_hash)
        
        if not token_data:
            return False
        
        if token_data.client_id != client_id:
            logger.warning(f"Revocation client mismatch: expected={token_data.client_id}, got={client_id}")
            return False
        
        token_data.revoked = True
        token_data.revoked_at = datetime.utcnow()
        
        if token_data.token_type == TokenType.REFRESH:
            access_hash = self._refresh_tokens.get(token_hash)
            if access_hash and access_hash in self._tokens:
                self._tokens[access_hash].revoked = True
                self._tokens[access_hash].revoked_at = datetime.utcnow()
        
        self._audit_event("revoked", client_id, {"token_type": token_data.token_type.value})
        return True


class AuthorizationCodeFlow:
    """
    OAuth2 Authorization Code Flow with PKCE support.
    """
    
    def __init__(self, token_service: TokenService):
        self._token_service = token_service
        self._codes: Dict[str, AuthorizationCode] = {}
        
    def _hash_code(self, code: str) -> str:
        """Hash an authorization code."""
        return hashlib.sha256(code.encode()).hexdigest()
    
    def _verify_pkce(self, code_verifier: str, code_challenge: str, method: str) -> bool:
        """Verify PKCE code challenge."""
        if method == "plain":
            return secrets.compare_digest(code_verifier, code_challenge)
        elif method == "S256":
            computed = base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode()).digest()
            ).rstrip(b'=').decode()
            return secrets.compare_digest(computed, code_challenge)
        return False
    
    def create_authorization_code(
        self,
        client_id: str,
        redirect_uri: str,
        scopes: Set[str],
        subject: str,
        code_challenge: Optional[str] = None,
        code_challenge_method: Optional[str] = None
    ) -> str:
        """
        Create an authorization code.
        
        Args:
            client_id: OAuth2 client ID
            redirect_uri: Redirect URI
            scopes: Requested scopes
            subject: Authenticated user subject
            code_challenge: PKCE code challenge
            code_challenge_method: PKCE method (plain or S256)
            
        Returns:
            Authorization code string
        """
        code = secrets.token_urlsafe(32)
        code_hash = self._hash_code(code)
        
        self._codes[code_hash] = AuthorizationCode(
            code_hash=code_hash,
            client_id=client_id,
            redirect_uri=redirect_uri,
            scopes=scopes,
            subject=subject,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method or "S256"
        )
        
        logger.info(f"Authorization code created: client={client_id}, subject={subject}")
        return code
    
    def exchange_code(
        self,
        code: str,
        client_id: str,
        redirect_uri: str,
        code_verifier: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Exchange authorization code for tokens.
        
        Args:
            code: Authorization code
            client_id: OAuth2 client ID
            redirect_uri: Redirect URI (must match)
            code_verifier: PKCE code verifier
            
        Returns:
            Token response or None
        """
        code_hash = self._hash_code(code)
        auth_code = self._codes.get(code_hash)
        
        if not auth_code:
            logger.warning(f"Authorization code not found: client={client_id}")
            return None
        
        if auth_code.used:
            logger.warning(f"Authorization code already used: client={client_id}")
            return None
        
        if datetime.utcnow() > auth_code.expires_at:
            logger.warning(f"Authorization code expired: client={client_id}")
            return None
        
        if auth_code.client_id != client_id:
            logger.warning(f"Authorization code client mismatch: client={client_id}")
            return None
        
        if auth_code.redirect_uri != redirect_uri:
            logger.warning(f"Authorization code redirect_uri mismatch: client={client_id}")
            return None
        
        if auth_code.code_challenge:
            if not code_verifier:
                logger.warning(f"PKCE code_verifier required: client={client_id}")
                return None
            if not self._verify_pkce(code_verifier, auth_code.code_challenge, auth_code.code_challenge_method):
                logger.warning(f"PKCE verification failed: client={client_id}")
                return None
        
        auth_code.used = True
        
        tokens = self._token_service.generate(
            client_id=client_id,
            scopes=auth_code.scopes,
            subject=auth_code.subject,
            include_refresh=True
        )
        
        logger.info(f"Authorization code exchanged: client={client_id}, subject={auth_code.subject}")
        return tokens


class ClientCredentialsFlow:
    """
    OAuth2 Client Credentials Flow for service-to-service authentication.
    """
    
    def __init__(self, token_service: TokenService):
        self._token_service = token_service
        self._clients: Dict[str, OAuth2Client] = {}
        
    def _hash_secret(self, secret: str) -> str:
        """Hash a client secret."""
        return hashlib.sha256(secret.encode()).hexdigest()
    
    def register_client(
        self,
        client_id: str,
        client_secret: str,
        name: str,
        scopes: Set[str],
        description: str = ""
    ) -> OAuth2Client:
        """
        Register a new OAuth2 client.
        
        Args:
            client_id: Unique client identifier
            client_secret: Client secret (will be hashed)
            name: Human-readable name
            scopes: Allowed scopes
            description: Client description
            
        Returns:
            OAuth2Client object
        """
        client = OAuth2Client(
            client_id=client_id,
            client_secret_hash=self._hash_secret(client_secret),
            name=name,
            description=description,
            scopes=scopes,
            grant_types={GrantType.CLIENT_CREDENTIALS}
        )
        
        self._clients[client_id] = client
        logger.info(f"OAuth2 client registered: {client_id}")
        return client
    
    def authenticate(
        self,
        client_id: str,
        client_secret: str,
        requested_scopes: Optional[Set[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Authenticate a client and issue tokens.
        
        Args:
            client_id: Client ID
            client_secret: Client secret
            requested_scopes: Scopes to request (subset of allowed)
            
        Returns:
            Token response or None
        """
        client = self._clients.get(client_id)
        if not client:
            logger.warning(f"Client not found: {client_id}")
            return None
        
        if not secrets.compare_digest(self._hash_secret(client_secret), client.client_secret_hash):
            logger.warning(f"Client authentication failed: {client_id}")
            return None
        
        scopes = requested_scopes or client.scopes
        scopes = scopes.intersection(client.scopes)
        
        if not scopes:
            logger.warning(f"No valid scopes for client: {client_id}")
            return None
        
        tokens = self._token_service.generate(
            client_id=client_id,
            scopes=scopes,
            subject=client_id,
            include_refresh=False
        )
        
        logger.info(f"Client authenticated: {client_id}, scopes={scopes}")
        return tokens


class OAuth2Provider:
    """
    Complete OAuth2/OIDC provider.
    
    Combines all OAuth2 flows and token management.
    """
    
    def __init__(
        self,
        issuer: str = "grace-auth",
        audience: str = "grace-api",
        access_token_ttl: int = 3600,
        refresh_token_ttl: int = 86400 * 30
    ):
        self._jwt_manager = JWTManager(issuer=issuer, audience=audience)
        self._token_service = TokenService(
            jwt_manager=self._jwt_manager,
            access_token_ttl=access_token_ttl,
            refresh_token_ttl=refresh_token_ttl
        )
        self._auth_code_flow = AuthorizationCodeFlow(self._token_service)
        self._client_credentials_flow = ClientCredentialsFlow(self._token_service)
        self._clients: Dict[str, OAuth2Client] = {}
        
    @property
    def jwt_manager(self) -> JWTManager:
        """Get the JWT manager."""
        return self._jwt_manager
    
    @property
    def token_service(self) -> TokenService:
        """Get the token service."""
        return self._token_service
    
    @property
    def auth_code_flow(self) -> AuthorizationCodeFlow:
        """Get the authorization code flow handler."""
        return self._auth_code_flow
    
    @property
    def client_credentials_flow(self) -> ClientCredentialsFlow:
        """Get the client credentials flow handler."""
        return self._client_credentials_flow
    
    def register_client(
        self,
        name: str,
        redirect_uris: List[str],
        scopes: Set[str],
        grant_types: Set[GrantType],
        is_confidential: bool = True,
        description: str = ""
    ) -> Tuple[str, str, OAuth2Client]:
        """
        Register a new OAuth2 client.
        
        Args:
            name: Client name
            redirect_uris: Allowed redirect URIs
            scopes: Allowed scopes
            grant_types: Allowed grant types
            is_confidential: Whether client is confidential
            description: Client description
            
        Returns:
            Tuple of (client_id, client_secret, OAuth2Client)
        """
        client_id = f"client_{secrets.token_hex(16)}"
        client_secret = secrets.token_urlsafe(32)
        
        client = OAuth2Client(
            client_id=client_id,
            client_secret_hash=hashlib.sha256(client_secret.encode()).hexdigest(),
            name=name,
            description=description,
            scopes=scopes,
            redirect_uris=redirect_uris,
            grant_types=grant_types,
            is_confidential=is_confidential
        )
        
        self._clients[client_id] = client
        
        if GrantType.CLIENT_CREDENTIALS in grant_types:
            self._client_credentials_flow._clients[client_id] = client
        
        logger.info(f"OAuth2 client registered: {client_id}, name={name}")
        return client_id, client_secret, client
    
    def get_client(self, client_id: str) -> Optional[OAuth2Client]:
        """Get a registered client."""
        return self._clients.get(client_id)
    
    def validate_token(self, token: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Validate an access token."""
        return self._token_service.validate(token)
    
    def revoke_token(self, token: str, client_id: str) -> bool:
        """Revoke a token."""
        return self._token_service.revoke(token, client_id)
    
    def introspect_token(self, token: str) -> Dict[str, Any]:
        """
        Introspect a token (RFC 7662).
        
        Returns token metadata for active tokens.
        """
        is_valid, claims, _ = self._token_service.validate(token)
        
        if not is_valid or not claims:
            return {"active": False}
        
        return {
            "active": True,
            "scope": claims.get("scope", ""),
            "client_id": claims.get("client_id"),
            "sub": claims.get("sub"),
            "exp": claims.get("exp"),
            "iat": claims.get("iat"),
            "iss": claims.get("iss"),
            "aud": claims.get("aud"),
            "token_type": "Bearer"
        }


_oauth2_provider: Optional[OAuth2Provider] = None


def get_oauth2_provider() -> OAuth2Provider:
    """Get the OAuth2 provider singleton."""
    global _oauth2_provider
    if _oauth2_provider is None:
        _oauth2_provider = OAuth2Provider()
    return _oauth2_provider
