"""
GRACE Role-Based Access Control (RBAC) System.

Provides comprehensive access control:
- Role-based permissions with inheritance
- Fine-grained permission definitions
- Attribute-based access conditions
- FastAPI integration (dependencies, middleware, decorators)
- Immutable audit logging of all authorization decisions

Usage:
    # Initialize RBAC
    from security.rbac import get_role_manager, get_permission_manager
    
    role_manager = get_role_manager(session)
    role_manager.initialize_built_in_roles()
    
    # Assign roles
    role_manager.assign_role("user-123", "developer")
    
    # Check permissions
    from security.rbac import get_enforcer
    
    enforcer = get_enforcer(session)
    result = enforcer.check_permission("user-123", "code:*:read")
    if result.allowed:
        # Access granted
        ...
    
    # FastAPI endpoint protection
    from security.rbac import create_permission_dependency
    
    @app.get(
        "/admin/users",
        dependencies=[Depends(create_permission_dependency("users:*:read"))]
    )
    def list_users():
        ...
    
    # Function-level authorization
    from security.rbac import require_permission
    
    @require_permission("code:healing:approve")
    def approve_healing(genesis_id: str, action_id: str):
        ...
"""

import logging

_logger = logging.getLogger(__name__)

try:
    from .models import (
        Role,
        Permission,
        UserRole,
        PolicyDocument,
        Condition,
        ConditionOperator,
        ResourceType,
        ActionType,
        PermissionCheck,
        AuthorizationContext,
    )
except ImportError as e:
    _logger.warning(f"Could not import models: {e}")
    Role = None
    Permission = None
    UserRole = None
    PolicyDocument = None
    Condition = None
    ConditionOperator = None
    ResourceType = None
    ActionType = None
    PermissionCheck = None
    AuthorizationContext = None

try:
    from .roles import (
        RoleManager,
        get_role_manager,
        BuiltInRole,
        ROLE_HIERARCHY,
        BUILT_IN_ROLE_DEFINITIONS,
    )
except ImportError as e:
    _logger.warning(f"Could not import roles: {e}")
    RoleManager = None
    get_role_manager = None
    BuiltInRole = None
    ROLE_HIERARCHY = {}
    BUILT_IN_ROLE_DEFINITIONS = {}

try:
    from .permissions import (
        PermissionManager,
        get_permission_manager,
        PERMISSION_DEFINITIONS,
        BUSINESS_HOURS_POLICY,
        INTERNAL_NETWORK_POLICY,
        OWNER_ONLY_POLICY,
    )
except ImportError as e:
    _logger.warning(f"Could not import permissions: {e}")
    PermissionManager = None
    get_permission_manager = None
    PERMISSION_DEFINITIONS = {}
    BUSINESS_HOURS_POLICY = None
    INTERNAL_NETWORK_POLICY = None
    OWNER_ONLY_POLICY = None

try:
    from .enforcer import (
        RBACEnforcer,
        get_enforcer,
        create_permission_dependency,
        require_permission,
        require_any,
        require_all,
        PermissionChecker,
        get_permission_checker,
    )
except ImportError as e:
    _logger.warning(f"Could not import enforcer: {e}")
    RBACEnforcer = None
    get_enforcer = None
    create_permission_dependency = None
    require_permission = None
    require_any = None
    require_all = None
    PermissionChecker = None
    get_permission_checker = None

try:
    from .middleware import (
        RBACMiddleware,
        RBACEnforcementMiddleware,
        PermissionCache,
        get_permission_cache,
        invalidate_user_cache,
        clear_permission_cache,
        ENDPOINT_PERMISSION_MAP,
    )
except ImportError as e:
    _logger.warning(f"Could not import middleware: {e}")
    RBACMiddleware = None
    RBACEnforcementMiddleware = None
    PermissionCache = None
    get_permission_cache = None
    invalidate_user_cache = None
    clear_permission_cache = None
    ENDPOINT_PERMISSION_MAP = {}

try:
    from .api import router as rbac_router
except ImportError as e:
    _logger.warning(f"Could not import API router: {e}")
    rbac_router = None


__all__ = [
    "Role",
    "Permission",
    "UserRole",
    "PolicyDocument",
    "Condition",
    "ConditionOperator",
    "ResourceType",
    "ActionType",
    "PermissionCheck",
    "AuthorizationContext",
    "RoleManager",
    "get_role_manager",
    "BuiltInRole",
    "ROLE_HIERARCHY",
    "BUILT_IN_ROLE_DEFINITIONS",
    "PermissionManager",
    "get_permission_manager",
    "PERMISSION_DEFINITIONS",
    "BUSINESS_HOURS_POLICY",
    "INTERNAL_NETWORK_POLICY",
    "OWNER_ONLY_POLICY",
    "RBACEnforcer",
    "get_enforcer",
    "create_permission_dependency",
    "require_permission",
    "require_any",
    "require_all",
    "PermissionChecker",
    "get_permission_checker",
    "RBACMiddleware",
    "RBACEnforcementMiddleware",
    "PermissionCache",
    "get_permission_cache",
    "invalidate_user_cache",
    "clear_permission_cache",
    "ENDPOINT_PERMISSION_MAP",
    "rbac_router",
]
