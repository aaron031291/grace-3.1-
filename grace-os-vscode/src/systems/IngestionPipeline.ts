/**
 * Ingestion Pipeline - Full Bidirectional Sync System
 *
 * Comprehensive data flow management:
 * - IDE to Backend sync
 * - Backend to IDE sync
 * - User interaction pipeline
 * - Real-time streaming
 * - Batch processing
 * - Conflict resolution
 */

import * as vscode from 'vscode';
import { GraceOSCore } from '../core/GraceOSCore';
import { IDEBridge } from '../bridges/IDEBridge';
import { GraceWebSocketBridge } from '../bridges/WebSocketBridge';
import { DeepMagmaMemory } from './DeepMagmaMemory';

// ============================================================================
// Types
// ============================================================================

export interface IngestionConfig {
    batchSize: number;
    flushInterval: number;
    maxQueueSize: number;
    retryAttempts: number;
    retryDelay: number;
    compressionEnabled: boolean;
    encryptionEnabled: boolean;
}

export type DataSource = 'ide' | 'user' | 'backend' | 'system' | 'external';
export type DataType = 'code' | 'edit' | 'diagnostic' | 'memory' | 'event' | 'telemetry' | 'command' | 'context';
export type SyncDirection = 'upstream' | 'downstream' | 'bidirectional';

export interface DataPacket {
    id: string;
    source: DataSource;
    type: DataType;
    payload: any;
    timestamp: Date;
    priority: number;
    metadata: PacketMetadata;
}

export interface PacketMetadata {
    checksum?: string;
    compressed?: boolean;
    encrypted?: boolean;
    version?: number;
    correlationId?: string;
    sessionId?: string;
}

export interface SyncState {
    lastUpstreamSync: Date;
    lastDownstreamSync: Date;
    pendingUpstream: number;
    pendingDownstream: number;
    conflicts: SyncConflict[];
    status: 'synced' | 'syncing' | 'pending' | 'error';
}

export interface SyncConflict {
    id: string;
    type: string;
    localData: any;
    remoteData: any;
    timestamp: Date;
    resolution?: ConflictResolution;
}

export type ConflictResolution = 'local_wins' | 'remote_wins' | 'merge' | 'manual';

export interface StreamChannel {
    id: string;
    name: string;
    direction: SyncDirection;
    active: boolean;
    handlers: StreamHandler[];
    filters: StreamFilter[];
}

export interface StreamHandler {
    type: DataType;
    callback: (packet: DataPacket) => Promise<void>;
}

export interface StreamFilter {
    field: string;
    operator: 'eq' | 'ne' | 'gt' | 'lt' | 'contains' | 'regex';
    value: any;
}

export interface PipelineStats {
    packetsProcessed: number;
    bytesTransferred: number;
    upstreamLatency: number;
    downstreamLatency: number;
    errorRate: number;
    throughput: number;
}

// ============================================================================
// Ingestion Pipeline
// ============================================================================

export class IngestionPipeline {
    private core: GraceOSCore;
    private bridge: IDEBridge;
    private wsBridge: GraceWebSocketBridge;
    private memory?: DeepMagmaMemory;

    private config: IngestionConfig;
    private upstreamQueue: DataPacket[] = [];
    private downstreamQueue: DataPacket[] = [];
    private channels: Map<string, StreamChannel> = new Map();
    private syncState: SyncState;
    private stats: PipelineStats;

    private flushInterval?: NodeJS.Timeout;
    private processingUpstream: boolean = false;
    private processingDownstream: boolean = false;

