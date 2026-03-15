#!/usr/bin/env python3
"""
Export FastAPI OpenAPI schema to frontend/public/api-schema.json

Run from backend/:
    python scripts/export_openapi.py

This auto-generates the API contract that the frontend useTabData() hook
can validate against at runtime.
"""

import json
import sys
import os

# Ensure backend/ is on the path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

def main():
    # Suppress noisy startup logs
    os.environ.setdefault("DISABLE_GENESIS_TRACKING", "true")
    
    from app import app
    
    schema = app.openapi()
    
    # Write to frontend/public/
    out_dir = os.path.join(backend_dir, "..", "frontend", "public")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "api-schema.json")
    
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, default=str)
    
    # Summary
    paths = schema.get("paths", {})
    schemas_count = len(schema.get("components", {}).get("schemas", {}))
    print(f"✓ Exported OpenAPI schema")
    print(f"  Endpoints: {len(paths)}")
    print(f"  Schemas:   {schemas_count}")
    print(f"  Output:    {os.path.abspath(out_path)}")


if __name__ == "__main__":
    main()
