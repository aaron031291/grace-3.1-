# Genesis Key System - Setup & User Guide

## 🔑 Overview

The **Genesis Key System** is a comprehensive version control and tracking system that monitors every input, change, and action in your application. It provides:

- **Complete Tracking**: Tracks what, where, when, why, who, and how for every action
- **Error Detection**: Automatically detects code issues and highlights them
- **One-Click Fixes**: Provides intelligent fix suggestions like spell-check for code
- **Version Control Integration**: Links every change to Git commits with rollback capability
- **24-Hour Archival**: Automatically collects and archives keys daily with reports
- **User Profiles**: Tracks actions by user with Genesis-generated IDs
- **Double-Click Navigation**: Click any Genesis Key to view details or open version control

## 📦 Installation

### 1. Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

New dependencies added:
- `schedule` - For automated daily archival

### 2. Run Database Migration

Create the Genesis Key tables:

```bash
cd backend
python database/migrate_add_genesis_keys.py
```

This creates the following tables:
- `genesis_key` - Main tracking table
- `fix_suggestion` - Fix suggestions for errors
- `genesis_key_archive` - Daily archives
- `user_profile` - User tracking with Genesis IDs

### 3. Verify Installation

Check that the tables were created:

```bash
# The migration script will output:
# ✓ Genesis Key tables created successfully
#   - genesis_key
#   - fix_suggestion
#   - genesis_key_archive
#   - user_profile
```

## 🚀 Usage

### Frontend Access

1. Navigate to the RAG Tab in the application
2. Click the **🔑 Genesis Key** tab
3. You'll see:
   - Statistics dashboard
   - List of Genesis Keys
   - Recent archives
   - Error detection and fixes

### Creating Genesis Keys (Automatic)

Genesis Keys are created automatically when using the tracking system:

```python
from backend.genesis.genesis_key_service import get_genesis_service
from backend.models.genesis_key_models import GenesisKeyType

genesis = get_genesis_service()

# Create a key for tracking a user action
key = genesis.create_key(
    key_type=GenesisKeyType.USER_INPUT,
    what_description="User uploaded file",
    who_actor="user@example.com",
    where_location="File Upload Page",
    why_reason="Adding new document to knowledge base",
    how_method="Web interface upload",
    file_path="/path/to/file.pdf",
    user_id="GU-abc123",  # Genesis-generated user ID
    session_id="session-xyz"
)
```

### Using Context Manager (Recommended)

```python
with genesis.track_operation(
    GenesisKeyType.FILE_OPERATION,
    "file_upload",
    "user@example.com",
    user_id="GU-abc123"
) as key:
    # Your code here
    upload_file(file_path)
    # Automatically tracked with success/failure
```

### Code Analysis

Analyze code for errors and get fix suggestions:

```python
from backend.genesis.code_analyzer import get_code_analyzer

analyzer = get_code_analyzer()

# Analyze Python code
code = """
def hello()
    print("missing colon")
"""

issues = analyzer.analyze_python_code(code)

for issue in issues:
    print(f"{issue.severity}: {issue.message}")
    print(f"Suggested fix: {issue.suggested_fix}")
```

### Error Detection & Fixes

When an error is detected, Genesis Key automatically:

1. Creates an error Genesis Key
2. Analyzes the error
3. Generates fix suggestions
4. Provides one-click fix capability

From the frontend:
1. View errors in the **🚨 Errors Only** filter
2. Double-click an error key to see details
3. Click **✨ Apply Fix** for one-click solution
4. The fix is applied and tracked with a new Genesis Key

### Version Control & Rollback

Every Genesis Key can link to a Git commit:

1. **View Version History**: Double-click a key with a commit SHA to open version control
2. **Rollback**: Click **🔄 Rollback** to revert to that state
3. **Track Changes**: All rollbacks create new Genesis Keys for auditing

### Daily Archival

Genesis Keys are automatically archived every 24 hours:

**Automatic**: Runs at 2:00 AM daily
- Collects all keys from the previous day
- Generates comprehensive report
- Stores in `backend/genesis_archives/YYYY-MM-DD/`

**Manual**: Trigger archival anytime:
1. Click **📦 Archive Now** button in UI
2. Or call API: `POST /genesis/archive/trigger`

Each archive includes:
- JSON file with all keys
- Human-readable text report
- Detailed statistics
- Tracking summary (what, where, when, why, who, how)

### User Profiles

Genesis Keys use user profiles for tracking:

```python
# Get or create user profile
user = genesis.get_or_create_user(
    username="john_doe",
    email="john@example.com"
)

# User gets Genesis-generated ID: GU-abc123...
# Use this ID for all operations
```

User profiles track:
- Total actions
- Total changes
- Total errors
- Total fixes
- First and last seen timestamps

## 📊 API Endpoints

### Genesis Keys