    constructor(
        core: GraceOSCore,
        bridge: IDEBridge,
        wsBridge: GraceWebSocketBridge
    ) {
        this.core = core;
        this.bridge = bridge;
        this.wsBridge = wsBridge;

        this.config = {
            batchSize: 50,
            flushInterval: 5000,
            maxQueueSize: 1000,
            retryAttempts: 3,
            retryDelay: 1000,
            compressionEnabled: true,
            encryptionEnabled: false,
        };

        this.syncState = {
            lastUpstreamSync: new Date(),
            lastDownstreamSync: new Date(),
            pendingUpstream: 0,
            pendingDownstream: 0,
            conflicts: [],
            status: 'synced',
        };

        this.stats = {
            packetsProcessed: 0,
            bytesTransferred: 0,
            upstreamLatency: 0,
            downstreamLatency: 0,
            errorRate: 0,
            throughput: 0,
        };
    }

    setMemory(memory: DeepMagmaMemory): void {
        this.memory = memory;
    }

    async initialize(): Promise<void> {
        this.core.log('Initializing Ingestion Pipeline...');

        // Set up default channels
        this.setupDefaultChannels();

        // Set up IDE event listeners
        this.setupIDEListeners();

        // Set up WebSocket handlers
        this.setupWebSocketHandlers();

        // Start flush timer
        this.startFlushTimer();

        // Initial sync
        await this.performFullSync();

        this.core.enableFeature('ingestionPipeline');
        this.core.log('Ingestion Pipeline initialized');
    }

    // ============================================================================
    // Channel Management
    // ============================================================================

    private setupDefaultChannels(): void {
        // Code changes channel
        this.registerChannel({
            id: 'code_changes',
            name: 'Code Changes',
            direction: 'upstream',
            active: true,
            handlers: [
                { type: 'code', callback: this.handleCodeChange.bind(this) },
                { type: 'edit', callback: this.handleEdit.bind(this) },
            ],
            filters: [],
        });

        // Diagnostics channel
        this.registerChannel({
            id: 'diagnostics',
            name: 'Diagnostics',
            direction: 'bidirectional',
            active: true,
            handlers: [
                { type: 'diagnostic', callback: this.handleDiagnostic.bind(this) },
            ],
            filters: [],
        });

        // Memory sync channel
        this.registerChannel({
            id: 'memory_sync',
            name: 'Memory Sync',
            direction: 'bidirectional',
            active: true,
            handlers: [
                { type: 'memory', callback: this.handleMemorySync.bind(this) },
            ],
            filters: [],
        });

        // Events channel
        this.registerChannel({
            id: 'events',
            name: 'System Events',
            direction: 'bidirectional',
            active: true,
            handlers: [
                { type: 'event', callback: this.handleEvent.bind(this) },
            ],
            filters: [],
        });

        // Telemetry channel
        this.registerChannel({
            id: 'telemetry',
            name: 'Telemetry',
            direction: 'upstream',
            active: true,
            handlers: [
                { type: 'telemetry', callback: this.handleTelemetry.bind(this) },
            ],
            filters: [],
        });

        // Commands channel
        this.registerChannel({
            id: 'commands',
            name: 'Commands',
            direction: 'downstream',
            active: true,
            handlers: [
                { type: 'command', callback: this.handleCommand.bind(this) },
            ],
            filters: [],
        });

        // Context channel
        this.registerChannel({
            id: 'context',
            name: 'Context Updates',
            direction: 'bidirectional',
            active: true,
            handlers: [
                { type: 'context', callback: this.handleContext.bind(this) },
            ],
            filters: [],
        });
    }

    registerChannel(channel: StreamChannel): void {
        this.channels.set(channel.id, channel);
        this.core.log(`Registered channel: ${channel.name}`);
    }

    enableChannel(channelId: string): void {
        const channel = this.channels.get(channelId);
        if (channel) {
            channel.active = true;
        }
    }

    disableChannel(channelId: string): void {
        const channel = this.channels.get(channelId);
        if (channel) {
            channel.active = false;
        }
    }

    // ============================================================================
    // IDE Event Listeners
    // ============================================================================

