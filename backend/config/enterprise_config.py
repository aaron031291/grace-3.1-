"""
Enterprise Configuration Module
===============================

Enables/disables enterprise features for finance, law, and hedge fund clients.

Usage:
    from config.enterprise_config import EnterpriseConfig
    
    if EnterpriseConfig.ENABLE_GOVERNANCE:
        # Governance features enabled
        pass
"""

import os
from typing import Dict, Any
from enum import Enum


class IndustryType(str, Enum):
    """Industry types for pre-configured settings."""
    FINANCE = "finance"
    LAW = "law"
    HEDGE_FUND = "hedge_fund"
    GENERAL = "general"


class EnterpriseConfig:
    """
    Enterprise configuration - controls which enterprise features are enabled.
    
    Set via environment variables:
    - GRACE_ENTERPRISE_MODE=true
    - GRACE_INDUSTRY_TYPE=finance|law|hedge_fund
    - GRACE_ENABLE_GOVERNANCE=true
    - etc.
    """
    
    # ========================================================================
    # Core Enterprise Mode
    # ========================================================================
    
    ENTERPRISE_MODE: bool = os.getenv("GRACE_ENTERPRISE_MODE", "true").lower() == "true"
    INDUSTRY_TYPE: IndustryType = IndustryType(
        os.getenv("GRACE_INDUSTRY_TYPE", "general").lower()
    )
    
    # ========================================================================
    # Governance Features
    # ========================================================================
    
    ENABLE_GOVERNANCE: bool = os.getenv(
        "GRACE_ENABLE_GOVERNANCE", 
        "true" if ENTERPRISE_MODE else "false"
    ).lower() == "true"
    
    ENABLE_PARLIAMENT_GOVERNANCE: bool = os.getenv(
        "GRACE_ENABLE_PARLIAMENT_GOVERNANCE",
        "true" if ENTERPRISE_MODE else "false"
    ).lower() == "true"
    
    ENABLE_DECISION_REVIEW: bool = os.getenv(
        "GRACE_ENABLE_DECISION_REVIEW",
        "true" if ENTERPRISE_MODE else "false"
    ).lower() == "true"
    
    ENABLE_COMPLIANCE_RULES: bool = os.getenv(
        "GRACE_ENABLE_COMPLIANCE_RULES",
        "true" if ENTERPRISE_MODE else "false"
    ).lower() == "true"
    
    # ========================================================================
    # Whitelisting Features
    # ========================================================================
    
    ENABLE_WHITELIST: bool = os.getenv(
        "GRACE_ENABLE_WHITELIST",
        "true" if ENTERPRISE_MODE else "false"
    ).lower() == "true"
    
    ENABLE_WHITELIST_APPROVAL: bool = os.getenv(
        "GRACE_ENABLE_WHITELIST_APPROVAL",
        "true" if ENTERPRISE_MODE else "false"
    ).lower() == "true"
    
    ENABLE_SOURCE_VERIFICATION: bool = os.getenv(
        "GRACE_ENABLE_SOURCE_VERIFICATION",
        "true" if ENTERPRISE_MODE else "false"
    ).lower() == "true"
    
    # ========================================================================
    # Security & Layering Features
    # ========================================================================
    
    ENABLE_LAYER1_ENFORCEMENT: bool = os.getenv(
        "GRACE_ENABLE_LAYER1_ENFORCEMENT",
        "true" if ENTERPRISE_MODE else "false"
    ).lower() == "true"
    
    ENABLE_GENESIS_TRACKING: bool = os.getenv(
        "GRACE_ENABLE_GENESIS_TRACKING",
        "true" if ENTERPRISE_MODE else "false"
    ).lower() == "true"
    
    ENABLE_AUDIT_LOGGING: bool = os.getenv(
        "GRACE_ENABLE_AUDIT_LOGGING",
        "true" if ENTERPRISE_MODE else "false"
    ).lower() == "true"
    
    ENABLE_DATA_ISOLATION: bool = os.getenv(
        "GRACE_ENABLE_DATA_ISOLATION",
        "true" if ENTERPRISE_MODE else "false"
    ).lower() == "true"
    
    # ========================================================================
    # Secure Ingestion Features
    # ========================================================================
    
    ENABLE_SECURE_INGESTION: bool = os.getenv(
        "GRACE_ENABLE_SECURE_INGESTION",
        "true" if ENTERPRISE_MODE else "false"
    ).lower() == "true"
    
    ENABLE_CONTENT_HASHING: bool = os.getenv(
        "GRACE_ENABLE_CONTENT_HASHING",
        "true" if ENTERPRISE_MODE else "false"
    ).lower() == "true"
    
    ENABLE_INTEGRITY_VERIFICATION: bool = os.getenv(
        "GRACE_ENABLE_INTEGRITY_VERIFICATION",
        "true" if ENTERPRISE_MODE else "false"
    ).lower() == "true"
    
    ENABLE_INGESTION_AUDIT: bool = os.getenv(
        "GRACE_ENABLE_INGESTION_AUDIT",
        "true" if ENTERPRISE_MODE else "false"
    ).lower() == "true"
    
    # ========================================================================
    # Industry-Specific Settings
    # ========================================================================
    
    @classmethod
    def get_industry_config(cls) -> Dict[str, Any]:
        """
        Get industry-specific configuration.
        
        Returns:
            Dict with industry-specific settings
        """
        configs = {
            IndustryType.FINANCE: {
                "governance": {
                    "strict_mode": True,
                    "compliance_rules": ["FINRA", "SEC", "SOX"],
                    "decision_review_required": True,
                },
                "whitelisting": {
                    "strict_mode": True,
                    "approval_required": True,
                    "source_verification": True,
                },
                "ingestion": {
                    "content_hashing": True,
                    "audit_logging": True,
                    "integrity_verification": True,
                },
                "security": {
                    "layer1_enforcement": True,
                    "genesis_tracking": True,
                    "data_isolation": True,
                },
            },
            IndustryType.LAW: {
                "governance": {
                    "strict_mode": True,
                    "privilege_protection": True,
                    "client_isolation": True,
                    "decision_review_required": True,
                },
                "whitelisting": {
                    "strict_mode": True,
                    "client_specific_whitelists": True,
                    "approval_workflow": True,
                },
                "ingestion": {
                    "content_hashing": True,
                    "privilege_detection": True,
                    "client_tagging": True,
                },
                "security": {
                    "encryption_at_rest": True,
                    "access_control": "strict",
                    "audit_logging": "comprehensive",
                },
            },
            IndustryType.HEDGE_FUND: {
                "governance": {
                    "strict_mode": True,
                    "strategy_isolation": True,
                    "performance_tracking": True,
                },
                "whitelisting": {
                    "market_data_sources": "whitelisted",
                    "strategy_specific": True,
                },
                "ingestion": {
                    "real_time_ingestion": True,
                    "market_data_validation": True,
                },
                "security": {
                    "strategy_isolation": True,
                    "performance_encryption": True,
                },
            },
            IndustryType.GENERAL: {
                "governance": {
                    "strict_mode": False,
                    "decision_review_required": False,
                },
                "whitelisting": {
                    "strict_mode": False,
                    "approval_required": False,
                },
                "ingestion": {
                    "content_hashing": True,
                    "audit_logging": True,
                },
                "security": {
                    "layer1_enforcement": True,
                    "genesis_tracking": True,
                },
            },
        }
        
        return configs.get(cls.INDUSTRY_TYPE, configs[IndustryType.GENERAL])
    
    @classmethod
    def is_feature_enabled(cls, feature_name: str) -> bool:
        """
        Check if a specific feature is enabled.
        
        Args:
            feature_name: Name of the feature (e.g., "governance", "whitelist")
            
        Returns:
            True if feature is enabled, False otherwise
        """
        feature_map = {
            "governance": cls.ENABLE_GOVERNANCE,
            "parliament_governance": cls.ENABLE_PARLIAMENT_GOVERNANCE,
            "decision_review": cls.ENABLE_DECISION_REVIEW,
            "compliance_rules": cls.ENABLE_COMPLIANCE_RULES,
            "whitelist": cls.ENABLE_WHITELIST,
            "whitelist_approval": cls.ENABLE_WHITELIST_APPROVAL,
            "source_verification": cls.ENABLE_SOURCE_VERIFICATION,
            "layer1": cls.ENABLE_LAYER1_ENFORCEMENT,
            "genesis_tracking": cls.ENABLE_GENESIS_TRACKING,
            "audit_logging": cls.ENABLE_AUDIT_LOGGING,
            "data_isolation": cls.ENABLE_DATA_ISOLATION,
            "secure_ingestion": cls.ENABLE_SECURE_INGESTION,
            "content_hashing": cls.ENABLE_CONTENT_HASHING,
            "integrity_verification": cls.ENABLE_INTEGRITY_VERIFICATION,
            "ingestion_audit": cls.ENABLE_INGESTION_AUDIT,
        }
        
        return feature_map.get(feature_name.lower(), False)
    
    @classmethod
    def get_config_summary(cls) -> Dict[str, Any]:
        """
        Get a summary of all enterprise configuration.
        
        Returns:
            Dict with all configuration settings
        """
        return {
            "enterprise_mode": cls.ENTERPRISE_MODE,
            "industry_type": cls.INDUSTRY_TYPE.value,
            "features": {
                "governance": {
                    "enabled": cls.ENABLE_GOVERNANCE,
                    "parliament_governance": cls.ENABLE_PARLIAMENT_GOVERNANCE,
                    "decision_review": cls.ENABLE_DECISION_REVIEW,
                    "compliance_rules": cls.ENABLE_COMPLIANCE_RULES,
                },
                "whitelisting": {
                    "enabled": cls.ENABLE_WHITELIST,
                    "approval_required": cls.ENABLE_WHITELIST_APPROVAL,
                    "source_verification": cls.ENABLE_SOURCE_VERIFICATION,
                },
                "security": {
                    "layer1_enforcement": cls.ENABLE_LAYER1_ENFORCEMENT,
                    "genesis_tracking": cls.ENABLE_GENESIS_TRACKING,
                    "audit_logging": cls.ENABLE_AUDIT_LOGGING,
                    "data_isolation": cls.ENABLE_DATA_ISOLATION,
                },
                "ingestion": {
                    "secure_ingestion": cls.ENABLE_SECURE_INGESTION,
                    "content_hashing": cls.ENABLE_CONTENT_HASHING,
                    "integrity_verification": cls.ENABLE_INTEGRITY_VERIFICATION,
                    "audit_logging": cls.ENABLE_INGESTION_AUDIT,
                },
            },
            "industry_config": cls.get_industry_config(),
        }


# ============================================================================
# Convenience Functions
# ============================================================================

def is_enterprise_mode() -> bool:
    """Check if enterprise mode is enabled."""
    return EnterpriseConfig.ENTERPRISE_MODE


def get_industry_type() -> IndustryType:
    """Get current industry type."""
    return EnterpriseConfig.INDUSTRY_TYPE


def is_feature_enabled(feature_name: str) -> bool:
    """Check if a feature is enabled."""
    return EnterpriseConfig.is_feature_enabled(feature_name)
