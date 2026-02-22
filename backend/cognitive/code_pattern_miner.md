# code_pattern_miner

Code Pattern Miner - Extracts actionable coding knowledge from source code.

## Location
`cognitive/code_pattern_miner.py`

## Classes
- **CodePatternMiner**: Mines source code into actionable patterns a coding agent can use.

## Methods
- `mine_codebase(root_path)` - Mine all .py files for function signatures, class patterns, error handling
- `mine_framework_patterns()` - Store framework-specific patterns (FastAPI, SQLAlchemy, Qdrant, pytest, Pydantic)
- `mine_error_solutions()` - Store common error-solution pairs
- `get_stats()` - Return mining statistics

## Functions
- `get_code_pattern_miner()` - Singleton accessor