    private setupIDEListeners(): void {
        // Document changes
        vscode.workspace.onDidChangeTextDocument(event => {
            if (event.contentChanges.length > 0) {
                this.ingest({
                    source: 'ide',
                    type: 'edit',
                    payload: {
                        uri: event.document.uri.toString(),
                        languageId: event.document.languageId,
                        changes: event.contentChanges.map(c => ({
                            range: {
                                start: { line: c.range.start.line, character: c.range.start.character },
                                end: { line: c.range.end.line, character: c.range.end.character },
                            },
                            text: c.text,
                        })),
                        version: event.document.version,
                    },
                    priority: 5,
                });
            }
        });

        // Document saves
        vscode.workspace.onDidSaveTextDocument(doc => {
            this.ingest({
                source: 'ide',
                type: 'code',
                payload: {
                    uri: doc.uri.toString(),
                    languageId: doc.languageId,
                    content: doc.getText(),
                    action: 'save',
                },
                priority: 7,
            });
        });

        // File operations
        vscode.workspace.onDidCreateFiles(event => {
            for (const uri of event.files) {
                this.ingest({
                    source: 'ide',
                    type: 'event',
                    payload: {
                        event: 'file_created',
                        uri: uri.toString(),
                    },
                    priority: 6,
                });
            }
        });

        vscode.workspace.onDidDeleteFiles(event => {
            for (const uri of event.files) {
                this.ingest({
                    source: 'ide',
                    type: 'event',
                    payload: {
                        event: 'file_deleted',
                        uri: uri.toString(),
                    },
                    priority: 6,
                });
            }
        });

        vscode.workspace.onDidRenameFiles(event => {
            for (const { oldUri, newUri } of event.files) {
                this.ingest({
                    source: 'ide',
                    type: 'event',
                    payload: {
                        event: 'file_renamed',
                        oldUri: oldUri.toString(),
                        newUri: newUri.toString(),
                    },
                    priority: 6,
                });
            }
        });

        // Diagnostics
        vscode.languages.onDidChangeDiagnostics(event => {
            for (const uri of event.uris) {
                const diagnostics = vscode.languages.getDiagnostics(uri);
                this.ingest({
                    source: 'ide',
                    type: 'diagnostic',
                    payload: {
                        uri: uri.toString(),
                        diagnostics: diagnostics.map(d => ({
                            severity: d.severity,
                            message: d.message,
                            range: {
                                start: { line: d.range.start.line, character: d.range.start.character },
                                end: { line: d.range.end.line, character: d.range.end.character },
                            },
                            source: d.source,
                            code: d.code,
                        })),
                    },
                    priority: 4,
                });
            }
        });

        // Selection changes
        vscode.window.onDidChangeTextEditorSelection(event => {
            this.ingest({
                source: 'ide',
                type: 'context',
                payload: {
                    uri: event.textEditor.document.uri.toString(),
                    selections: event.selections.map(s => ({
                        anchor: { line: s.anchor.line, character: s.anchor.character },
                        active: { line: s.active.line, character: s.active.character },
                    })),
                },
                priority: 2,
            });
        });

        // Active editor changes
        vscode.window.onDidChangeActiveTextEditor(editor => {
            if (editor) {
                this.ingest({
                    source: 'ide',
                    type: 'context',
                    payload: {
                        event: 'active_editor_changed',
                        uri: editor.document.uri.toString(),
                        languageId: editor.document.languageId,
                    },
                    priority: 3,
                });
            }
        });

        // Terminal events
        vscode.window.onDidOpenTerminal(terminal => {
            this.ingest({
                source: 'ide',
                type: 'event',
                payload: {
                    event: 'terminal_opened',
                    name: terminal.name,
                },
                priority: 3,
            });
        });

        vscode.window.onDidCloseTerminal(terminal => {
            this.ingest({
                source: 'ide',
                type: 'event',
                payload: {
                    event: 'terminal_closed',
                    name: terminal.name,
                },
                priority: 3,
            });
        });
    }

    // ============================================================================
    // WebSocket Handlers
    // ============================================================================

