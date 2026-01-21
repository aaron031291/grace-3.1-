/**
 * IDE Bridge
 *
 * Connects VSCode to Grace backend services.
 * Handles all HTTP communication with the Grace API.
 */

import * as vscode from 'vscode';
import axios, { AxiosInstance, AxiosError } from 'axios';
import { GraceOSCore } from '../core/GraceOSCore';

export interface ApiResponse<T = any> {
    success: boolean;
    data?: T;
    error?: string;
    statusCode?: number;
}

export interface ChatMessage {
    role: 'user' | 'assistant' | 'system';
    content: string;
    timestamp?: string;
    metadata?: Record<string, any>;
}

export interface MemoryQuery {
    query: string;
    limit?: number;
    memoryTypes?: string[];
    filters?: Record<string, any>;
}

export interface MemoryEntry {
    id: string;
    content: string;
    memoryType: string;
    timestamp: string;
    score?: number;
    metadata?: Record<string, any>;
}

export interface GenesisKey {
    id: string;
    type: string;
    entityId: string;
    parentKey?: string;
    timestamp: string;
    hash: string;
    metadata?: Record<string, any>;
}

export interface DiagnosticResult {
    status: 'healthy' | 'warning' | 'error';
    layer: string;
    message: string;
    details?: Record<string, any>;
    recommendations?: string[];
}

export interface CognitiveAnalysis {
    analysis: string;
    patterns: string[];
    suggestions: string[];
    confidence: number;
    metadata?: Record<string, any>;
}

export interface LearningInsight {
    id: string;
    content: string;
    category: string;
    trustScore: number;
    timestamp: string;
}

export interface AutonomousTask {
    id: string;
    name: string;
    type: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    scheduledTime?: string;
    result?: any;
}

export class IDEBridge {
    private core: GraceOSCore;
    private client: AxiosInstance;
    private isConnected: boolean = false;
    private retryCount: number = 0;
    private maxRetries: number = 3;

    constructor(core: GraceOSCore) {
        this.core = core;
        const config = core.getConfig();

        this.client = axios.create({
            baseURL: config.backendUrl,
            timeout: 30000,
            headers: {
                'Content-Type': 'application/json',
                'X-Grace-Session': core.getSession().id,
            },
        });

        this.setupInterceptors();
    }

    private setupInterceptors(): void {
        // Request interceptor
        this.client.interceptors.request.use(
            config => {
                this.core.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
                return config;
            },
            error => {
                this.core.log(`API Request Error: ${error.message}`, 'error');
                return Promise.reject(error);
            }
        );

        // Response interceptor
        this.client.interceptors.response.use(
            response => {
                this.core.log(`API Response: ${response.status} ${response.config.url}`);
                this.retryCount = 0;
                return response;
            },
            async error => {
                const axiosError = error as AxiosError;
                this.core.log(`API Error: ${axiosError.message}`, 'error');

                // Handle connection errors
                if (axiosError.code === 'ECONNREFUSED' || axiosError.code === 'ENOTFOUND') {
                    this.isConnected = false;
                    this.core.setConnected(false);
                }

                return Promise.reject(error);
            }
        );
    }

    async connect(): Promise<boolean> {
        try {
            const response = await this.client.get('/health');
            this.isConnected = response.status === 200;
            this.core.setConnected(this.isConnected);

            if (this.isConnected) {
                this.core.log('Connected to Grace backend');
            }

            return this.isConnected;
        } catch (error) {
            this.core.log('Failed to connect to Grace backend', 'error');
            this.isConnected = false;
            this.core.setConnected(false);
            return false;
        }
    }

    disconnect(): void {
        this.isConnected = false;
        this.core.setConnected(false);
    }

    // Chat API

    async sendChatMessage(message: string, context?: Record<string, any>): Promise<ApiResponse<ChatMessage>> {
        try {
            const response = await this.client.post('/api/chat', {
                message,
                context,
                session_id: this.core.getSession().id,
            });
            return { success: true, data: response.data };
        } catch (error) {
            return this.handleError(error);
        }
    }

    async streamChatMessage(
        message: string,
        onChunk: (chunk: string) => void,
        context?: Record<string, any>
    ): Promise<ApiResponse<void>> {
        try {
            const response = await this.client.post('/api/streaming/chat', {
                message,
                context,
                session_id: this.core.getSession().id,
            }, {
                responseType: 'stream',
            });

            return new Promise((resolve, reject) => {
                response.data.on('data', (chunk: Buffer) => {
                    onChunk(chunk.toString());
                });
                response.data.on('end', () => {
                    resolve({ success: true });
                });
                response.data.on('error', (err: Error) => {
                    reject({ success: false, error: err.message });
                });
            });
        } catch (error) {
            return this.handleError(error);
        }
    }

