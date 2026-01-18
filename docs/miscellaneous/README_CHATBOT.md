# Grace Chatbot Frontend

A modern ChatGPT-like frontend for the Grace AI chatbot API, built with React and Vite.

## Features

### 🗨️ Chat Tab

- **Real-time Chat**: Send and receive messages from the LLM
- **Chat History**: View all past conversations
- **Multiple Chats**: Create and manage multiple chat sessions
- **Chat Management**:
  - Create new chats
  - Rename chats
  - Delete chats
  - View chat metadata (model, temperature)
- **Message History**: Full conversation history with timestamps
- **Auto-scroll**: Automatically scrolls to the latest message

### 📄 Documents Tab (Coming Soon)

- Upload documents for RAG (Retrieval-Augmented Generation)
- Manage uploaded documents
- Configure RAG parameters

### 📊 Monitoring Tab (Coming Soon)

- System health monitoring
- API status
- Performance metrics
- Resource usage

## Project Structure

```
src/
├── App.jsx                 # Main app component with routing
├── App.css                 # Global styles
├── components/
│   ├── ChatTab.jsx         # Chat tab container
│   ├── ChatTab.css
│   ├── ChatList.jsx        # Sidebar with chat list
│   ├── ChatList.css
│   ├── ChatWindow.jsx      # Main chat interface
│   ├── ChatWindow.css
│   ├── RAGTab.jsx          # Document upload tab
│   ├── RAGTab.css
│   ├── MonitoringTab.jsx   # System monitoring tab
│   └── MonitoringTab.css
├── index.css               # Global CSS reset
└── main.jsx                # React entry point
```

## Getting Started

### Prerequisites

- Node.js 16+ and npm
- Backend API running on http://localhost:8000
- Ollama service running

### Installation

```bash
cd frontend
npm install
```

### Development

```bash
npm run dev
```

The app will be available at `http://localhost:5174` (or another port if 5173-5174 are in use).

### Build for Production

```bash
npm run build
```

The built files will be in the `dist/` directory.

## API Integration

The frontend communicates with the Grace API at `http://localhost:8000`. Key endpoints used:

### Health Check

- `GET /health` - Check if Ollama is running and get available models

### Chat Management

- `POST /chats` - Create a new chat
- `GET /chats` - List all chats
- `GET /chats/{chat_id}` - Get specific chat
- `PUT /chats/{chat_id}` - Update chat settings
- `DELETE /chats/{chat_id}` - Delete a chat

### Messages

- `GET /chats/{chat_id}/messages` - Get chat history
- `POST /chats/{chat_id}/prompt` - Send a message and get response

## Usage

### Creating a Chat

1. Click the **+** button in the chat list header
2. A new chat is created automatically

### Sending a Message

1. Select a chat from the list
2. Type your message in the input field at the bottom
3. Press Enter or click the send button
4. The AI response will appear below your message

### Renaming a Chat

1. Select a chat
2. Click the **✎** (edit) button
3. Enter the new title
4. Click **✓** to save or **✕** to cancel

### Deleting a Chat

1. Select a chat
2. Click the **🗑** (delete) button
3. Confirm the deletion

### Health Status

The top-right corner shows:

- **Connected** (green dot): Ollama is running
- **Disconnected** (orange dot): Ollama is not running

## Styling

The frontend uses a clean, modern design similar to ChatGPT:

- Light theme with gray accents
- Responsive layout
- Smooth animations and transitions
- Intuitive UI/UX

## Architecture

### Component Hierarchy

```
App
├── ChatTab
│   ├── ChatList
│   └── ChatWindow
├── RAGTab
└── MonitoringTab
```

### State Management

- Uses React hooks (useState, useEffect)
- Local state for UI interactions
- API calls for data persistence

### Key Features Explained

**ChatTab**: Container component that manages the chat interface

- Fetches list of chats on mount
- Handles chat creation, deletion, and renaming
- Passes handlers to child components

**ChatList**: Sidebar component showing all chats

- Displays chat list with selection
- Handles rename/delete actions
- Creates new chats

**ChatWindow**: Main chat interface

- Displays message history
- Handles sending messages
- Auto-scrolls to latest message
- Shows chat metadata

## Future Enhancements

### Documents Tab

- File upload interface
- Document management
- RAG configuration

### Monitoring Tab

- Real-time system metrics
- API performance monitoring
- Error tracking

### Chat Features

- Message search
- Conversation export
- Message editing
- Conversation export to PDF/JSON

### UI Improvements

- Dark mode support
- Keyboard shortcuts
- Message reactions
- Rich text editing

## Troubleshooting

### "Ollama service is not running"

Make sure Ollama is running on your system. Start it with:

```bash
ollama serve
```

### Port already in use

If port 5174 is already in use, Vite will automatically try the next available port. Check the terminal output for the actual port.

### API Connection Error

- Ensure the backend is running on http://localhost:8000
- Check CORS settings in the backend
- Verify network connectivity

### Messages not loading

- Check browser console for errors (F12)
- Verify the chat ID is valid
- Check backend API logs

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 15+
- Opera 76+

## License

MIT