    private setupWebSocketHandlers(): void {
        // Handle incoming messages from backend
        this.wsBridge.on('message', async (data: any) => {
            if (data.type === 'sync_packet') {
                await this.receiveDownstream(data.packet);
            } else if (data.type === 'command') {
                await this.ingestDownstream({
                    source: 'backend',
                    type: 'command',
                    payload: data.payload,
                    priority: 8,
                });
            } else if (data.type === 'memory_update') {
                await this.ingestDownstream({
                    source: 'backend',
                    type: 'memory',
                    payload: data.payload,
                    priority: 5,
                });
            } else if (data.type === 'context_update') {
                await this.ingestDownstream({
                    source: 'backend',
                    type: 'context',
                    payload: data.payload,
                    priority: 4,
                });
            }
        });

        // Subscribe to relevant channels
        this.wsBridge.subscribeToUpdates([
            'ingestion',
            'sync',
            'commands',
            'memory',
            'context',
        ]);
    }

    // ============================================================================
    // Ingestion API
    // ============================================================================

    ingest(options: {
        source: DataSource;
        type: DataType;
        payload: any;
        priority?: number;
        metadata?: Partial<PacketMetadata>;
    }): string {
        const packet: DataPacket = {
            id: `pkt_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            source: options.source,
            type: options.type,
            payload: options.payload,
            timestamp: new Date(),
            priority: options.priority || 5,
            metadata: {
                sessionId: this.core.getState().sessionId,
                version: 1,
                ...options.metadata,
            },
        };

        // Apply compression if enabled
        if (this.config.compressionEnabled && packet.payload) {
            packet.metadata.compressed = true;
            // Note: actual compression would be applied here
        }

        // Calculate checksum
        packet.metadata.checksum = this.calculateChecksum(packet.payload);

        // Add to upstream queue
        this.upstreamQueue.push(packet);
        this.upstreamQueue.sort((a, b) => b.priority - a.priority);

        // Trim queue if too large
        if (this.upstreamQueue.length > this.config.maxQueueSize) {
            this.upstreamQueue = this.upstreamQueue.slice(0, this.config.maxQueueSize);
        }

        this.syncState.pendingUpstream = this.upstreamQueue.length;

        // Immediate flush for high priority
        if (packet.priority >= 8) {
            this.flushUpstream();
        }

        return packet.id;
    }

    private async ingestDownstream(options: {
        source: DataSource;
        type: DataType;
        payload: any;
        priority?: number;
    }): Promise<void> {
        const packet: DataPacket = {
            id: `pkt_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            source: options.source,
            type: options.type,
            payload: options.payload,
            timestamp: new Date(),
            priority: options.priority || 5,
            metadata: {},
        };

        this.downstreamQueue.push(packet);
        this.downstreamQueue.sort((a, b) => b.priority - a.priority);

        this.syncState.pendingDownstream = this.downstreamQueue.length;

        // Process immediately for high priority
        if (packet.priority >= 8) {
            await this.processDownstream();
        }
    }

    // ============================================================================
    // Upstream Processing (IDE → Backend)
    // ============================================================================

    private startFlushTimer(): void {
        this.flushInterval = setInterval(() => {
            this.flushUpstream();
            this.processDownstream();
        }, this.config.flushInterval);
    }

