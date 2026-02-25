/**
 * API Configuration
 *
 * Centralized configuration for API endpoints.
 * Uses environment variables for flexibility across environments.
 */

// Backend API base URL - defaults to localhost for development
// In production, set VITE_API_BASE_URL environment variable
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// Backward compatibility alias for components using the old name
export const API_BASE = API_BASE_URL;

// Ollama LLM service URL
export const OLLAMA_BASE_URL = import.meta.env.VITE_OLLAMA_URL || 'http://localhost:11434';

// API endpoints
export const API_ENDPOINTS = {
  // Health
  health: `${API_BASE_URL}/health`,

  // Chat
  chat: `${API_BASE_URL}/chat`,
  chats: `${API_BASE_URL}/chats`,

  // Files
  files: `${API_BASE_URL}/files`,
  upload: `${API_BASE_URL}/files/upload`,

  // Retrieval
  retrieve: `${API_BASE_URL}/retrieve`,
  search: `${API_BASE_URL}/retrieve/search`,

  // Cognitive
  cognitive: `${API_BASE_URL}/cognitive`,
  decisions: `${API_BASE_URL}/cognitive/decisions`,

  // Ingestion
  ingest: `${API_BASE_URL}/ingest`,

  // Telemetry
  telemetry: `${API_BASE_URL}/telemetry`,

  // Voice
  voice: `${API_BASE_URL}/voice`,

  // Scraping
  scrape: `${API_BASE_URL}/scrape`,

  // Version Control
  versionControl: `${API_BASE_URL}/api/version-control`,

  // Genesis
  genesis: `${API_BASE_URL}/genesis`,

  // Knowledge Base
  knowledgeBase: `${API_BASE_URL}/knowledge-base`,

  // Learning
  learning: `${API_BASE_URL}/learning-memory`,
  training: `${API_BASE_URL}/training`,

  // LLM
  llm: `${API_BASE_URL}/llm`,

  // Governance
  governance: `${API_BASE_URL}/governance`,

  // Repositories
  repositories: `${API_BASE_URL}/repositories`,

  // Sandbox
  sandbox: `${API_BASE_URL}/sandbox`,

  // Librarian
  librarian: `${API_BASE_URL}/librarian`,

  // KPI
  kpi: `${API_BASE_URL}/kpi`,

  // Notion
  notion: `${API_BASE_URL}/notion`,

  // World Model
  worldModel: `${API_BASE_URL}/api/world-model`,
  worldModelState: `${API_BASE_URL}/api/world-model/state`,
  worldModelChat: `${API_BASE_URL}/api/world-model/chat`,
  worldModelSubsystems: `${API_BASE_URL}/api/world-model/subsystems`,

  // Librarian File System
  librarianFs: `${API_BASE_URL}/api/librarian-fs`,
  librarianFsTree: `${API_BASE_URL}/api/librarian-fs/tree`,
  librarianFsBrowse: `${API_BASE_URL}/api/librarian-fs/browse`,
  librarianFsStats: `${API_BASE_URL}/api/librarian-fs/stats`,

  // MCP Chat
  mcpChat: `${API_BASE_URL}/api/mcp/chat`,

  // Cross-Tab Intelligence
  folderChat: `${API_BASE_URL}/api/intelligence/folder-chat`,
  allTags: `${API_BASE_URL}/api/intelligence/tags`,
  activity: `${API_BASE_URL}/api/intelligence/activity`,

  // Docs Library
  docsAll: `${API_BASE_URL}/api/docs/all`,
  docsByFolder: `${API_BASE_URL}/api/docs/by-folder`,
  docsUpload: `${API_BASE_URL}/api/docs/upload`,
  docsStats: `${API_BASE_URL}/api/docs/stats`,
};

// Helper function to build URLs with query params
export const buildUrl = (endpoint, params = {}) => {
  const url = new URL(endpoint);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      url.searchParams.append(key, value);
    }
  });
  return url.toString();
};

export default {
  API_BASE_URL,
  OLLAMA_BASE_URL,
  API_ENDPOINTS,
  buildUrl,
};
