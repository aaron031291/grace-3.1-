# Self-Healing Enhancement Implementation Plan

**Date:** 2025-01-27  
**Priority:** Implement top 5 critical gaps  
**Estimated Impact:** Increase coverage from 55% to 85%

---

## 🎯 Phase 1: Critical External Service Monitoring (Week 1)

### 1.1 Enhanced Qdrant Health Monitoring

**Current:** Basic connection check only  
**Enhancement:** Comprehensive health monitoring

**Implementation:**
```python
def _check_qdrant_health(self) -> Dict[str, Any]:
    """Comprehensive Qdrant health check."""
    health = {
        "connected": False,
        "collections": [],
        "collection_count": 0,
        "disk_usage": None,
        "query_performance": None,
        "index_health": [],
        "issues": []
    }
    
    try:
        from vector_db.client import get_qdrant_client
        qdrant = get_qdrant_client()
        
        if not qdrant.is_connected():
            health["issues"].append({
                "type": "connection_failure",
                "severity": "critical",
                "description": "Qdrant not connected"
            })
            return health
        
        health["connected"] = True
        
        # Check collections
        try:
            collections = qdrant.list_collections()
            health["collections"] = collections
            health["collection_count"] = len(collections)
            
            # Check each collection
            for collection in collections:
                try:
                    info = qdrant.client.get_collection(collection)
                    health["index_health"].append({
                        "collection": collection,
                        "points_count": info.points_count,
                        "indexed": info.indexed,
                        "status": "healthy" if info.indexed else "degraded"
                    })
                except Exception as e:
                    health["issues"].append({
                        "type": "collection_error",
                        "severity": "medium",
                        "collection": collection,
                        "description": str(e)
                    })
        except Exception as e:
            health["issues"].append({
                "type": "collection_list_error",
                "severity": "high",
                "description": str(e)
            })
        
        # Test query performance
        try:
            import time
            start = time.time()
            qdrant.client.scroll(collection_name=collections[0] if collections else "documents", limit=1)
            query_time = time.time() - start
            health["query_performance"] = {
                "test_query_time_ms": query_time * 1000,
                "status": "healthy" if query_time < 1.0 else "degraded"
            }
        except Exception as e:
            health["issues"].append({
                "type": "query_performance_test_failed",
                "severity": "medium",
                "description": str(e)
            })
            
    except Exception as e:
        health["issues"].append({
            "type": "health_check_error",
            "severity": "high",
            "description": str(e)
        })
    
    return health
```

---

### 1.2 Enhanced Ollama Health Monitoring

**Current:** Basic "is running" check  
**Enhancement:** Deep health monitoring

**Implementation:**
```python
def _check_ollama_health(self) -> Dict[str, Any]:
    """Comprehensive Ollama health check."""
    health = {
        "running": False,
        "models_loaded": [],
        "model_count": 0,
        "gpu_available": False,
        "gpu_memory": None,
        "response_time": None,
        "issues": []
    }
    
    try:
        from ollama_client.client import get_ollama_client
        client = get_ollama_client()
        
        if not client.is_running():
            health["issues"].append({
                "type": "service_not_running",
                "severity": "critical",
                "description": "Ollama service not running"
            })
            return health
        
        health["running"] = True
        
        # Check models
        try:
            models = client.get_all_models()
            health["models_loaded"] = [m.get("name", "unknown") for m in models]
            health["model_count"] = len(models)
            
            if not models:
                health["issues"].append({
                    "type": "no_models_loaded",
                    "severity": "high",
                    "description": "No models available in Ollama"
                })
        except Exception as e:
            health["issues"].append({
                "type": "model_list_error",
                "severity": "medium",
                "description": str(e)
            })
        
        # Test response time
        try:
            import time
            start = time.time()
            response = client.chat(
                model=health["models_loaded"][0] if health["models_loaded"] else "mistral:7b",
                messages=[{"role": "user", "content": "test"}],
                stream=False
            )
            response_time = time.time() - start
            health["response_time"] = {
                "test_response_time_ms": response_time * 1000,
                "status": "healthy" if response_time < 5.0 else "degraded"
            }
        except Exception as e:
            health["issues"].append({
                "type": "response_test_failed",
                "severity": "medium",
                "description": str(e)
            })
        
        # Check GPU (if available)
        try:
            import torch
            if torch.cuda.is_available():
                health["gpu_available"] = True
                health["gpu_memory"] = {
                    "total_gb": torch.cuda.get_device_properties(0).total_memory / 1e9,
                    "allocated_gb": torch.cuda.memory_allocated(0) / 1e9,
                    "cached_gb": torch.cuda.memory_reserved(0) / 1e9
                }
        except Exception:
            pass  # GPU check optional
            
    except Exception as e:
        health["issues"].append({
            "type": "health_check_error",
            "severity": "high",
            "description": str(e)
        })
    
    return health
```