    // Memory Mesh API

    async queryMemory(query: MemoryQuery): Promise<ApiResponse<MemoryEntry[]>> {
        try {
            const response = await this.client.post('/api/memory/query', query);
            return { success: true, data: response.data };
        } catch (error) {
            return this.handleError(error);
        }
    }

    async storeMemory(content: string, memoryType: string, metadata?: Record<string, any>): Promise<ApiResponse<MemoryEntry>> {
        try {
            const response = await this.client.post('/api/memory/store', {
                content,
                memory_type: memoryType,
                metadata,
            });
            return { success: true, data: response.data };
        } catch (error) {
            return this.handleError(error);
        }
    }

    async triggerMemoryConsolidation(): Promise<ApiResponse<void>> {
        try {
            await this.client.post('/api/magma/consolidate');
            return { success: true };
        } catch (error) {
            return this.handleError(error);
        }
    }

    async ingestToMagma(content: string, sourceType: string, metadata?: Record<string, any>): Promise<ApiResponse<any>> {
        try {
            const response = await this.client.post('/api/magma/ingest', {
                content,
                source_type: sourceType,
                metadata,
            });
            return { success: true, data: response.data };
        } catch (error) {
            return this.handleError(error);
        }
    }

    // Genesis Key API

    async createGenesisKey(type: string, entityId: string, metadata?: Record<string, any>): Promise<ApiResponse<GenesisKey>> {
        try {
            const response = await this.client.post('/api/genesis/create', {
                type,
                entity_id: entityId,
                metadata,
            });
            return { success: true, data: response.data };
        } catch (error) {
            return this.handleError(error);
        }
    }

    async getGenesisKey(keyId: string): Promise<ApiResponse<GenesisKey>> {
        try {
            const response = await this.client.get(`/api/genesis/${keyId}`);
            return { success: true, data: response.data };
        } catch (error) {
            return this.handleError(error);
        }
    }

    async getCodeLineage(filePath: string, lineNumber?: number): Promise<ApiResponse<GenesisKey[]>> {
        try {
            const response = await this.client.get('/api/genesis/lineage', {
                params: { file_path: filePath, line_number: lineNumber },
            });
            return { success: true, data: response.data };
        } catch (error) {
            return this.handleError(error);
        }
    }

    async trackCodeChange(filePath: string, changes: any[], genesisKey?: string): Promise<ApiResponse<void>> {
        try {
            await this.client.post('/api/genesis/track-change', {
                file_path: filePath,
                changes,
                genesis_key: genesisKey,
            });
            return { success: true };
        } catch (error) {
            return this.handleError(error);
        }
    }

    // Diagnostic API

    async runDiagnostics(): Promise<ApiResponse<DiagnosticResult[]>> {
        try {
            const response = await this.client.post('/api/diagnostics/run');
            return { success: true, data: response.data };
        } catch (error) {
            return this.handleError(error);
        }
    }

    async getSystemHealth(): Promise<ApiResponse<any>> {
        try {
            const response = await this.client.get('/api/diagnostics/health');
            return { success: true, data: response.data };
        } catch (error) {
            return this.handleError(error);
        }
    }

    // Cognitive API

    async analyzeCode(code: string, language: string, context?: Record<string, any>): Promise<ApiResponse<CognitiveAnalysis>> {
        try {
            const response = await this.client.post('/api/cognitive/analyze', {
                code,
                language,
                context,
            });
            return { success: true, data: response.data };
        } catch (error) {
            return this.handleError(error);
        }
    }

    async explainCode(code: string, language: string): Promise<ApiResponse<string>> {
        try {
            const response = await this.client.post('/api/cognitive/explain', {
                code,
                language,
            });
            return { success: true, data: response.data };
        } catch (error) {
            return this.handleError(error);
        }
    }

    async suggestRefactoring(code: string, language: string): Promise<ApiResponse<any>> {
        try {
            const response = await this.client.post('/api/cognitive/refactor', {
                code,
                language,
            });
            return { success: true, data: response.data };
        } catch (error) {
            return this.handleError(error);
        }
    }

    // Learning API

