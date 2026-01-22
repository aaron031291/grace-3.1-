# GRACE Project Setup Guide

Complete setup instructions for the GRACE project including database migrations.

## Prerequisites

### Required

- **Python 3.10+** - [Download](https://www.python.org/downloads/)
- **Node.js 18+** - [Download](https://nodejs.org/)
- **Git** - [Download](https://git-scm.com/)

### Optional (for development)

- **Ollama** - For local LLM support
- **Git GUI** - For easier version control

## Installation Steps

### 1. Clone the Repository

```bash
git clone <repository-url>
cd grace_3
```

### 2. Backend Setup

#### Install Python Dependencies

```bash
cd backend

# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### Run Database Migrations

**Windows:**

```bash
run_migrations.bat
```

**Linux/macOS:**

```bash
./run_migrations.sh
```

**Any Platform:**

```bash
python run_all_migrations.py
```

Expected output:

```
✓ PASSED: Base Tables
✓ PASSED: Metadata Columns
✓ PASSED: Folder Path
✓ PASSED: Confidence Scoring
✓ PASSED: Database Verification

✓ All migrations completed successfully!
```

#### Start the Backend Server

```bash
python app.py
```

Backend will be available at: `http://localhost:5000`

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will be available at: `http://localhost:5174`

### 4. Verify Installation

- ✅ Backend running at http://localhost:5000
- ✅ Frontend running at http://localhost:5174
- ✅ Database created at `backend/data/grace.db`
- ✅ Can see Documents tab with Notion kanban board

## Project Structure

```
grace_3/
├── backend/                    # Python backend
│   ├── run_all_migrations.py  # Migration orchestrator
│   ├── run_migrations.bat     # Windows migration script
│   ├── run_migrations.sh      # Linux/macOS migration script
│   ├── app.py                 # Main server
│   ├── data/
│   │   └── grace.db           # SQLite database (auto-created)
│   ├── database/              # Database layer
│   ├── api/                   # REST API endpoints
│   ├── models/                # Data models
│   └── requirements.txt        # Python dependencies
│
├── frontend/                   # React frontend
│   ├── src/
│   │   ├── components/        # React components
│   │   │   ├── NotionTab.jsx  # Kanban board
│   │   │   ├── RAGTab.jsx     # Documents interface
│   │   │   └── ...
│   │   ├── App.jsx            # Main app
│   │   └── index.css          # Styles
│   ├── package.json           # Node.js dependencies
│   └── vite.config.js         # Vite configuration
│
└── docs/                       # Documentation
```

## Database

### Location

`backend/data/grace.db` (SQLite)

### Tables Created

- `users` - User accounts
- `conversations` - Chat conversations
- `messages` - Individual messages
- `chats` - Chat sessions
- `chat_history` - Chat history records
- `documents` - Uploaded documents
- `document_chunks` - Document chunks for RAG
- `embeddings` - Vector embeddings

### Reset Database (if needed)

```bash
cd backend
python clear_all_data.py
python run_all_migrations.py  # or run_migrations.bat
```

## Environment Variables

### Backend (.env)

```
DATABASE_URL=sqlite:///./data/grace.db
DEBUG=True
LOG_LEVEL=INFO

# Optional: GitHub Personal Access Token for cloning repositories
# Generate at: https://github.com/settings/tokens
# Required scopes: 'public_repo' or 'repo'
GITHUB_TOKEN=
```

See `.env.example` for all options.

## Common Tasks

### Check Backend Status

```bash
# Check if backend is running
curl http://localhost:5000/health
```

### Check Frontend Status

```bash
# Open browser to http://localhost:5174
# Should see login/signup page
```

### View Database

```bash
cd backend

# Windows:
python -m sqlite3 data/grace.db

# Linux/macOS:
sqlite3 data/grace.db
```

### Restart Services

**Backend:**

```bash
# Stop: Ctrl+C in terminal
# Start: python app.py
```

**Frontend:**

```bash
# Stop: Ctrl+C in terminal
# Start: npm run dev
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'xxx'"

```bash
cd backend
pip install -r requirements.txt
```

### "Port already in use"

```bash
# Backend (5000)
lsof -i :5000
kill -9 <PID>

# Frontend (5174)
lsof -i :5174
kill -9 <PID>
```

### Database migration fails

```bash
cd backend
rm -rf data/grace.db
python run_all_migrations.py  # or run_migrations.bat
```

### Frontend not loading

```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

## Development Workflow

1. **Start Backend**

   ```bash
   cd backend
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   python app.py
   ```

2. **Start Frontend** (in another terminal)

   ```bash
   cd frontend
   npm run dev
   ```

3. **Make Changes**

   - Backend changes auto-reload (if debug enabled)
   - Frontend hot-reloads automatically

4. **Run Tests**
   ```bash
   cd backend
   python -m pytest
   ```

## Building for Production

### Backend

```bash
cd backend
# Set DEBUG=False in .env
python app.py --no-debug
```

### Frontend

```bash
cd frontend
npm run build
# Output in: frontend/dist/
```

## Documentation

- **Migrations**: See `MIGRATIONS.md` or `MIGRATION_QUICK_REFERENCE.md`
- **API**: Backend endpoints documented in `backend/docs/`
- **Components**: Frontend components in `frontend/src/components/`
- **Database**: Schema in `backend/models/database_models.py`

## Support & Help

For issues:

1. Check the relevant README files
2. Review the error logs in console
3. Check existing issues/documentation
4. Run migrations again if database seems corrupted

## Next Steps

After setup:

1. Create a user account
2. Explore the Documents tab (with Kanban board)
3. Try uploading documents
4. Test the chat interface
5. Review the admin panel

---

**Setup Complete!** 🎉 Your GRACE instance is ready to use.
