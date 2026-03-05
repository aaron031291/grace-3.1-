# Genesis ID Login System - Complete Guide

## 🎯 Overview

The Genesis ID Login system assigns every user a unique Genesis ID (GU-prefix) that serves as their profile ID throughout the system. **Every single input and output** is tracked from the very first login and automatically saved to the knowledge base.

## 🔑 Key Features

✅ **Genesis ID as Profile ID** - Each user gets a unique GU-prefix ID for all tracking
✅ **Auto-Tracking from First Login** - All inputs/outputs tracked immediately
✅ **Auto-Population to Knowledge Base** - Saves to `knowledge_base/layer_1/genesis_key/`
✅ **Session Management** - Tracks user journeys with session IDs
✅ **Middleware Integration** - Automatic tracking of all API requests
✅ **No Registration Required** - Instant Genesis ID assignment
✅ **Complete History** - Full audit trail from day one

## 📁 Auto-Population Structure

All Genesis Keys are automatically saved to:

```
backend/knowledge_base/layer_1/genesis_key/
├── README.md                          # Folder documentation
├── GU-abc123.../                      # User folder (Genesis ID)
│   ├── profile.json                   # User profile
│   ├── session_SS-xyz789....json      # Session keys
│   ├── session_SS-def456....json      # Another session
│   └── keys_2026-01-11.json           # Date-based keys
├── GU-def456.../                      # Another user
│   └── ...
└── system/                            # System-generated keys
    └── ...
```

### What Gets Saved

**1. User Profile (`profile.json`)**
```json
{
  "user_id": "GU-abc123...",
  "username": "john_doe",
  "email": "john@example.com",
  "total_actions": 156,
  "total_errors": 3,
  "total_fixes": 2,
  "first_seen": "2026-01-11T10:00:00Z",
  "last_seen": "2026-01-11T15:30:00Z",
  "user_agent": "Mozilla/5.0...",
  "initial_ip": "192.168.1.1",
  "current_session_id": "SS-xyz789..."
}
```

**2. Session Keys (`session_SS-xyz....json`)**
```json
{
  "user_id": "GU-abc123...",
  "session_id": "SS-xyz789...",
  "created_at": "2026-01-11T10:00:00Z",
  "last_updated": "2026-01-11T15:30:00Z",
  "total_keys": 42,
  "keys": [
    {
      "key_id": "GK-...",
      "key_type": "api_request",
      "timestamp": "2026-01-11T10:05:00Z",
      "what": "API Request: POST /chat",
      "where": "/chat",
      "when": "2026-01-11T10:05:00Z",
      "why": "User action via POST request",
      "who": "GU-abc123...",
      "how": "HTTP POST",
      "input_data": {
        "message": "Hello, how are you?"
      },
      "output_data": {
        "response": "I'm doing well, thank you!"
      }
    }
  ]
}
```

## 🚀 How It Works

### 1. User Accesses Application

On first access, the system:

1. **Generates Genesis ID**: `GU-{16-char-hex}`
2. **Creates User Profile**: Saves to database and knowledge base
3. **Generates Session ID**: `SS-{16-char-hex}` for this session
4. **Sets Cookies**: Stores Genesis ID (1 year) and Session ID (24 hours)
5. **Creates Login Genesis Key**: Tracks the login event
6. **Auto-Saves to KB**: All data goes to `knowledge_base/layer_1/genesis_key/`

### 2. Middleware Tracks Every Request

The Genesis Key Middleware automatically:

1. **Captures Request**:
   - Method, path, headers, query params
   - Request body (for POST/PUT/PATCH)
   - Creates Genesis Key with input data

2. **Processes Request**:
   - Your API handles the request normally
   - No code changes needed

3. **Captures Response**:
   - Status code, headers, duration
   - Creates Genesis Key with output data
   - Links to request key (parent_key_id)

4. **Auto-Saves to KB**:
   - Both keys saved to user's folder
   - Grouped by session

### 3. Complete Input/Output Tracking

**Every interaction is tracked:**

