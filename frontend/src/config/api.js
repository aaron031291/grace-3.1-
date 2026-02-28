/**
 * API Configuration — Grace v1
 *
 * Clean resource-based REST API.
 * 10 resources, 108 endpoints.
 */

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
export const API_BASE = API_BASE_URL;

// v1 Resource endpoints
export const V1 = {
  chats:      `${API_BASE_URL}/api/v1/chats`,
  files:      `${API_BASE_URL}/api/v1/files`,
  documents:  `${API_BASE_URL}/api/v1/documents`,
  governance: `${API_BASE_URL}/api/v1/governance`,
  sources:    `${API_BASE_URL}/api/v1/sources`,
  training:   `${API_BASE_URL}/api/v1/training`,
  projects:   `${API_BASE_URL}/api/v1/projects`,
  tasks:      `${API_BASE_URL}/api/v1/tasks`,
  system:     `${API_BASE_URL}/api/v1/system`,
  agent:      `${API_BASE_URL}/api/v1/agent`,
};

// Chunked upload endpoints (5 GB support)
export const UPLOAD = {
  initiate: `${API_BASE_URL}/api/upload/initiate`,
  chunk:    `${API_BASE_URL}/api/upload/chunk`,
  complete: `${API_BASE_URL}/api/upload/complete`,
  status:   `${API_BASE_URL}/api/upload/status`,
  cancel:   `${API_BASE_URL}/api/upload/cancel`,
  active:   `${API_BASE_URL}/api/upload/active`,
};

// Legacy endpoints still used directly by some components
export const API_ENDPOINTS = {
  health: `${API_BASE_URL}/health`,
  chat: `${API_BASE_URL}/chat`,
  chats: `${API_BASE_URL}/chats`,
  retrieve: `${API_BASE_URL}/retrieve`,
  search: `${API_BASE_URL}/retrieve/search`,
  voice: `${API_BASE_URL}/voice`,
  mcpChat: `${API_BASE_URL}/api/mcp/chat`,
};

export const buildUrl = (endpoint, params = {}) => {
  const url = new URL(endpoint);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      url.searchParams.append(key, value);
    }
  });
  return url.toString();
};

export default { API_BASE_URL, V1, UPLOAD, API_ENDPOINTS, buildUrl };
