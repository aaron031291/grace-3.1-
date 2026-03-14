#!/bin/bash
# Qdrant Storage Monitor
# Usage: ./check_qdrant.sh

echo "=== Qdrant Storage Status ==="
echo "Time: $(date)"
echo ""

# Check if Qdrant is running
if ! curl -s http://localhost:6333 > /dev/null 2>&1; then
    echo "❌ Qdrant is not running"
    exit 1
fi

echo "✅ Qdrant is running"
echo ""

# Get collection info
echo "Collection: documents"
COLLECTION_INFO=$(curl -s http://localhost:6333/collections/documents 2>/dev/null)

if echo "$COLLECTION_INFO" | grep -q '"result"'; then
    POINTS=$(echo "$COLLECTION_INFO" | jq -r '.result.points_count // 0')
    VECTORS=$(echo "$COLLECTION_INFO" | jq -r '.result.indexed_vectors_count // 0')
    DIMENSION=$(echo "$COLLECTION_INFO" | jq -r '.result.config.params.vectors.size // "N/A"')
    STATUS=$(echo "$COLLECTION_INFO" | jq -r '.result.status // "unknown"')
    
    echo "  Status: $STATUS"
    echo "  Points: $POINTS"
    echo "  Indexed Vectors: $VECTORS"
    echo "  Vector Dimension: $DIMENSION"
else
    echo "  ⚠️  Collection does not exist"
fi

echo ""

# Check disk usage
if [ -d "qdrant_storage" ]; then
    DISK_USAGE=$(du -sh qdrant_storage/ 2>/dev/null | cut -f1)
    echo "Disk Usage: $DISK_USAGE"
else
    echo "Disk Usage: N/A (storage directory not found)"
fi

echo ""
echo "==========================="