    private async flushUpstream(): Promise<void> {
        if (this.processingUpstream || this.upstreamQueue.length === 0) return;

        this.processingUpstream = true;
        this.syncState.status = 'syncing';
        const startTime = Date.now();

        try {
            // Get batch
            const batch = this.upstreamQueue.splice(0, this.config.batchSize);

            // Send to backend
            const response = await this.bridge.invokeAgent('ingest_batch', {
                packets: batch,
                timestamp: new Date().toISOString(),
            });

            if (response.success) {
                // Process each packet through channels
                for (const packet of batch) {
                    await this.routeToChannel(packet);
                }

                this.stats.packetsProcessed += batch.length;
                this.stats.bytesTransferred += JSON.stringify(batch).length;
            } else {
                // Put packets back in queue
                this.upstreamQueue.unshift(...batch);
                this.stats.errorRate = (this.stats.errorRate * 0.9) + (1 * 0.1);
            }

            const latency = Date.now() - startTime;
            this.stats.upstreamLatency = (this.stats.upstreamLatency * 0.9) + (latency * 0.1);

            this.syncState.lastUpstreamSync = new Date();
            this.syncState.pendingUpstream = this.upstreamQueue.length;

        } catch (error: any) {
            this.core.log(`Upstream flush error: ${error.message}`, 'error');
            this.stats.errorRate = (this.stats.errorRate * 0.9) + (1 * 0.1);
        } finally {
            this.processingUpstream = false;
            this.syncState.status = this.upstreamQueue.length === 0 ? 'synced' : 'pending';
        }
    }

    // ============================================================================
    // Downstream Processing (Backend → IDE)
    // ============================================================================

    private async receiveDownstream(packet: DataPacket): Promise<void> {
        // Verify checksum
        if (packet.metadata.checksum) {
            const calculated = this.calculateChecksum(packet.payload);
            if (calculated !== packet.metadata.checksum) {
                this.core.log('Checksum mismatch on downstream packet', 'warn');
                return;
            }
        }

        await this.ingestDownstream({
            source: packet.source,
            type: packet.type,
            payload: packet.payload,
            priority: packet.priority,
        });
    }

    private async processDownstream(): Promise<void> {
        if (this.processingDownstream || this.downstreamQueue.length === 0) return;

        this.processingDownstream = true;
        const startTime = Date.now();

        try {
            const batch = this.downstreamQueue.splice(0, this.config.batchSize);

            for (const packet of batch) {
                await this.routeToChannel(packet);
            }

            this.stats.packetsProcessed += batch.length;

            const latency = Date.now() - startTime;
            this.stats.downstreamLatency = (this.stats.downstreamLatency * 0.9) + (latency * 0.1);

            this.syncState.lastDownstreamSync = new Date();
            this.syncState.pendingDownstream = this.downstreamQueue.length;

        } catch (error: any) {
            this.core.log(`Downstream processing error: ${error.message}`, 'error');
        } finally {
            this.processingDownstream = false;
        }
    }

    // ============================================================================
    // Channel Routing
    // ============================================================================

    private async routeToChannel(packet: DataPacket): Promise<void> {
        for (const channel of this.channels.values()) {
            if (!channel.active) continue;

            // Check direction
            const isUpstream = packet.source === 'ide' || packet.source === 'user';
            if (isUpstream && channel.direction === 'downstream') continue;
            if (!isUpstream && channel.direction === 'upstream') continue;

            // Apply filters
            if (!this.passesFilters(packet, channel.filters)) continue;

            // Find and execute handler
            const handler = channel.handlers.find(h => h.type === packet.type);
            if (handler) {
                try {
                    await handler.callback(packet);
                } catch (error: any) {
                    this.core.log(`Channel handler error: ${error.message}`, 'error');
                }
            }
        }
    }

    private passesFilters(packet: DataPacket, filters: StreamFilter[]): boolean {
        for (const filter of filters) {
            const value = this.getNestedValue(packet, filter.field);

            switch (filter.operator) {
                case 'eq':
                    if (value !== filter.value) return false;
                    break;
                case 'ne':
                    if (value === filter.value) return false;
                    break;
                case 'gt':
                    if (value <= filter.value) return false;
                    break;
                case 'lt':
                    if (value >= filter.value) return false;
                    break;
                case 'contains':
                    if (!String(value).includes(filter.value)) return false;
                    break;
                case 'regex':
                    if (!new RegExp(filter.value).test(String(value))) return false;
                    break;
            }
        }
        return true;
    }