---

### 1.3 Enhanced Embedding Model Health

**Implementation:**
```python
def _check_embedding_model_health(self) -> Dict[str, Any]:
    """Comprehensive embedding model health check."""
    health = {
        "model_loaded": False,
        "model_path": None,
        "model_exists": False,
        "gpu_memory": None,
        "batch_capability": None,
        "test_embedding": None,
        "issues": []
    }
    
    try:
        from embedding import get_embedding_model
        from settings import Settings
        
        health["model_path"] = Settings.EMBEDDING_MODEL_PATH
        health["model_exists"] = Path(Settings.EMBEDDING_MODEL_PATH).exists()
        
        if not health["model_exists"]:
            health["issues"].append({
                "type": "model_file_missing",
                "severity": "critical",
                "description": f"Embedding model not found at {health['model_path']}"
            })
            return health
        
        try:
            model = get_embedding_model()
            health["model_loaded"] = True
            
            # Test embedding generation
            try:
                test_text = "test embedding"
                embedding = model.embed_text([test_text])
                health["test_embedding"] = {
                    "success": True,
                    "dimension": len(embedding[0]) if embedding else 0,
                    "status": "healthy"
                }
            except Exception as e:
                health["issues"].append({
                    "type": "embedding_generation_failed",
                    "severity": "high",
                    "description": str(e)
                })
            
            # Check batch capability
            try:
                test_batch = ["test1", "test2", "test3"]
                batch_embeddings = model.embed_text(test_batch, batch_size=2)
                health["batch_capability"] = {
                    "success": True,
                    "batch_size_tested": 2,
                    "status": "healthy"
                }
            except Exception as e:
                health["issues"].append({
                    "type": "batch_processing_failed",
                    "severity": "medium",
                    "description": str(e)
                })
            
            # Check GPU memory
            try:
                import torch
                if torch.cuda.is_available():
                    health["gpu_memory"] = {
                        "allocated_gb": torch.cuda.memory_allocated(0) / 1e9,
                        "cached_gb": torch.cuda.memory_reserved(0) / 1e9
                    }
            except Exception:
                pass
                
        except Exception as e:
            health["issues"].append({
                "type": "model_loading_failed",
                "severity": "critical",
                "description": str(e)
            })
            
    except Exception as e:
        health["issues"].append({
            "type": "health_check_error",
            "severity": "high",
            "description": str(e)
        })
    
    return health
```

---

## 🎯 Phase 2: API Endpoint Health Monitoring (Week 2)

### 2.1 Endpoint Health Tracker

**Implementation:**
```python
class EndpointHealthTracker:
    """Track health of all API endpoints."""
    
    def __init__(self):
        self.endpoint_metrics = {}  # endpoint -> metrics
        self.endpoint_errors = {}   # endpoint -> error_count
    
    def track_request(self, endpoint: str, method: str, status_code: int, duration_ms: float):
        """Track API request."""
        key = f"{method} {endpoint}"
        if key not in self.endpoint_metrics:
            self.endpoint_metrics[key] = {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "avg_response_time_ms": 0.0,
                "max_response_time_ms": 0.0,
                "error_rate": 0.0
            }
        
        metrics = self.endpoint_metrics[key]
        metrics["total_requests"] += 1
        metrics["avg_response_time_ms"] = (
            (metrics["avg_response_time_ms"] * (metrics["total_requests"] - 1) + duration_ms) 
            / metrics["total_requests"]
        )
        metrics["max_response_time_ms"] = max(metrics["max_response_time_ms"], duration_ms)
        
        if status_code < 400:
            metrics["successful_requests"] += 1
        else:
            metrics["failed_requests"] += 1
            metrics["error_rate"] = metrics["failed_requests"] / metrics["total_requests"]
    
    def get_unhealthy_endpoints(self) -> List[Dict[str, Any]]:
        """Get endpoints with health issues."""
        unhealthy = []
        for endpoint, metrics in self.endpoint_metrics.items():
            issues = []
            
            if metrics["error_rate"] > 0.1:  # 10% error rate
                issues.append({
                    "type": "high_error_rate",
                    "severity": "high",
                    "error_rate": metrics["error_rate"]
                })
            
            if metrics["avg_response_time_ms"] > 5000:  # 5 seconds
                issues.append({
                    "type": "slow_response",
                    "severity": "medium",
                    "avg_time_ms": metrics["avg_response_time_ms"]
                })
            
            if issues:
                unhealthy.append({
                    "endpoint": endpoint,
                    "issues": issues,
                    "metrics": metrics
                })
        
        return unhealthy
```

---

## 🎯 Phase 3: Data Integrity Validation (Week 3)

### 3.1 Vector DB Sync Validation

