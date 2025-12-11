# Grace Chatbot - Visual Tour & Component Guide

## User Interface Layout

```
┌──────────────────────────────────────────────────────────────────┐
│                        Grace Header                              │
│  Logo         Health Status (Connected/Disconnected) Models: X   │
├──────────────┬──────────────────────────────────────────────────┤
│              │                                                    │
│  Chat List   │         Chat Window                               │
│  ┌─────────┐ │  ┌───────────────────────────────────────────┐   │
│  │New Chat │ │  │ Chat Title    [model] [temp: 0.7]        │   │
│  └─────────┘ │  ├───────────────────────────────────────────┤   │
│              │  │                                            │   │
│  Chat 1      │  │  👤 User Message                          │   │
│  Chat 2      │  │  This is my question                      │   │
│  Chat 3      │  │                                            │   │
│              │  │  🤖 Assistant Response                     │   │
│  [+] [-]     │  │  This is the AI response...               │   │
│              │  │                                            │   │
│              │  ├───────────────────────────────────────────┤   │
│              │  │ [Text Input Field]          [Send Button] │   │
│              │  └───────────────────────────────────────────┘   │
└──────────────┴──────────────────────────────────────────────────┘
```

## Component Hierarchy

```
App
├── Header
│   ├── Title (Grace)
│   └── Health Indicator
│       ├── Status Dot (green/orange)
│       └── Status Text
│
├── Sidebar
│   └── Tabs Navigation
│       ├── Chat Tab (active)
│       ├── Documents Tab
│       └── Monitoring Tab
│
└── Main Content
    ├── ChatTab (if chat tab selected)
    │   ├── ChatList
    │   │   ├── Header
    │   │   │   ├── Title
    │   │   │   └── New Chat Button
    │   │   │
    │   │   └── Chat Items
    │   │       ├── Chat Title (editable)
    │   │       └── Actions (edit, delete)
    │   │
    │   └── ChatWindow
    │       ├── Header
    │       │   ├── Chat Title
    │       │   ├── Model Badge
    │       │   └── Temp Badge
    │       │
    │       ├── Messages Container
    │       │   └── Message Items
    │       │       ├── Avatar
    │       │       ├── Role Label
    │       │       ├── Message Text
    │       │       └── Metadata
    │       │
    │       └── Message Input Form
    │           ├── Text Input
    │           └── Send Button
    │
    ├── RAGTab (if rag tab selected)
    │   └── Placeholder (Coming Soon)
    │
    └── MonitoringTab (if monitoring tab selected)
        └── Placeholder (Coming Soon)
```

## Component Details

### App.jsx

**Purpose**: Main application container and tab routing

**Key Features**:

- Manages active tab state
- Health check polling
- Header rendering
- Sidebar navigation

**Props**: None
**State**:

- `activeTab`: 'chat' | 'rag' | 'monitoring'
- `apiHealth`: Health status object

**Styling**:

- Flexbox layout
- Full viewport height
- Color scheme: light theme

---

### Header Component (in App.jsx)

**Purpose**: Display app title and connection status

**Layout**:

```
┌─────────────────────────────────┐
│ Grace    🟢 Connected (3 models)│
└─────────────────────────────────┘
```

**Health Indicators**:

- 🟢 **Connected**: Ollama is running (green dot)
- 🟠 **Disconnected**: Ollama is not running (orange dot)
- Models count shown when running

---

### Sidebar Component (in App.jsx)

**Purpose**: Tab navigation

**Tabs**:

1. **Chat** - Main chatting interface (currently active)
2. **Documents** - RAG document upload (coming soon)
3. **Monitoring** - System monitoring (coming soon)

**Features**:

- Active tab highlighting
- SVG icons for each tab
- Vertical layout
- Always visible on desktop

---

### ChatList.jsx

**Purpose**: Display list of all chats with management

**Layout**:

```
┌──────────────────────┐
│ Chats           [+]  │  ← Header with new chat button
├──────────────────────┤
│ • Chat 1        [✎]  │  ← Normal state
│ • Chat 2        [✎]  │
│                      │
│ ◆ Chat 3 (active) │  ← Active state
│  [Edit] [Delete] │
│                      │
│ • Chat 4 (edit)  │  ← Edit mode
│  [TitleInput] [✓][✕]│
└──────────────────────┘
```