```
User Types Message
↓
Genesis Key Created (Input)
- what: "User message input"
- input_data: {"message": "..."}
- key_type: "user_input"
↓
API Request
↓
Genesis Key Created (Request)
- what: "API Request: POST /chat"
- input_data: {method, path, body}
↓
System Processes
↓
Genesis Key Created (Response)
- what: "API Response: POST /chat [200]"
- output_data: {status, duration}
↓
User Receives Response
↓
All Keys Saved to KB Automatically
```

## 💻 Frontend Integration

### Using GenesisLogin Component

```jsx
import GenesisLogin from "./components/GenesisLogin";

function App() {
  const [genesisId, setGenesisId] = useState(null);

  const handleLogin = (id) => {
    setGenesisId(id);
    console.log("User logged in with Genesis ID:", id);
    // Now all requests will be tracked
  };

  return (
    <div>
      <GenesisLogin onLogin={handleLogin} />
      {/* Rest of your app */}
    </div>
  );
}
```

### Making Tracked API Calls

```javascript
// All requests automatically tracked by middleware
// Just include credentials to send Genesis ID cookie

fetch("http://localhost:8000/chat", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
  },
  credentials: "include", // Important: sends cookies
  body: JSON.stringify({
    message: "Hello!",
  }),
});

// Genesis Key automatically created for:
// 1. The request (input)
// 2. The response (output)
// 3. Auto-saved to knowledge_base/layer_1/genesis_key/{genesis_id}/
```

### Manual Genesis Key Creation

For custom tracking in your frontend:

```javascript
// Track a specific user action
await fetch("http://localhost:8000/genesis/keys", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
  },
  credentials: "include",
  body: JSON.stringify({
    key_type: "user_input",
    what_description: "User clicked export button",
    who_actor: genesisId,
    where_location: "Export Page",
    why_reason: "User wants to export data",
    how_method: "Button click",
    input_data: {
      button_id: "export-pdf",
      timestamp: new Date().toISOString(),
    },
    tags: ["ui_interaction", "export", "button_click"],
  }),
});
```

## 🔧 Backend Integration

### Using in Your Endpoints

```python
from fastapi import Request

@app.post("/your-endpoint")
async def your_endpoint(request: Request):
    # Genesis ID automatically available in request state
    genesis_id = request.state.genesis_id
    session_id = request.state.session_id

    # Your logic here
    result = process_data()

    # Everything is automatically tracked by middleware!
    return {"result": result}
```

### Manual Tracking

```python
from backend.genesis.genesis_key_service import get_genesis_service
from backend.models.genesis_key_models import GenesisKeyType

genesis = get_genesis_service()

# Track a custom operation
key = genesis.create_key(
    key_type=GenesisKeyType.DATABASE_CHANGE,
    what_description="Updated user preferences",
    who_actor=request.state.genesis_id,
    where_location="UserPreferencesService",
    why_reason="User changed theme to dark mode",
    how_method="Preferences API",
    user_id=request.state.genesis_id,
    session_id=request.state.session_id,
    input_data={"preference": "theme", "value": "dark"},
    output_data={"success": True}
)
# Automatically saved to knowledge base!
```

## 📊 API Endpoints

### Authentication

**POST /auth/login**
```json
{
  "username": "optional",
  "email": "optional"
}
```
Response:
```json
{
  "genesis_id": "GU-abc123...",
  "session_id": "SS-xyz789...",
  "username": "john_doe",
  "is_new_user": true,
  "message": "Welcome! You've been assigned Genesis ID: GU-abc123..."
}
```

**GET /auth/session**
```json
{
  "genesis_id": "GU-abc123...",
  "session_id": "SS-xyz789...",
  "username": "john_doe",
  "total_actions": 156,
  "total_errors": 3,
  "total_fixes": 2,
  "first_seen": "2026-01-11T10:00:00Z",
  "last_seen": "2026-01-11T15:30:00Z"
}
```

**GET /auth/whoami**
```json
{
  "genesis_id": "GU-abc123...",
  "username": "john_doe",
  "message": "You are john_doe"
}
```

