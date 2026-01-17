# Enterprise Genesis Key Storage System

## 🎯 Overview

**Enterprise-grade storage solution for Genesis Keys designed to scale to 100,000+ keys while working within PC resource limits.**

### Key Features:

1. **Smart Indexing & Querying** - Fast queries with optimized indexes
2. **Intelligent Caching** - LRU cache for frequently accessed keys
3. **Compression** - Compress old keys to reduce storage
4. **Archiving** - Archive very old keys to files
5. **Lifecycle Management** - Automatic compression and archiving
6. **Resource-Aware Design** - Optimized for PC limits
7. **Bulk Operations** - Efficient bulk create and archive
8. **Analytics & Health** - Statistics and health monitoring

---

## 🏗️ Architecture

### Storage Tiers:

```
ACTIVE (Database)     → Most recent 10,000 keys
  ↓ (90 days)
COMPRESSED (Database) → Compressed old keys
  ↓ (365 days)
ARCHIVED (Files)      → Archived to JSON.gz files
  ↓ (very old)
FROZEN (Long-term)    → Long-term storage (rarely accessed)
```

### Cache System:

- **In-Memory LRU Cache** - Stores 1,000 most recently accessed keys
- **Access Tracking** - Tracks access frequency and recency
- **Automatic Eviction** - Evicts least recently used keys

---

## 📊 Storage Capacity

### Current Configuration:

- **Active Keys:** Up to 10,000 keys in main database
- **Compressed Keys:** Unlimited (in database, compressed)
- **Archived Keys:** Unlimited (in files, ~1KB each)
- **Cache Size:** 1,000 keys (configurable)

### Estimated Storage for 100,000 Keys:

| Tier | Keys | Size per Key | Total Size |
|------|------|--------------|------------|
| Active | 10,000 | ~10 KB | ~100 MB |
| Compressed | 30,000 | ~2 KB | ~60 MB |
| Archived | 60,000 | ~1 KB | ~60 MB |
| **Total** | **100,000** | **-** | **~220 MB** |

**Well within PC limits!**

---

## 🚀 Usage

### Basic Usage:

```python
from backend.genesis.enterprise_genesis_storage import get_enterprise_genesis_storage
from backend.database.session import get_session

# Get storage instance
session = next(get_session())
storage = get_enterprise_genesis_storage(session, cache_size=1000)

# Get a key (with caching)
key = storage.get_key_smart("key-id-123")

# Search keys
keys, total = storage.search_keys(
    query_text="code change",
    key_type=GenesisKeyType.CODE_CHANGE,
    limit=1000
)

# Get keys by type
keys = storage.get_keys_by_type(GenesisKeyType.USER_INPUT, limit=1000)

# Manage lifecycle (compress and archive)
results = storage.manage_lifecycle()
print(f"Compressed: {results['compressed']}, Archived: {results['archived']}")

# Get statistics
stats = storage.get_statistics()
print(f"Total keys: {stats['total_keys']}")
print(f"Cache hit rate: {stats['cache_hit_rate']:.2%}")
```

### API Usage:

```bash
# Get a key
GET /api/enterprise/genesis/key/{key_id}

# Search keys
POST /api/enterprise/genesis/search
{
  "query_text": "code change",
  "key_type": "code_change",
  "limit": 1000
}

# Get keys by type
GET /api/enterprise/genesis/by-type/{key_type}?limit=1000

# Get keys by file
GET /api/enterprise/genesis/by-file/{file_path}?limit=1000

# Manage lifecycle
POST /api/enterprise/genesis/lifecycle/manage?force=false

# Get statistics
GET /api/enterprise/genesis/statistics

# Get health metrics
GET /api/enterprise/genesis/health

# Clear cache
POST /api/enterprise/genesis/cache/clear
```

---

## ⚙️ Configuration

### Initialization Options:

```python
storage = EnterpriseGenesisStorage(
    session=session,
    archive_path=Path("backend/data/genesis_archive"),  # Archive directory
    cache_size=1000,                                     # Cache size
    compress_after_days=90,                              # Compress after 90 days
    archive_after_days=365,                              # Archive after 365 days
    max_active_keys=10000                                # Max active keys
)
```

### Recommended Settings for PC:

- **cache_size:** 500-2000 (based on available RAM)
- **compress_after_days:** 90 (compress after 3 months)
- **archive_after_days:** 365 (archive after 1 year)
- **max_active_keys:** 5000-10000 (based on database size)

---

## 🔧 Lifecycle Management

### Automatic Lifecycle:

The system automatically manages the lifecycle of Genesis Keys:

1. **Active** (0-90 days) - In main database, uncompressed
2. **Compressed** (90-365 days) - In database, compressed
3. **Archived** (365+ days) - In files, JSON.gz format
4. **Frozen** (very old) - Long-term storage

### Manual Lifecycle Management:

```python
# Run lifecycle management
results = storage.manage_lifecycle(force=True)

# Results:
# {
#   "compressed": 150,
#   "archived": 30,
#   "errors": []
# }
```

### Lifecycle Triggers:

- **Automatic:** Run during maintenance windows
- **Manual:** Call `manage_lifecycle()` when needed
- **Scheduled:** Run via cron/scheduled task

---

## 📈 Performance Optimization

### Indexes:

The system uses optimized indexes for fast queries:

- `idx_key_type_status` - Filter by type and status
- `idx_user_session` - Filter by user and session
- `idx_error_fix` - Filter errors and fixes
- `idx_timestamp` - Order by timestamp
- `idx_file_path` - Filter by file path

### Query Optimization:

- **Pagination** - All queries support pagination
- **Filtering** - Multiple filters in single query
- **Caching** - Frequently accessed keys cached
- **Bulk Operations** - Efficient bulk create/archive

### Cache Strategy:

- **LRU Eviction** - Least recently used keys evicted first
- **Access Tracking** - Tracks access frequency
- **Warm-up** - Cache warmed on query results

---

## 📊 Analytics & Health

### Statistics:

```python
stats = storage.get_statistics()

# Returns:
# {
#   "total_keys": 45000,
#   "active_keys": 8000,
#   "compressed_keys": 25000,
#   "archived_keys": 12000,
#   "cached_keys": 1000,
#   "cache_hit_rate": 0.75,
#   "storage_estimates": {
#     "active_mb": 80.0,
#     "compressed_mb": 50.0,
#     "archived_mb": 12.0,
#     "total_mb": 142.0
#   }
# }
```

### Health Metrics:

```python
health = storage.get_health_metrics()

# Returns:
# {
#   "health_score": 0.82,
#   "health_status": "excellent",
#   "cache_efficiency": 0.75,
#   "storage_efficiency": 0.18,
#   "recommendations": [
#     "Consider archiving more old keys"
#   ]
# }
```

---

## 🔍 Query Examples

### Search by Text:

```python
keys, total = storage.search_keys(
    query_text="database error",
    limit=100
)
```

### Search by Type:

```python
keys = storage.get_keys_by_type(
    GenesisKeyType.ERROR,
    limit=1000
)
```

### Search by File:

```python
keys = storage.get_keys_by_file_path(
    "backend/app.py",
    limit=500
)
```

### Search by User:

```python
keys = storage.get_keys_by_user(
    "user-123",
    limit=1000
)
```

### Complex Search:

```python
keys, total = storage.search_keys(
    query_text="code change",
    key_type=GenesisKeyType.CODE_CHANGE,
    file_path="backend/app.py",
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 12, 31),
    limit=1000,
    offset=0
)
```

---

## 🛡️ Resource Management

### PC-Friendly Design:

1. **Limited Active Keys** - Only 10,000 most recent in main table
2. **Compression** - Old keys compressed to reduce size
3. **Archiving** - Very old keys archived to files
4. **Caching** - In-memory cache limited to 1,000 keys
5. **Batch Processing** - Bulk operations in batches

### Memory Usage:

- **Cache:** ~10 MB (1,000 keys × ~10 KB)
- **Active Keys:** ~100 MB (10,000 keys × ~10 KB)
- **Compressed Keys:** ~60 MB (30,000 keys × ~2 KB)
- **Total Database:** ~160 MB

### Disk Usage:

- **Database:** ~160 MB (active + compressed)
- **Archived Files:** ~60 MB (60,000 keys × ~1 KB)
- **Total:** ~220 MB for 100,000 keys

**Very efficient for PC usage!**

---

## 🔄 Integration

### With Genesis Key Service:

```python
from backend.genesis.genesis_key_service import get_genesis_service
from backend.genesis.enterprise_genesis_storage import get_enterprise_genesis_storage

# Create keys via service
genesis_service = get_genesis_service(session)
key = genesis_service.create_key(...)

# Query via enterprise storage
storage = get_enterprise_genesis_storage(session)
keys = storage.search_keys(...)
```

### With Startup Sequence:

```python
from backend.genesis.enterprise_genesis_storage import get_enterprise_genesis_storage

# In startup, initialize storage
storage = get_enterprise_genesis_storage(session)

# Run lifecycle management periodically
storage.manage_lifecycle()
```

---

## 📝 Summary

**Enterprise Genesis Key Storage provides:**

✅ **Scalable** - Handles 100,000+ keys  
✅ **Efficient** - ~220 MB for 100k keys  
✅ **Fast** - Smart indexing and caching  
✅ **Resource-Aware** - Optimized for PC limits  
✅ **Automatic** - Lifecycle management  
✅ **Analytics** - Statistics and health monitoring  

**Perfect for enterprise-scale Genesis Key storage within PC resource limits!**