**Props**:
| Prop | Type | Description |
|------|------|-------------|
| chats | Array | List of chat objects |
| selectedChatId | Number | Currently selected chat ID |
| onSelectChat | Function | Callback for selecting chat |
| onCreateChat | Function | Callback for creating chat |
| onDeleteChat | Function | Callback for deleting chat |
| onUpdateTitle | Function | Callback for renaming chat |
| loading | Boolean | Loading state |

**Features**:

- Click to select chat
- Edit button to rename
- Delete button with confirmation
- Visual selection indicator
- Scrollable for many chats
- New chat button in header

---

### ChatWindow.jsx

**Purpose**: Main chat interface with message display and input

**Layout**:

```
┌────────────────────────────────────┐
│ My Chat    [mistral] [0.7]         │  ← Header
├────────────────────────────────────┤
│                                    │
│ 👤 User                            │  ← User message
│    What is AI?                     │
│                                    │
│ 🤖 Assistant                       │  ← AI response
│    AI stands for Artificial...     │
│    Tokens: 45                      │
│                                    │
│ 👤 User                            │
│    Tell me more                    │
│                                    │
├────────────────────────────────────┤
│ [Type message...] [→]              │  ← Input
└────────────────────────────────────┘
```

**Props**:
| Prop | Type | Description |
|------|------|-------------|
| chatId | Number | Current chat ID |
| onChatCreated | Function | Callback after message sent |

**State**:
| State | Type | Description |
|-------|------|-------------|
| messages | Array | Message history |
| input | String | Current input text |
| loading | Boolean | Sending state |
| chatInfo | Object | Chat metadata |

**Features**:

- Display chat history with scrolling
- Auto-scroll to latest message
- Real-time message display
- Message animations (fade in, slide up)
- Model and temperature badges
- Empty state message
- Loading indicator while sending

---

### Message Item (inside ChatWindow)

**Layout**:

```
┌─────────────────────────────────┐
│ 👤 USER                         │  ← Avatar + Role
│    Hello, how are you?          │  ← Message content
│                                 │
│ 🤖 ASSISTANT                    │
│    I'm doing great, thanks!     │
│    Tokens: 12                   │  ← Metadata
└─────────────────────────────────┘
```

**Features**:

- Role-based styling (different colors)
- Avatar emoji (👤 for user, 🤖 for AI)
- Timestamp (optional)
- Token count
- Text wrapping
- Proper spacing

---

### ChatTab.jsx

**Purpose**: Container for chat interface

**Structure**:

- Combines ChatList and ChatWindow
- Manages chat data fetching
- Handles CRUD operations
- Passes data to children

**Features**:

- Side-by-side layout
- Responsive width distribution
- State lifting from children

---

### RAGTab.jsx

**Purpose**: Document upload interface (placeholder)

**Current State**:

```
┌──────────────────────────────────┐
│                                  │
│            📄                     │
│    Document Upload & RAG         │
│    Upload documents to enhance   │
│    your chatbot...               │
│                                  │
│    Coming soon...                │
│                                  │
└──────────────────────────────────┘
```

**Planned Features**:

- File upload area (drag & drop)
- Document list
- Document deletion
- Document metadata
- RAG settings

---

### MonitoringTab.jsx

**Purpose**: System monitoring dashboard (placeholder)

**Current State**:

```
┌──────────────────────────────────┐
│                                  │
│            📊                     │
│    System Monitoring             │
│    Monitor the health and        │
│    performance...                │
│                                  │
│    Coming soon...                │
│                                  │
└──────────────────────────────────┘
```

**Planned Features**:

- Real-time metrics
- Performance graphs
- Health status
- Resource usage
- Logs viewer

---

## Styling Architecture

### CSS Files

```
App.css
├── Global layout
├── Header styles
├── Sidebar styles
└── Main content styles

ChatTab.css
└── Tab layout

ChatList.css
├── List container
├── Chat items
├── Hover states
└── Edit mode

ChatWindow.css
├── Chat header
├── Messages container
├── Message styles
├── Input form
└── Animations

RAGTab.css & MonitoringTab.css
└── Placeholder styles
```

### Color Scheme

```
Primary: #0d0d0d (black)
Secondary: #6b7280 (gray)
Border: #e5e5e5 (light gray)
Background: #fff (white)
Hover: #f9fafb (light gray)
Active: #e5e7eb (medium gray)

User Message: #dbeafe (light blue)
AI Message: #f0fdf4 (light green)
System Message: #fef3c7 (light yellow)

Success: #10a981 (green)
Warning: #d97706 (orange)
Error: #dc2626 (red)
```

### Typography

