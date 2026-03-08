/**
 * Global State Management with Zustand
 * =====================================
 * Centralized state management for GRACE frontend.
 * Includes persistence, subscriptions, and devtools support.
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { devtools } from 'zustand/middleware';

// =============================================================================
// User Preferences Store
// =============================================================================

export const usePreferencesStore = create(
  devtools(
    persist(
      (set, _get) => ({
        // Theme
        theme: 'system', // 'light' | 'dark' | 'system'
        setTheme: (theme) => set({ theme }),

        // Sidebar
        sidebarOpen: true,
        sidebarWidth: 280,
        setSidebarOpen: (open) => set({ sidebarOpen: open }),
        setSidebarWidth: (width) => set({ sidebarWidth: width }),
        toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),

        // Chat preferences
        chatFontSize: 14,
        setChatFontSize: (size) => set({ chatFontSize: size }),
        showTimestamps: true,
        setShowTimestamps: (show) => set({ showTimestamps: show }),
        enableMarkdown: true,
        setEnableMarkdown: (enable) => set({ enableMarkdown: enable }),

        // Notifications
        notificationsEnabled: true,
        soundEnabled: true,
        setNotificationsEnabled: (enabled) => set({ notificationsEnabled: enabled }),
        setSoundEnabled: (enabled) => set({ soundEnabled: enabled }),

        // Keyboard shortcuts
        keyboardShortcutsEnabled: true,
        setKeyboardShortcutsEnabled: (enabled) => set({ keyboardShortcutsEnabled: enabled }),

        // Reset to defaults
        resetPreferences: () => set({
          theme: 'system',
          sidebarOpen: true,
          sidebarWidth: 280,
          chatFontSize: 14,
          showTimestamps: true,
          enableMarkdown: true,
          notificationsEnabled: true,
          soundEnabled: true,
          keyboardShortcutsEnabled: true,
        }),
      }),
      {
        name: 'grace-preferences',
        storage: createJSONStorage(() => localStorage),
      }
    ),
    { name: 'PreferencesStore' }
  )
);

// =============================================================================
// Chat Store
// =============================================================================

export const useChatStore = create(
  devtools(
    persist(
      (set, _get) => ({
        // Active chat
        activeChat: null,
        setActiveChat: (chat) => set({ activeChat: chat }),

        // Chat list
        chats: [],
        setChats: (chats) => set({ chats }),
        addChat: (chat) => set((state) => ({ chats: [chat, ...state.chats] })),
        removeChat: (chatId) => set((state) => ({
          chats: state.chats.filter((c) => c.id !== chatId),
          activeChat: state.activeChat?.id === chatId ? null : state.activeChat,
        })),
        updateChat: (chatId, updates) => set((state) => ({
          chats: state.chats.map((c) => (c.id === chatId ? { ...c, ...updates } : c)),
          activeChat: state.activeChat?.id === chatId ? { ...state.activeChat, ...updates } : state.activeChat,
        })),

        // Messages for active chat
        messages: [],
        setMessages: (messages) => set({ messages }),
        addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
        updateMessage: (messageId, updates) => set((state) => ({
          messages: state.messages.map((m) => (m.id === messageId ? { ...m, ...updates } : m)),
        })),

        // Streaming state
        isStreaming: false,
        streamingMessageId: null,
        setStreaming: (isStreaming, messageId = null) => set({ isStreaming, streamingMessageId: messageId }),

        // Draft message
        draftMessage: '',
        setDraftMessage: (draft) => set({ draftMessage: draft }),

        // Clear chat data
        clearChatData: () => set({
          activeChat: null,
          chats: [],
          messages: [],
          isStreaming: false,
          streamingMessageId: null,
          draftMessage: '',
        }),
      }),
      {
        name: 'grace-chat',
        storage: createJSONStorage(() => localStorage),
        partialize: (state) => ({
          chats: state.chats.slice(0, 50), // Only persist last 50 chats
          activeChat: state.activeChat,
        }),
      }
    ),
    { name: 'ChatStore' }
  )
);

// =============================================================================
// UI Store (non-persistent)
// =============================================================================

export const useUIStore = create(
  devtools(
    (set, _get) => ({
      // Loading states
      isLoading: false,
      loadingMessage: '',
      setLoading: (isLoading, message = '') => set({ isLoading, loadingMessage: message }),

      // Modals
      activeModal: null,
      modalData: null,
      openModal: (modal, data = null) => set({ activeModal: modal, modalData: data }),
      closeModal: () => set({ activeModal: null, modalData: null }),

      // Toasts (managed by Toast component, but tracked here)
      toastQueue: [],
      addToast: (toast) => set((state) => ({ toastQueue: [...state.toastQueue, { ...toast, id: Date.now() }] })),
      removeToast: (id) => set((state) => ({ toastQueue: state.toastQueue.filter((t) => t.id !== id) })),

      // Search
      searchQuery: '',
      searchResults: [],
      isSearching: false,
      setSearchQuery: (query) => set({ searchQuery: query }),
      setSearchResults: (results) => set({ searchResults: results }),
      setIsSearching: (searching) => set({ isSearching: searching }),

      // Command palette
      commandPaletteOpen: false,
      setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),
      toggleCommandPalette: () => set((state) => ({ commandPaletteOpen: !state.commandPaletteOpen })),

      // File browser
      currentPath: '/',
      selectedFiles: [],
      setCurrentPath: (path) => set({ currentPath: path }),
      setSelectedFiles: (files) => set({ selectedFiles: files }),
      toggleFileSelection: (file) => set((state) => {
        const isSelected = state.selectedFiles.some((f) => f.path === file.path);
        return {
          selectedFiles: isSelected
            ? state.selectedFiles.filter((f) => f.path !== file.path)
            : [...state.selectedFiles, file],
        };
      }),
      clearFileSelection: () => set({ selectedFiles: [] }),
    }),
    { name: 'UIStore' }
  )
);

// =============================================================================
// Auth Store
// =============================================================================

export const useAuthStore = create(
  devtools(
    persist(
      (set, _get) => ({
        // User
        user: null,
        isAuthenticated: false,
        setUser: (user) => set({ user, isAuthenticated: !!user }),

        // Tokens
        accessToken: null,
        refreshToken: null,
        setTokens: (access, refresh) => set({ accessToken: access, refreshToken: refresh }),

        // Genesis keys
        genesisKeys: [],
        activeGenesisKey: null,
        setGenesisKeys: (keys) => set({ genesisKeys: keys }),
        setActiveGenesisKey: (key) => set({ activeGenesisKey: key }),

        // Session
        sessionId: null,
        setSessionId: (id) => set({ sessionId: id }),

        // Logout
        logout: () => set({
          user: null,
          isAuthenticated: false,
          accessToken: null,
          refreshToken: null,
          genesisKeys: [],
          activeGenesisKey: null,
          sessionId: null,
        }),
      }),
      {
        name: 'grace-auth',
        storage: createJSONStorage(() => localStorage),
        partialize: (state) => ({
          user: state.user,
          accessToken: state.accessToken,
          refreshToken: state.refreshToken,
          activeGenesisKey: state.activeGenesisKey,
        }),
      }
    ),
    { name: 'AuthStore' }
  )
);

// =============================================================================
// System Store
// =============================================================================

export const useSystemStore = create(
  devtools(
    (set, _get) => ({
      // Connection status
      isOnline: navigator.onLine,
      wsConnected: false,
      setOnline: (online) => set({ isOnline: online }),
      setWsConnected: (connected) => set({ wsConnected: connected }),

      // System health
      systemHealth: null,
      setSystemHealth: (health) => set({ systemHealth: health }),

      // Services status
      services: {
        ollama: { status: 'unknown', lastCheck: null },
        database: { status: 'unknown', lastCheck: null },
        qdrant: { status: 'unknown', lastCheck: null },
      },
      updateServiceStatus: (service, status) => set((state) => ({
        services: {
          ...state.services,
          [service]: { status, lastCheck: new Date().toISOString() },
        },
      })),

      // Models
      availableModels: [],
      activeModel: null,
      setAvailableModels: (models) => set({ availableModels: models }),
      setActiveModel: (model) => set({ activeModel: model }),

      // Notifications from server
      serverNotifications: [],
      addServerNotification: (notification) => set((state) => ({
        serverNotifications: [...state.serverNotifications, notification].slice(-100),
      })),
      clearServerNotifications: () => set({ serverNotifications: [] }),
    }),
    { name: 'SystemStore' }
  )
);

// =============================================================================
// Selectors (for optimized re-renders)
// =============================================================================

export const selectTheme = (state) => state.theme;
export const selectSidebarOpen = (state) => state.sidebarOpen;
export const selectActiveChat = (state) => state.activeChat;
export const selectMessages = (state) => state.messages;
export const selectIsStreaming = (state) => state.isStreaming;
export const selectIsAuthenticated = (state) => state.isAuthenticated;
export const selectUser = (state) => state.user;
export const selectIsOnline = (state) => state.isOnline;
export const selectSystemHealth = (state) => state.systemHealth;

// =============================================================================
// Combined hooks for common patterns
// =============================================================================

export function useChat() {
  const activeChat = useChatStore((state) => state.activeChat);
  const messages = useChatStore((state) => state.messages);
  const isStreaming = useChatStore((state) => state.isStreaming);
  const addMessage = useChatStore((state) => state.addMessage);
  const setMessages = useChatStore((state) => state.setMessages);

  return { activeChat, messages, isStreaming, addMessage, setMessages };
}

export function useTheme() {
  const theme = usePreferencesStore((state) => state.theme);
  const setTheme = usePreferencesStore((state) => state.setTheme);

  return { theme, setTheme };
}

export function useAuth() {
  const user = useAuthStore((state) => state.user);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const logout = useAuthStore((state) => state.logout);

  return { user, isAuthenticated, logout };
}

export default {
  usePreferencesStore,
  useChatStore,
  useUIStore,
  useAuthStore,
  useSystemStore,
};