    async recordLearningInsight(content: string, category: string, metadata?: Record<string, any>): Promise<ApiResponse<LearningInsight>> {
        try {
            const response = await this.client.post('/api/learning/record', {
                content,
                category,
                metadata,
            });
            return { success: true, data: response.data };
        } catch (error) {
            return this.handleError(error);
        }
    }

    async getLearningHistory(limit?: number): Promise<ApiResponse<LearningInsight[]>> {
        try {
            const response = await this.client.get('/api/learning/history', {
                params: { limit },
            });
            return { success: true, data: response.data };
        } catch (error) {
            return this.handleError(error);
        }
    }

    // Librarian API

    async searchKnowledgeBase(query: string, filters?: Record<string, any>): Promise<ApiResponse<any[]>> {
        try {
            const response = await this.client.post('/api/librarian/search', {
                query,
                filters,
            });
            return { success: true, data: response.data };
        } catch (error) {
            return this.handleError(error);
        }
    }

    async tagFile(filePath: string, tags: string[]): Promise<ApiResponse<void>> {
        try {
            await this.client.post('/api/librarian/tag', {
                file_path: filePath,
                tags,
            });
            return { success: true };
        } catch (error) {
            return this.handleError(error);
        }
    }

    // Whitelist API

    async proposeWhitelistEntry(content: string, category: string, metadata?: Record<string, any>): Promise<ApiResponse<any>> {
        try {
            const response = await this.client.post('/api/whitelist/propose', {
                content,
                category,
                metadata,
            });
            return { success: true, data: response.data };
        } catch (error) {
            return this.handleError(error);
        }
    }

    // CI/CD API

    async triggerCICDPipeline(pipelineId?: string): Promise<ApiResponse<any>> {
        try {
            const response = await this.client.post('/api/cicd/trigger', {
                pipeline_id: pipelineId,
            });
            return { success: true, data: response.data };
        } catch (error) {
            return this.handleError(error);
        }
    }

    // Autonomous Task API

    async scheduleTask(task: Partial<AutonomousTask>): Promise<ApiResponse<AutonomousTask>> {
        try {
            const response = await this.client.post('/api/autonomous/schedule', task);
            return { success: true, data: response.data };
        } catch (error) {
            return this.handleError(error);
        }
    }

    async getScheduledTasks(): Promise<ApiResponse<AutonomousTask[]>> {
        try {
            const response = await this.client.get('/api/autonomous/tasks');
            return { success: true, data: response.data };
        } catch (error) {
            return this.handleError(error);
        }
    }

    async cancelTask(taskId: string): Promise<ApiResponse<void>> {
        try {
            await this.client.delete(`/api/autonomous/tasks/${taskId}`);
            return { success: true };
        } catch (error) {
            return this.handleError(error);
        }
    }

    // RAG API

    async retrieveContext(query: string, topK?: number): Promise<ApiResponse<any[]>> {
        try {
            const response = await this.client.post('/api/retrieve', {
                query,
                top_k: topK || 5,
            });
            return { success: true, data: response.data };
        } catch (error) {
            return this.handleError(error);
        }
    }

    async ingestDocument(content: string, metadata?: Record<string, any>): Promise<ApiResponse<any>> {
        try {
            const response = await this.client.post('/api/ingest', {
                content,
                metadata,
            });
            return { success: true, data: response.data };
        } catch (error) {
            return this.handleError(error);
        }
    }

    // Telemetry API

    async sendTelemetry(event: string, data?: Record<string, any>): Promise<ApiResponse<void>> {
        try {
            await this.client.post('/api/telemetry/event', {
                event,
                data,
                session_id: this.core.getSession().id,
                timestamp: new Date().toISOString(),
            });
            return { success: true };
        } catch (error) {
            // Silently fail for telemetry
            return { success: false };
        }
    }

    // Agent API

    async invokeAgent(task: string, context?: Record<string, any>): Promise<ApiResponse<any>> {
        try {
            const response = await this.client.post('/api/agent/invoke', {
                task,
                context,
            });
            return { success: true, data: response.data };
        } catch (error) {
            return this.handleError(error);
        }
    }

    // Utility methods

    private handleError(error: any): ApiResponse {
        const message = error.response?.data?.message || error.message || 'Unknown error';
        const statusCode = error.response?.status;

        return {
            success: false,
            error: message,
            statusCode,
        };
    }

    isBackendConnected(): boolean {
        return this.isConnected;
    }

    getBaseUrl(): string {
        return this.core.getConfig().backendUrl;
    }
}