```
Font Family: -apple-system, BlinkMacSystemFont, 'Segoe UI'...
Base Size: 16px
Line Height: 1.5

H1: 1.5rem (24px), font-weight: 700
H2: 1.125rem (18px), font-weight: 600
Body: 0.95rem (15px), font-weight: 400
Small: 0.875rem (14px), font-weight: 400
Tiny: 0.75rem (12px), font-weight: 600
```

### Spacing Scale

```
0.25rem = 4px   (xs)
0.5rem = 8px    (sm)
0.75rem = 12px  (md)
1rem = 16px     (lg)
1.5rem = 24px   (xl)
2rem = 32px     (2xl)
```

---

## Interaction Flows

### 1. Create Chat

```
User clicks [+] button
    ↓
ChatTab.createNewChat() called
    ↓
POST /chats request sent
    ↓
New chat added to list
    ↓
Chat automatically selected
    ↓
ChatWindow shows empty state
```

### 2. Send Message

```
User types message
    ↓
User presses Enter or clicks send
    ↓
Message state cleared, loading starts
    ↓
POST /chats/{id}/prompt sent
    ↓
Request includes message content + settings
    ↓
Backend saves user message, calls Ollama, saves response
    ↓
Response received by frontend
    ↓
fetchChatHistory() refreshes messages
    ↓
Messages displayed with animations
    ↓
Auto-scroll to latest message
    ↓
Loading stops
```

### 3. Rename Chat

```
User selects chat
    ↓
User clicks [✎] edit button
    ↓
Chat title becomes editable input
    ↓
User types new title
    ↓
User presses Enter or clicks [✓]
    ↓
PUT /chats/{id} request sent
    ↓
Chat title updated in list
    ↓
Edit mode exits
```

### 4. Delete Chat

```
User selects chat
    ↓
User clicks [🗑] delete button
    ↓
Confirmation dialog shown
    ↓
User confirms deletion
    ↓
DELETE /chats/{id} request sent
    ↓
Chat removed from list
    ↓
If this was selected chat, select first available
    ↓
ChatWindow shows empty state
```

### 5. Switch Chat

```
User clicks different chat in list
    ↓
selectedChatId state updated
    ↓
ChatWindow re-renders with new chatId
    ↓
useEffect triggers fetchChatHistory()
    ↓
useEffect triggers fetchChatInfo()
    ↓
Messages loaded for selected chat
    ↓
Chat metadata displayed in header
```

---

## Responsive Behavior

### Desktop (1280px+)

- Full sidebar always visible
- Split view (sidebar + chat window)
- Optimal for multitasking
- Wide input field

### Tablet (768px - 1279px)

- Sidebar might collapse to icons
- Chat window takes more space
- Touch-friendly buttons
- Optimized spacing

### Mobile (< 768px)

- Sidebar hidden by default
- Full-screen chat
- Modal sidebar toggle
- Stack layout

**Current Implementation**: Desktop optimized. Mobile support can be added with media queries.

---

## Accessibility Features

### Keyboard Navigation

- Tab through interactive elements
- Enter to select/submit
- Escape to cancel editing
- Arrow keys for navigation (future)

### Screen Readers

- Semantic HTML (button, input, nav)
- ARIA labels on icon buttons
- Alternative text for SVG icons
- Role attributes where needed

### Visual

- High contrast text (#0d0d0d on #fff)
- Focus indicators (blue outline)
- Color not the only indicator
- Readable font sizes

### Focus Management

- Focus visible on all buttons
- Logical tab order
- Focus trapping in dialogs (future)
- Skip links (future)

---

## Performance Optimizations

### Rendering

- Avoid unnecessary re-renders
- useRef for scroll element
- useCallback for stable references
- useEffect for side effects

### Network

- Single message load (not per-message request)
- Pagination for long histories
- Batch API calls
- Caching with fetch

### DOM

- Smooth scrolling (not jarring)
- CSS animations (GPU-accelerated)
- Minimal DOM updates
- Efficient CSS selectors

---

## Future Enhancements

### UI/UX

- [ ] Collapsible sidebar
- [ ] Dark mode
- [ ] Message search
- [ ] Conversation export
- [ ] Rich text editor
- [ ] Message reactions

### Features

- [ ] Voice input
- [ ] Image support
- [ ] File uploads
- [ ] Message pinning
- [ ] Conversation sharing
- [ ] Conversation templates

### Performance

- [ ] Message virtualization
- [ ] Service Worker
- [ ] Offline support
- [ ] Progressive loading
- [ ] Image optimization