- `POST /genesis/keys` - Create a Genesis Key
- `GET /genesis/keys` - List keys (with filters)
- `GET /genesis/keys/{key_id}` - Get specific key
- `GET /genesis/keys/{key_id}/metadata` - Get human/AI metadata
- `POST /genesis/keys/{key_id}/rollback` - Rollback to key state

### Code Analysis

- `POST /genesis/analyze-code` - Analyze code for errors
- `GET /genesis/keys/{key_id}/fixes` - Get fix suggestions
- `POST /genesis/fixes/{suggestion_id}/apply` - Apply a fix

### Users

- `POST /genesis/users` - Create/get user profile
- `GET /genesis/users/{user_id}` - Get user profile
- `GET /genesis/users/{user_id}/keys` - Get user's keys

### Archives

- `POST /genesis/archive/trigger` - Trigger archival
- `GET /genesis/archives` - List archives
- `GET /genesis/archives/{archive_id}` - Get specific archive
- `GET /genesis/archives/{archive_id}/report` - Get archive report

### Statistics

- `GET /genesis/stats` - Get overall statistics

## 🎯 Key Features

### 1. Complete Tracking (What, Where, When, Why, Who, How)

Every Genesis Key captures:

- **WHAT**: What action was performed
- **WHERE**: Location in code/system
- **WHEN**: Timestamp of action
- **WHY**: Reason/purpose for the action
- **WHO**: Actor (user, system, process)
- **HOW**: Method/mechanism used

### 2. Error Highlighting

Like spell-check for code:
- **Syntax Errors**: Missing colons, parentheses, etc.
- **Logic Issues**: Bare except clauses, mutable defaults
- **Style Issues**: Line length, trailing whitespace
- **Anti-Patterns**: print statements, console.log, var usage

### 3. Fix Suggestions

Each error gets:
- **Type**: syntax, logic, style, etc.
- **Severity**: low, medium, high, critical
- **Description**: Clear explanation
- **Fix Code**: Exact code to apply
- **Confidence Score**: AI confidence (0-1)
- **One-Click Apply**: Apply fix instantly

### 4. Version Control Integration

- Links to Git commits
- Shows commit SHA in key
- Rollback to any previous state
- Tracks all version changes
- Integrates with existing Git service

### 5. Daily Archives & Reports

Archives include:
- Total keys, errors, fixes
- Most active user
- Most changed file
- Most common error
- Type breakdown
- Time distribution
- Full tracking summary

### 6. Double-Click Navigation

- **With Commit**: Opens version control module
- **Without Commit**: Shows detailed metadata
- **Error Keys**: Shows available fixes
- **Quick Actions**: Rollback, apply fix, view details

## 📁 File Structure

```
backend/
├── genesis/
│   ├── __init__.py
│   ├── genesis_key_service.py    # Main service
│   ├── code_analyzer.py          # Error detection
│   └── archival_service.py       # Daily archival
├── models/
│   └── genesis_key_models.py     # Database models
├── api/
│   └── genesis_keys.py           # API endpoints
├── database/
│   └── migrate_add_genesis_keys.py  # Migration
└── genesis_archives/             # Archive storage
    └── YYYY-MM-DD/
        ├── genesis_keys_YYYY-MM-DD.json
        ├── report_YYYY-MM-DD.txt
        └── data_YYYY-MM-DD.json

frontend/
└── src/
    └── components/
        ├── GenesisKeyPanel.jsx   # Main UI
        └── GenesisKeyPanel.css   # Styles
```

## 🔧 Configuration

### Enable Automatic Archival

Add to your app startup (in `app.py` or similar):

```python
from backend.genesis.archival_service import schedule_daily_archival

# On startup
@app.on_event("startup")
async def startup_event():
    schedule_daily_archival()
```

### Customize Archive Path

```python
from backend.genesis.archival_service import ArchivalService

archival = ArchivalService(
    archive_base_path="/custom/path/to/archives"
)
```

### User ID Generation

Genesis Keys automatically generate user IDs:

- **From Identifier**: `GU-<hash_of_email>`
- **Random**: `GU-<random_hex>`

Use consistent identifiers (email/username) for same user.

## 📈 Best Practices

### 1. Use Context Managers

Always prefer context managers for automatic tracking:

```python
with genesis.track_operation(...) as key:
    # Your code
    pass  # Automatically tracks success/failure
```

### 2. Provide Why/How

Always include `why_reason` and `how_method` for better tracking:

```python
genesis.create_key(
    key_type=GenesisKeyType.CODE_CHANGE,
    what_description="Updated authentication logic",
    who_actor="developer@example.com",
    why_reason="Fix security vulnerability CVE-2024-1234",
    how_method="Manual code edit in IDE"
)
```

### 3. Tag Important Keys

Use tags for searchability:

```python
genesis.create_key(
    ...,
    tags=["security", "authentication", "critical", "prod"]
)
```

### 4. Review Archives Regularly

- Check daily archives for patterns
- Monitor error trends
- Review fix application rates
- Track user activity

### 5. Use Filters

In the UI, use filters to focus on:
- Errors only
- Fixes only
- Specific users
- Specific file paths

## 🐛 Troubleshooting

### Tables Not Created

```bash
# Re-run migration
python backend/database/migrate_add_genesis_keys.py
```

### Archives Not Working

Check that scheduler is started:

```python
# In app.py
schedule_daily_archival()
```

### Frontend Not Showing Keys

1. Check API is running: `http://localhost:8000/genesis/stats`
2. Check CORS settings in backend
3. Verify Genesis Key tab is visible in RAG Tab

### Rollback Failed

- Ensure Git service is initialized
- Check commit SHA exists in repository
- Verify user has Git permissions

### Qdrant upsert returns 400 (genesis_keys)

If you see `FLAG_FOR_HUMAN: [genesis_qdrant_400] Qdrant upsert (genesis_keys) returns 400`:

1. **Vector size**: The `genesis_keys` collection in Qdrant Cloud must use the same vector size as the backend. If you leave `GENESIS_VECTOR_SIZE` **unset** in `.env`, the backend uses the embedding model's dimension (e.g. 384 for `all-MiniLM-L6-v2`), so it stays in sync. If the collection already exists with a different size, set `GENESIS_VECTOR_SIZE` to that size (e.g. `GENESIS_VECTOR_SIZE=384`), or drop and recreate the collection so the backend can create it with the correct size.
2. **Collection schema**: If the collection already exists with a different size, either drop and recreate it (backend will recreate with the effective vector size on first push) or set `GENESIS_VECTOR_SIZE` to match the existing collection.
3. **Payload**: Backend sends payload keys: `gk_id`, `genesis_key_id`, `key_type`, `type`, `what`, `where`, `tags`, `timestamp`. Ensure the collection does not enforce a stricter payload schema that rejects these.
4. **Temporarily disable Qdrant push**: Set `DISABLE_GENESIS_QDRANT_PUSH=1` in `.env` to stop pushing Genesis keys to Qdrant (stops 400s and genesis_qdrant health alerts until the collection is fixed).

## 📚 Example Workflows

### Workflow 1: Track File Upload

```python
genesis = get_genesis_service()

user = genesis.get_or_create_user(email="user@example.com")

with genesis.track_operation(
    GenesisKeyType.FILE_OPERATION,
    "file_upload",
    user.username,
    user_id=user.user_id,
    why_reason="Adding training document"
) as key:
    upload_result = process_file(file_path)
```

### Workflow 2: Error Detection & Fix

```python
# Analyze code
analyzer = get_code_analyzer()
issues = analyzer.analyze_python_code(code, file_path)

# Create Genesis Key for each issue
for issue in issues:
    key = genesis.create_key(
        key_type=GenesisKeyType.ERROR,
        what_description=f"Error: {issue.message}",
        who_actor="Code Analyzer",
        file_path=file_path,
        line_number=issue.line_number,
        is_error=True,
        error_type=issue.issue_type,
        error_message=issue.message
    )

    # Create fix suggestion
    if issue.suggested_fix:
        genesis.create_fix_suggestion(
            genesis_key_id=key.key_id,
            suggestion_type=issue.issue_type,
            title=f"Fix {issue.issue_type}",
            description=issue.message,
            severity=issue.severity,
            fix_code=issue.suggested_fix,
            confidence=issue.fix_confidence
        )
```

### Workflow 3: Daily Archive Review

```python
from backend.genesis.archival_service import get_archival_service
from datetime import datetime, timedelta

archival = get_archival_service()

# Get yesterday's archive
yesterday = datetime.utcnow() - timedelta(days=1)
archive = archival.get_archive_for_date(yesterday)

if archive:
    print(f"Keys archived: {archive.key_count}")
    print(f"Errors detected: {archive.error_count}")
    print(f"Fixes applied: {archive.fix_count}")
    print(f"\nReport:\n{archive.report_summary}")
```

## 🎉 Summary

The Genesis Key System provides:

✅ **Complete transparency** - Track every action
✅ **Error prevention** - Detect issues before deployment
✅ **Quick fixes** - One-click solutions for common problems
✅ **Version control** - Full rollback capability
✅ **Automated reporting** - Daily insights and trends
✅ **User tracking** - Know who did what, when, and why
✅ **Easy integration** - Simple API and UI

Start using Genesis Keys today to gain complete visibility into your system!

## 📞 Support

For issues or questions:
1. Check the error logs in `backend/logs/`
2. Review archive reports for patterns
3. Use the statistics dashboard for insights
4. Check API documentation at `http://localhost:8000/docs`