**POST /auth/logout**
- Clears Genesis ID and Session ID cookies
- Creates logout Genesis Key

## 🎨 UI Components

### GenesisLogin Component

Features:
- Automatic session detection
- Optional username/email
- Instant Genesis ID assignment
- Real-time session statistics
- Logout functionality

### GenesisKeyPanel Component

Features:
- View all your Genesis Keys
- Filter by errors, fixes, etc.
- Double-click to view details
- One-click fix application
- Session history

## 📈 Tracking Examples

### Example 1: Complete User Journey

```
1. User visits site
   → Genesis ID created: GU-abc123...
   → Profile saved to KB
   → Login key created

2. User searches for "python tutorial"
   → Request key: API Request: GET /search?q=python+tutorial
   → Response key: API Response: GET /search [200]
   → Both saved to KB under GU-abc123.../session_SS-xyz...

3. User clicks a result
   → Key created: User clicked search result
   → Saved to KB

4. User uploads file
   → Request key: API Request: POST /upload
   → Response key: API Response: POST /upload [200]
   → File operation key created
   → All saved to KB

5. Error occurs
   → Error key created with details
   → Fix suggestion generated
   → Saved to KB

6. User applies fix
   → Fix key created
   → Original error updated
   → Saved to KB

7. User logs out
   → Logout key created
   → Session summary saved
```

### Example 2: Knowledge Base Contents

After the above journey, KB structure:

```
knowledge_base/layer_1/genesis_key/
└── GU-abc123.../
    ├── profile.json                    # User profile
    ├── session_SS-xyz789....json       # This session's keys
    │   Contains:
    │   - Login key
    │   - Search request/response keys
    │   - Click interaction key
    │   - Upload request/response keys
    │   - Error key
    │   - Fix key
    │   - Logout key
    └── keys_2026-01-11.json            # Date-based backup
```

## 🔒 Security & Privacy

1. **Genesis IDs are opaque** - No personal information in ID
2. **Cookies are HTTP-only** - Protected from XSS
3. **Optional user info** - Username/email not required
4. **Local storage** - All data stays in your knowledge base
5. **Full control** - Users can view/export their data anytime

## 🎯 Benefits

### For Users
- **Complete transparency** - See exactly what's being tracked
- **Full history** - Never lose track of your work
- **Error tracking** - All issues logged and fixable
- **Session recovery** - Pick up where you left off

### For Developers
- **Zero configuration** - Automatic tracking via middleware
- **Complete audit trail** - Full history of all actions
- **Error debugging** - Every error captured with context
- **User analytics** - Understand user behavior
- **Compliance** - Complete activity logs for auditing

### For AI/System
- **Complete context** - AI has full conversation history
- **Pattern recognition** - Learn from user behaviors
- **Personalization** - Tailor responses based on history
- **Continuous improvement** - Learn from errors and fixes

## 🚀 Getting Started

1. **Backend setup** (already done):
   - Genesis Key middleware added to app.py
   - Auth endpoints available
   - Auto-population to KB configured

2. **Frontend integration**:
   ```jsx
   import GenesisLogin from "./components/GenesisLogin";

   <GenesisLogin onLogin={(id) => console.log("Logged in:", id)} />
   ```

3. **Start tracking**:
   - User logs in → Gets Genesis ID
   - Makes any request → Automatically tracked
   - View in Genesis Key tab
   - Data in `knowledge_base/layer_1/genesis_key/`

## 📝 Summary

The Genesis ID Login system provides:

✅ **Instant profile creation** - No registration needed
✅ **Genesis ID as profile ID** - Unique identifier for each user
✅ **Complete input/output tracking** - Every action recorded
✅ **Auto-population to KB** - Saves to knowledge_base/layer_1/genesis_key/
✅ **Session management** - Track user journeys
✅ **Middleware automation** - Zero-config tracking
✅ **Full audit trail** - Complete history from day one

Start using Genesis IDs today and never miss a single user interaction!
