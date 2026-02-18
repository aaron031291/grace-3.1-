# JavaScript & React Development Guide

## Modern JavaScript (ES6+)

### Arrow Functions
```javascript
const add = (a, b) => a + b;
const greet = (name) => `Hello, ${name}!`;
```

### Destructuring
```javascript
const { name, age } = user;
const [first, second, ...rest] = items;
```

### Async/Await
```javascript
async function fetchData(url) {
  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.json();
  } catch (error) {
    console.error('Fetch failed:', error);
    throw error;
  }
}
```

### Optional Chaining & Nullish Coalescing
```javascript
const city = user?.address?.city ?? 'Unknown';
const count = data?.items?.length ?? 0;
```

## React Fundamentals

### Function Components with Hooks
```jsx
import { useState, useEffect, useCallback } from 'react';

function UserProfile({ userId }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchUser(userId).then(data => {
      setUser(data);
      setLoading(false);
    });
  }, [userId]);

  if (loading) return <div>Loading...</div>;
  return <div>{user.name}</div>;
}
```

### Custom Hooks
```jsx
function useApi(url) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(url)
      .then(res => res.json())
      .then(setData)
      .catch(setError)
      .finally(() => setLoading(false));
  }, [url]);

  return { data, loading, error };
}
```

### Context for State Management
```jsx
const ThemeContext = React.createContext('light');

function App() {
  return (
    <ThemeContext.Provider value="dark">
      <Toolbar />
    </ThemeContext.Provider>
  );
}

function ThemedButton() {
  const theme = useContext(ThemeContext);
  return <button className={theme}>Click me</button>;
}
```

## Component Patterns

### Container/Presenter
- Container: Fetches data, manages state
- Presenter: Pure rendering, receives props

### Error Boundaries
```jsx
class ErrorBoundary extends React.Component {
  state = { hasError: false };
  
  static getDerivedStateFromError(error) {
    return { hasError: true };
  }
  
  render() {
    if (this.state.hasError) return <h1>Something went wrong.</h1>;
    return this.props.children;
  }
}
```

### Loading States
Always handle: loading, error, empty, and data states.

## API Integration

### Fetch with Error Handling
```javascript
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

async function apiCall(endpoint, options = {}) {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `API error: ${response.status}`);
  }
  return response.json();
}
```

### Server-Sent Events (Streaming)
```javascript
async function streamChat(message, onToken) {
  const response = await fetch(`${API_BASE}/stream/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });
  
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const text = decoder.decode(value);
    // Parse SSE format
    const lines = text.split('\n');
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));
        onToken(data);
      }
    }
  }
}
```

### WebSocket Connection
```javascript
function connectWebSocket(channel, onMessage) {
  const ws = new WebSocket(`ws://localhost:8000/ws?channel=${channel}`);
  ws.onmessage = (event) => onMessage(JSON.parse(event.data));
  ws.onerror = (error) => console.error('WS error:', error);
  return ws;
}
```