**Implementation:**
```python
def _verify_vector_db_sync(self) -> Dict[str, Any]:
    """Verify vector database is in sync with SQL database."""
    sync_status = {
        "in_sync": True,
        "document_count_db": 0,
        "document_count_qdrant": 0,
        "missing_in_qdrant": [],
        "orphaned_in_qdrant": [],
        "issues": []
    }
    
    try:
        # Count documents in SQL database
        from models.database_models import Document
        db_count = self.session.query(Document).count()
        sync_status["document_count_db"] = db_count
        
        # Count vectors in Qdrant
        from vector_db.client import get_qdrant_client
        qdrant = get_qdrant_client()
        
        if qdrant.is_connected():
            collections = qdrant.list_collections()
            qdrant_count = 0
            for collection in collections:
                try:
                    info = qdrant.client.get_collection(collection)
                    qdrant_count += info.points_count
                except:
                    pass
            
            sync_status["document_count_qdrant"] = qdrant_count
            
            # Check for mismatches
            if abs(db_count - qdrant_count) > 10:  # Allow 10 document difference
                sync_status["in_sync"] = False
                sync_status["issues"].append({
                    "type": "count_mismatch",
                    "severity": "high",
                    "description": f"DB has {db_count} documents, Qdrant has {qdrant_count} vectors"
                })
        else:
            sync_status["issues"].append({
                "type": "qdrant_not_connected",
                "severity": "critical",
                "description": "Cannot verify sync - Qdrant not connected"
            })
            
    except Exception as e:
        sync_status["issues"].append({
            "type": "sync_check_error",
            "severity": "medium",
            "description": str(e)
        })
    
    return sync_status
```

---

### 3.2 Genesis Key Chain Integrity

**Implementation:**
```python
def _verify_genesis_chain_integrity(self) -> Dict[str, Any]:
    """Verify Genesis Key chain integrity."""
    integrity = {
        "chains_valid": True,
        "orphaned_keys": [],
        "broken_links": [],
        "circular_references": [],
        "missing_parents": [],
        "issues": []
    }
    
    try:
        from models.genesis_key_models import GenesisKey
        
        # Get all keys with parent references
        keys_with_parents = self.session.query(GenesisKey).filter(
            GenesisKey.parent_key_id.isnot(None)
        ).all()
        
        # Check each parent link
        parent_ids = {k.key_id for k in self.session.query(GenesisKey).all()}
        
        for key in keys_with_parents:
            if key.parent_key_id not in parent_ids:
                integrity["missing_parents"].append({
                    "key_id": key.key_id,
                    "parent_key_id": key.parent_key_id
                })
                integrity["chains_valid"] = False
        
        # Check for circular references (simple check)
        visited = set()
        for key in keys_with_parents:
            chain = []
            current = key
            while current and current.parent_key_id:
                if current.key_id in visited:
                    break
                visited.add(current.key_id)
                chain.append(current.key_id)
                if current.parent_key_id == key.key_id:  # Circular!
                    integrity["circular_references"].append({
                        "key_id": key.key_id,
                        "chain": chain
                    })
                    integrity["chains_valid"] = False
                    break
                current = self.session.query(GenesisKey).filter_by(
                    key_id=current.parent_key_id
                ).first()
        
        if integrity["missing_parents"] or integrity["circular_references"]:
            integrity["issues"].append({
                "type": "chain_integrity_issues",
                "severity": "medium",
                "missing_parents": len(integrity["missing_parents"]),
                "circular_refs": len(integrity["circular_references"])
            })
            
    except Exception as e:
        integrity["issues"].append({
            "type": "integrity_check_error",
            "severity": "medium",
            "description": str(e)
        })
    
    return integrity
```

---

## 📋 Quick Implementation Checklist

### Immediate (Add to `_run_diagnostics`):
- [ ] Add `_check_external_services_health()` method
- [ ] Add `_check_qdrant_health()` method  
- [ ] Add `_check_ollama_health()` method
- [ ] Add `_check_embedding_model_health()` method
- [ ] Integrate into diagnostic cycle

### Short Term:
- [ ] Add endpoint health tracking
- [ ] Add data integrity validation
- [ ] Add log file management
- [ ] Add thread/process monitoring

### Medium Term:
- [ ] Add security vulnerability scanning
- [ ] Add frontend build monitoring
- [ ] Add cache health monitoring
- [ ] Add configuration drift detection

---

## 🚀 Expected Outcomes

**After Phase 1-3 Implementation:**
- ✅ External service health: 40% → 90%
- ✅ API endpoint monitoring: 10% → 80%
- ✅ Data integrity: 50% → 85%
- ✅ Overall coverage: 55% → 85%

**Benefits:**
- Proactive issue detection
- Faster recovery times
- Better system reliability
- Reduced manual intervention

---

**Status:** 📋 PLAN READY FOR IMPLEMENTATION
