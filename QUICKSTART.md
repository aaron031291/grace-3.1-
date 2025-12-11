# Grace Chatbot - Quick Start Guide

A full-stack chatbot application with a modern React frontend and FastAPI backend powered by Ollama.

## Architecture Overview

```
┌─────────────────────┐
│   React Frontend    │
│  (ChatGPT-like UI)  │
└──────────┬──────────┘
           │ HTTP
           ▼
┌─────────────────────┐
│   FastAPI Backend   │
│   (Grace API)       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│      Ollama         │
│  (LLM Service)      │
└─────────────────────┘
```

## Prerequisites

- **Ollama**: Download from https://ollama.ai/
- **Python 3.8+**: For the backend
- **Node.js 16+**: For the frontend
- **Git**: For version control

## Installation & Setup

### 1. Setup Ollama

```bash
# Download and install Ollama from https://ollama.ai/
# Start Ollama service
ollama serve

# In another terminal, pull a model (e.g., Mistral)
ollama pull mistral
# or another model like llama2, neural-chat, etc.
```

### 2. Setup Backend

```bash
cd backend

# Create a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the API server
python app.py
# or
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

- API Docs: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`

### 3. Setup Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:5174` (or the port shown in terminal)

## Quick Usage

1. **Start Ollama**:

   ```bash
   ollama serve
   ```

2. **Start Backend** (in a new terminal):

   ```bash
   cd backend
   python app.py
   ```

3. **Start Frontend** (in another new terminal):

   ```bash
   cd frontend
   npm run dev
   ```

4. **Open the Frontend**:

   - Navigate to `http://localhost:5174` in your browser
   - You should see the Grace chatbot interface

5. **Create a Chat and Start Talking**:
   - Click the "+" button to create a new chat
   - Type your message and hit Enter
   - Wait for the AI response

## Features

### ✅ Implemented

- **Chat Interface**: ChatGPT-like UI with message history
- **Multiple Chats**: Create, rename, delete conversations
- **Chat Management**: Full CRUD operations
- **Real-time Messaging**: Send and receive messages
- **Health Monitoring**: See connection status
- **Message History**: Persistent storage in database
- **Settings**: Adjustable temperature and model parameters

### 🔜 Coming Soon

- **Document Upload**: RAG support
- **System Monitoring**: Performance metrics
- **Dark Mode**: Theme support
- **Message Search**: Find conversations
- **Export**: Download conversations

## File Structure

```
grace_3/
├── backend/
│   ├── app.py                 # Main FastAPI application
│   ├── requirements.txt        # Python dependencies
│   ├── settings.py            # Configuration
│   ├── database/               # Database layer
│   ├── models/                # Data models
│   ├── embedding/             # Embedding models
│   ├── ollama_client/         # Ollama integration
│   └── tests/                 # Unit tests
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx            # Main app component
│   │   ├── components/        # React components
│   │   ├── index.css          # Global styles
│   │   └── main.jsx           # Entry point
│   ├── package.json           # Node dependencies
│   ├── vite.config.js         # Vite configuration
│   └── README_CHATBOT.md      # Frontend documentation
│
└── README_QUICKSTART.md       # This file
```

## API Endpoints

### Chat Management

| Method | Endpoint      | Description       |
| ------ | ------------- | ----------------- |
| POST   | `/chats`      | Create new chat   |
| GET    | `/chats`      | List all chats    |
| GET    | `/chats/{id}` | Get specific chat |
| PUT    | `/chats/{id}` | Update chat       |
| DELETE | `/chats/{id}` | Delete chat       |

### Messages

| Method | Endpoint                        | Description                |
| ------ | ------------------------------- | -------------------------- |
| POST   | `/chats/{id}/messages`          | Add message                |
| GET    | `/chats/{id}/messages`          | Get history                |
| PUT    | `/chats/{id}/messages/{msg_id}` | Edit message               |
| DELETE | `/chats/{id}/messages/{msg_id}` | Delete message             |
| POST   | `/chats/{id}/prompt`            | Send prompt & get response |

### System

| Method | Endpoint  | Description  |
| ------ | --------- | ------------ |
| GET    | `/health` | Health check |
| GET    | `/`       | API info     |

## Configuration

### Backend Settings

Edit `backend/settings.py`:

- `OLLAMA_BASE_URL`: Ollama service URL (default: http://localhost:11434)
- `OLLAMA_LLM_DEFAULT`: Default model (default: mistral:7b)
- `MAX_NUM_PREDICT`: Max tokens in response (default: 2048)
- `DATABASE_URL`: Database connection string

### Frontend Configuration

The frontend automatically detects the API at `http://localhost:8000`. To change:

- Search for `http://localhost:8000` in `frontend/src/` files
- Update to your API URL

## Troubleshooting

### "Ollama service is not running"

- Make sure Ollama is running: `ollama serve`
- Check if it's accessible: `curl http://localhost:11434/api/tags`

### "Model not found"

- Pull the required model: `ollama pull mistral`
- Check available models: `ollama list`

### Port already in use

- Backend: Change port in `app.py` (default: 8000)
- Frontend: Vite will auto-detect the next available port

### Database errors

- Ensure database directory exists
- Check `backend/database/config.py` for database settings

### CORS errors

- Backend CORS is configured in `app.py`
- Ensure frontend URL matches allowed origins

## Development

### Backend Development

```bash
cd backend
python -m pytest  # Run tests
python -m black . # Format code
```

### Frontend Development

```bash
cd frontend
npm run lint      # Lint code
npm run build     # Build for production
npm run preview   # Preview production build
```

## Performance Tips

1. **Model Selection**: Smaller models (3B-7B) are faster but less capable

   - Fast: neural-chat (7B), mistral (7B)
   - Balanced: mistral-medium (14B)
   - Powerful: neural-chat-7b-v3 (7B but good quality)

2. **Temperature Settings**:

   - Lower (0.3-0.5): More consistent, logical responses
   - Higher (0.7-1.0): More creative, varied responses

3. **Batch Processing**: Send messages one at a time

## Security Notes

⚠️ **Important**: This is a development setup. For production:

- Set up proper authentication
- Enable HTTPS/TLS
- Use environment variables for secrets
- Implement rate limiting
- Add input validation
- Use a production database

## Getting Help

1. Check the **API Documentation**: http://localhost:8000/docs
2. Read component **README files**: Look in each directory
3. Check **browser console** for frontend errors (F12)
4. Check **backend logs** for API errors

## Next Steps

1. **Customize the UI**: Edit CSS in `frontend/src/components/`
2. **Add RAG Support**: Implement document upload in `RAGTab.jsx`
3. **Add Monitoring**: Implement metrics in `MonitoringTab.jsx`
4. **Deploy**: Follow deployment guides for your platform

## License

MIT

---

**Ready to chat? Start the services and visit http://localhost:5174!** 🚀