    private getNestedValue(obj: any, path: string): any {
        return path.split('.').reduce((o, p) => o?.[p], obj);
    }

    // ============================================================================
    // Channel Handlers
    // ============================================================================

    private async handleCodeChange(packet: DataPacket): Promise<void> {
        // Store code changes to memory
        if (this.memory && packet.payload.content) {
            await this.memory.store(
                `Code update: ${packet.payload.uri}`,
                'episodic',
                {
                    uri: packet.payload.uri,
                    language: packet.payload.languageId,
                    action: packet.payload.action,
                }
            );
        }
    }

    private async handleEdit(packet: DataPacket): Promise<void> {
        // Track edit patterns
        this.core.emit('editRecorded', packet.payload);
    }

    private async handleDiagnostic(packet: DataPacket): Promise<void> {
        // Forward to diagnostic system
        this.core.emit('diagnosticsUpdated', packet.payload);
    }

    private async handleMemorySync(packet: DataPacket): Promise<void> {
        if (packet.source === 'backend' && this.memory) {
            // Sync memory from backend
            if (packet.payload.operation === 'store') {
                await this.memory.store(
                    packet.payload.content,
                    packet.payload.type,
                    packet.payload.metadata
                );
            }
        }
    }

    private async handleEvent(packet: DataPacket): Promise<void> {
        // Emit event through core
        this.core.emit('pipelineEvent', packet.payload);
    }

    private async handleTelemetry(packet: DataPacket): Promise<void> {
        // Send telemetry to backend
        this.bridge.sendTelemetry(packet.payload.event, packet.payload.data);
    }

    private async handleCommand(packet: DataPacket): Promise<void> {
        // Execute command from backend
        const { command, args } = packet.payload;

        try {
            if (command.startsWith('grace.')) {
                await vscode.commands.executeCommand(command, ...args);
            } else if (command === 'showMessage') {
                vscode.window.showInformationMessage(args[0]);
            } else if (command === 'openFile') {
                const doc = await vscode.workspace.openTextDocument(vscode.Uri.file(args[0]));
                await vscode.window.showTextDocument(doc);
            } else if (command === 'applyEdit') {
                await this.applyRemoteEdit(args[0]);
            }
        } catch (error: any) {
            this.core.log(`Command execution error: ${error.message}`, 'error');
        }
    }

    private async handleContext(packet: DataPacket): Promise<void> {
        // Update context
        this.core.emit('contextUpdated', packet.payload);
    }

    private async applyRemoteEdit(edit: {
        uri: string;
        changes: Array<{
            range: { start: { line: number; character: number }; end: { line: number; character: number } };
            text: string;
        }>;
    }): Promise<void> {
        const uri = vscode.Uri.parse(edit.uri);
        const doc = await vscode.workspace.openTextDocument(uri);
        const workspaceEdit = new vscode.WorkspaceEdit();

        for (const change of edit.changes) {
            const range = new vscode.Range(
                change.range.start.line,
                change.range.start.character,
                change.range.end.line,
                change.range.end.character
            );
            workspaceEdit.replace(uri, range, change.text);
        }

        await vscode.workspace.applyEdit(workspaceEdit);
    }

    // ============================================================================
    // Full Sync
    // ============================================================================

    async performFullSync(): Promise<void> {
        this.core.log('Performing full sync...');
        this.syncState.status = 'syncing';

        try {
            // Sync workspace state
            const workspaceFolders = vscode.workspace.workspaceFolders || [];

            const workspaceData = {
                folders: workspaceFolders.map(f => ({
                    name: f.name,
                    uri: f.uri.toString(),
                })),
                openFiles: vscode.workspace.textDocuments
                    .filter(d => d.uri.scheme === 'file')
                    .map(d => ({
                        uri: d.uri.toString(),
                        languageId: d.languageId,
                        isDirty: d.isDirty,
                        version: d.version,
                    })),
                activeFile: vscode.window.activeTextEditor?.document.uri.toString(),
            };

            await this.bridge.invokeAgent('full_sync', {
                workspace: workspaceData,
                timestamp: new Date().toISOString(),
            });

            this.syncState.status = 'synced';
            this.core.log('Full sync completed');

        } catch (error: any) {
            this.syncState.status = 'error';
            this.core.log(`Full sync error: ${error.message}`, 'error');
        }
    }

