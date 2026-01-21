/**
 * WebSocket Bridge
 *
 * Real-time communication channel between VSCode and Grace backend.
 * Handles streaming, events, and live updates.
 */

import * as vscode from 'vscode';
import { EventEmitter } from 'events';
import { GraceOSCore } from '../core/GraceOSCore';

export interface WebSocketMessage {
    type: string;
    payload: any;
    timestamp: string;
    sessionId?: string;
}

export interface StreamChunk {
    content: string;
    done: boolean;
    metadata?: Record<string, any>;
}

export class GraceWebSocketBridge extends EventEmitter {
    private core: GraceOSCore;
    private ws: WebSocket | null = null;
    private reconnectAttempts: number = 0;
    private maxReconnectAttempts: number = 5;
    private reconnectDelay: number = 1000;
    private pingInterval: NodeJS.Timeout | null = null;
    private messageQueue: WebSocketMessage[] = [];
    private isConnecting: boolean = false;

    constructor(core: GraceOSCore) {
        super();
        this.core = core;
    }

    async connect(): Promise<boolean> {
        if (this.ws?.readyState === WebSocket.OPEN) {
            return true;
        }

        if (this.isConnecting) {
            return false;
        }

        this.isConnecting = true;
        const config = this.core.getConfig();

        return new Promise((resolve) => {
            try {
                // Note: In VSCode extension, we use the 'ws' package
                // For browser-based code-server, we use native WebSocket
                const WebSocketImpl = typeof WebSocket !== 'undefined' ? WebSocket : require('ws');
                this.ws = new WebSocketImpl(config.wsUrl);

                this.ws.onopen = () => {
                    this.core.log('WebSocket connected');
                    this.isConnecting = false;
                    this.reconnectAttempts = 0;
                    this.startPing();
                    this.flushMessageQueue();
                    this.emit('connected');
                    resolve(true);
                };

                this.ws.onclose = (event: CloseEvent) => {
                    this.core.log(`WebSocket closed: ${event.code} - ${event.reason}`);
                    this.isConnecting = false;
                    this.stopPing();
                    this.emit('disconnected', event);
                    this.attemptReconnect();
                };

                this.ws.onerror = (error: Event) => {
                    this.core.log('WebSocket error', 'error');
                    this.isConnecting = false;
                    this.emit('error', error);
                    resolve(false);
                };

                this.ws.onmessage = (event: MessageEvent) => {
                    this.handleMessage(event.data);
                };

            } catch (error) {
                this.core.log(`WebSocket connection failed: ${error}`, 'error');
                this.isConnecting = false;
                resolve(false);
            }
        });
    }

    disconnect(): void {
        this.stopPing();
        if (this.ws) {
            this.ws.close(1000, 'Client disconnect');
            this.ws = null;
        }
    }

    private handleMessage(data: string): void {
        try {
            const message: WebSocketMessage = JSON.parse(data);
            this.core.log(`WS Message: ${message.type}`);

            switch (message.type) {
                case 'stream_chunk':
                    this.emit('streamChunk', message.payload as StreamChunk);
                    break;
                case 'stream_end':
                    this.emit('streamEnd', message.payload);
                    break;
                case 'diagnostic_update':
                    this.emit('diagnosticUpdate', message.payload);
                    break;
                case 'memory_update':
                    this.emit('memoryUpdate', message.payload);
                    break;
                case 'genesis_update':
                    this.emit('genesisUpdate', message.payload);
                    break;
                case 'learning_event':
                    this.emit('learningEvent', message.payload);
                    break;
                case 'task_update':
                    this.emit('taskUpdate', message.payload);
                    break;
                case 'notification':
                    this.handleNotification(message.payload);
                    break;
                case 'health_update':
                    this.emit('healthUpdate', message.payload);
                    break;
                case 'pong':
                    // Heartbeat response
                    break;
                default:
                    this.emit('message', message);
            }
        } catch (error) {
            this.core.log(`Failed to parse WebSocket message: ${error}`, 'error');
        }
    }

    private handleNotification(payload: any): void {
        const { level, title, message } = payload;

        switch (level) {
            case 'info':
                vscode.window.showInformationMessage(`Grace OS: ${message}`);
                break;
            case 'warning':
                vscode.window.showWarningMessage(`Grace OS: ${message}`);
                break;
            case 'error':
                vscode.window.showErrorMessage(`Grace OS: ${message}`);
                break;
        }

        this.emit('notification', payload);
    }

    private startPing(): void {
        this.pingInterval = setInterval(() => {
            this.send({ type: 'ping', payload: {}, timestamp: new Date().toISOString() });
        }, 30000);
    }

    private stopPing(): void {
        if (this.pingInterval) {
            clearInterval(this.pingInterval);
            this.pingInterval = null;
        }
    }

    private attemptReconnect(): void {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            this.core.log('Max reconnect attempts reached', 'error');
            vscode.window.showWarningMessage('Grace OS: Lost connection to backend. Some features may be unavailable.');
            return;
        }

        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

        this.core.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

        setTimeout(() => {
            this.connect();
        }, delay);
    }

    private flushMessageQueue(): void {
        while (this.messageQueue.length > 0) {
            const message = this.messageQueue.shift();
            if (message) {
                this.send(message);
            }
        }
    }

    send(message: WebSocketMessage): boolean {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            this.messageQueue.push(message);
            return false;
        }

        try {
            this.ws.send(JSON.stringify(message));
            return true;
        } catch (error) {
            this.core.log(`Failed to send WebSocket message: ${error}`, 'error');
            return false;
        }
    }

    // Convenience methods for specific message types

    sendChatMessage(content: string, context?: Record<string, any>): void {
        this.send({
            type: 'chat',
            payload: {
                content,
                context,
                session_id: this.core.getSession().id,
            },
            timestamp: new Date().toISOString(),
        });
    }

    sendCodeUpdate(filePath: string, changes: any[]): void {
        this.send({
            type: 'code_update',
            payload: {
                file_path: filePath,
                changes,
            },
            timestamp: new Date().toISOString(),
        });
    }

    requestStreamingAnalysis(code: string, language: string): void {
        this.send({
            type: 'stream_analysis',
            payload: {
                code,
                language,
            },
            timestamp: new Date().toISOString(),
        });
    }

    subscribeToUpdates(channels: string[]): void {
        this.send({
            type: 'subscribe',
            payload: { channels },
            timestamp: new Date().toISOString(),
        });
    }

    unsubscribeFromUpdates(channels: string[]): void {
        this.send({
            type: 'unsubscribe',
            payload: { channels },
            timestamp: new Date().toISOString(),
        });
    }

    isConnected(): boolean {
        return this.ws?.readyState === WebSocket.OPEN;
    }
}
