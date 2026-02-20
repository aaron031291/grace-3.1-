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

  // Unified Learning Pipeline
  pipeline: `${API_BASE_URL}/pipeline`,
  pipelineStatus: `${API_BASE_URL}/pipeline/status`,
  pipelineGraph: `${API_BASE_URL}/pipeline/graph`,

  // Streaming
  streamChat: `${API_BASE_URL}/stream/chat`,

  // WebSocket
  ws: `${API_BASE_URL.replace('http', 'ws')}/ws`,
  voiceWs: `${API_BASE_URL.replace('http', 'ws')}/voice/ws/continuous`,

  // Kimi + Grace Learning
  kimiLearning: `${API_BASE_URL}/llm-learning`,
  kimiStatus: `${API_BASE_URL}/llm-learning/kimi/status`,
  kimiAnalyze: `${API_BASE_URL}/llm-learning/kimi/analyze`,
  graceExecute: `${API_BASE_URL}/llm-learning/grace/execute`,
  learningProgress: `${API_BASE_URL}/llm-learning/progress`,
  learningDashboard: `${API_BASE_URL}/llm-learning/dashboard`,
  verificationPending: `${API_BASE_URL}/llm-learning/grace/verification/pending`,
  verificationConfirm: `${API_BASE_URL}/llm-learning/grace/verification/confirm`,

  // Diagnostic Machine
  diagnostic: \`\${API_BASE_URL}/diagnostic\`,

  // Proactive Learning
  proactiveLearning: \`\${API_BASE_URL}/proactive-learning\`,

  // Knowledge Browser
  knowledgeBrowser: \`\${API_BASE_URL}/knowledge-browser\`,
  knowledgeBrowserDomains: \`\${API_BASE_URL}/knowledge-browser/domains\`,
  knowledgeBrowserCoverage: \`\${API_BASE_URL}/knowledge-browser/coverage\`,

  // Agent
  agent: \`\${API_BASE_URL}/agent\`,

  // Codebase
  codebase: \`\${API_BASE_URL}/codebase\`,

  // Learning Efficiency
  learningEfficiency: \`\${API_BASE_URL}/learning-efficiency\`,

  // Repo Genesis
  repoGenesis: \`\${API_BASE_URL}/repo-genesis\`,

  // Testing
  testing: \`\${API_BASE_URL}/test\`,

  // Auth
  auth: \`\${API_BASE_URL}/auth\`,

  // System Monitoring
  monitoring: \`\${API_BASE_URL}/monitoring\`,

  // Layer 1
  layer1: \`\${API_BASE_URL}/layer1\`,

  // File Ingestion
  fileIngest: \`\${API_BASE_URL}/file-ingest\`,

  // Directory Hierarchy
  directoryHierarchy: \`\${API_BASE_URL}/directory-hierarchy\`,

  // Ingestion Integration
  ingestionIntegration: \`\${API_BASE_URL}/ingestion-integration\`,

  // Prometheus Metrics
  metrics: \`\${API_BASE_URL}/metrics\`,

  // Sandbox Lab
  sandboxLab: \`\${API_BASE_URL}/sandbox-lab\`,

  // Autonomous Learning
  autonomousLearning: \`\${API_BASE_URL}/autonomous-learning\`,

  // ML Intelligence
  mlIntelligence: \`\${API_BASE_URL}/ml-intelligence\`,
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

  // Diagnostic Machine
  diagnostic: \`\${API_BASE_URL}/diagnostic\`,

  // Proactive Learning
  proactiveLearning: \`\${API_BASE_URL}/proactive-learning\`,

  // Knowledge Browser
  knowledgeBrowser: \`\${API_BASE_URL}/knowledge-browser\`,
  knowledgeBrowserDomains: \`\${API_BASE_URL}/knowledge-browser/domains\`,
  knowledgeBrowserCoverage: \`\${API_BASE_URL}/knowledge-browser/coverage\`,

  // Agent
  agent: \`\${API_BASE_URL}/agent\`,

  // Codebase
  codebase: \`\${API_BASE_URL}/codebase\`,

  // Learning Efficiency
  learningEfficiency: \`\${API_BASE_URL}/learning-efficiency\`,

  // Repo Genesis
  repoGenesis: \`\${API_BASE_URL}/repo-genesis\`,

  // Testing
  testing: \`\${API_BASE_URL}/test\`,

  // Auth
  auth: \`\${API_BASE_URL}/auth\`,

  // System Monitoring
  monitoring: \`\${API_BASE_URL}/monitoring\`,

  // Layer 1
  layer1: \`\${API_BASE_URL}/layer1\`,

  // File Ingestion
  fileIngest: \`\${API_BASE_URL}/file-ingest\`,

  // Directory Hierarchy
  directoryHierarchy: \`\${API_BASE_URL}/directory-hierarchy\`,

  // Ingestion Integration
  ingestionIntegration: \`\${API_BASE_URL}/ingestion-integration\`,

  // Prometheus Metrics
  metrics: \`\${API_BASE_URL}/metrics\`,

  // Sandbox Lab
  sandboxLab: \`\${API_BASE_URL}/sandbox-lab\`,

  // Autonomous Learning
  autonomousLearning: \`\${API_BASE_URL}/autonomous-learning\`,

  // ML Intelligence
  mlIntelligence: \`\${API_BASE_URL}/ml-intelligence\`,
};

export default {
  API_BASE_URL,
  OLLAMA_BASE_URL,
  API_ENDPOINTS,
  buildUrl,

  // Diagnostic Machine
  diagnostic: \`\${API_BASE_URL}/diagnostic\`,

  // Proactive Learning
  proactiveLearning: \`\${API_BASE_URL}/proactive-learning\`,

  // Knowledge Browser
  knowledgeBrowser: \`\${API_BASE_URL}/knowledge-browser\`,
  knowledgeBrowserDomains: \`\${API_BASE_URL}/knowledge-browser/domains\`,
  knowledgeBrowserCoverage: \`\${API_BASE_URL}/knowledge-browser/coverage\`,

  // Agent
  agent: \`\${API_BASE_URL}/agent\`,

  // Codebase
  codebase: \`\${API_BASE_URL}/codebase\`,

  // Learning Efficiency
  learningEfficiency: \`\${API_BASE_URL}/learning-efficiency\`,

  // Repo Genesis
  repoGenesis: \`\${API_BASE_URL}/repo-genesis\`,

  // Testing
  testing: \`\${API_BASE_URL}/test\`,

  // Auth
  auth: \`\${API_BASE_URL}/auth\`,

  // System Monitoring
  monitoring: \`\${API_BASE_URL}/monitoring\`,

  // Layer 1
  layer1: \`\${API_BASE_URL}/layer1\`,

  // File Ingestion
  fileIngest: \`\${API_BASE_URL}/file-ingest\`,

  // Directory Hierarchy
  directoryHierarchy: \`\${API_BASE_URL}/directory-hierarchy\`,

  // Ingestion Integration
  ingestionIntegration: \`\${API_BASE_URL}/ingestion-integration\`,

  // Prometheus Metrics
  metrics: \`\${API_BASE_URL}/metrics\`,

  // Sandbox Lab
  sandboxLab: \`\${API_BASE_URL}/sandbox-lab\`,

  // Autonomous Learning
  autonomousLearning: \`\${API_BASE_URL}/autonomous-learning\`,

  // ML Intelligence
  mlIntelligence: \`\${API_BASE_URL}/ml-intelligence\`,
};