    // ============================================================================
    // Conflict Resolution
    // ============================================================================

    detectConflict(localData: any, remoteData: any, type: string): SyncConflict | null {
        // Simple timestamp-based conflict detection
        if (localData.timestamp && remoteData.timestamp) {
            const localTime = new Date(localData.timestamp).getTime();
            const remoteTime = new Date(remoteData.timestamp).getTime();

            if (Math.abs(localTime - remoteTime) < 1000) {
                // Concurrent modification
                return {
                    id: `conflict_${Date.now()}`,
                    type,
                    localData,
                    remoteData,
                    timestamp: new Date(),
                };
            }
        }

        return null;
    }

    async resolveConflict(conflictId: string, resolution: ConflictResolution): Promise<boolean> {
        const conflict = this.syncState.conflicts.find(c => c.id === conflictId);
        if (!conflict) return false;

        try {
            switch (resolution) {
                case 'local_wins':
                    await this.bridge.invokeAgent('resolve_conflict', {
                        conflictId,
                        data: conflict.localData,
                    });
                    break;
                case 'remote_wins':
                    // Apply remote data locally
                    await this.applyRemoteData(conflict.remoteData);
                    break;
                case 'merge':
                    const merged = this.mergeData(conflict.localData, conflict.remoteData);
                    await this.bridge.invokeAgent('resolve_conflict', {
                        conflictId,
                        data: merged,
                    });
                    await this.applyRemoteData(merged);
                    break;
            }

            conflict.resolution = resolution;
            this.syncState.conflicts = this.syncState.conflicts.filter(c => c.id !== conflictId);

            return true;
        } catch (error: any) {
            this.core.log(`Conflict resolution error: ${error.message}`, 'error');
            return false;
        }
    }

    private async applyRemoteData(data: any): Promise<void> {
        // Generic application of remote data
        if (data.type === 'file_content') {
            const uri = vscode.Uri.parse(data.uri);
            const edit = new vscode.WorkspaceEdit();
            const doc = await vscode.workspace.openTextDocument(uri);
            const fullRange = new vscode.Range(0, 0, doc.lineCount, 0);
            edit.replace(uri, fullRange, data.content);
            await vscode.workspace.applyEdit(edit);
        }
    }

    private mergeData(local: any, remote: any): any {
        // Simple merge strategy - combine both with timestamp markers
        return {
            ...local,
            ...remote,
            _merged: true,
            _mergeTimestamp: new Date().toISOString(),
            _localVersion: local,
            _remoteVersion: remote,
        };
    }

    // ============================================================================
    // Utilities
    // ============================================================================

    private calculateChecksum(data: any): string {
        const str = JSON.stringify(data);
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash;
        }
        return hash.toString(16);
    }

    // ============================================================================
    // Public API
    // ============================================================================

    getSyncState(): SyncState {
        return { ...this.syncState };
    }

    getStats(): PipelineStats {
        const now = Date.now();
        const elapsed = (now - (this.stats as any)._startTime) || 1;
        this.stats.throughput = (this.stats.packetsProcessed / elapsed) * 1000;

        return { ...this.stats };
    }

    getChannels(): StreamChannel[] {
        return Array.from(this.channels.values());
    }

    async forceFlush(): Promise<void> {
        await this.flushUpstream();
        await this.processDownstream();
    }

    dispose(): void {
        if (this.flushInterval) {
            clearInterval(this.flushInterval);
        }

        // Final flush
        this.flushUpstream();
    }
}
