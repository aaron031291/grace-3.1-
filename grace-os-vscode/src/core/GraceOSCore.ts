/**
 * Grace OS Core
 *
 * Central orchestrator for the Grace Operating System in VSCode.
 * Manages state, configuration, and coordinates all Grace subsystems.
 */

import * as vscode from 'vscode';
import { EventEmitter } from 'events';
import { v4 as uuidv4 } from 'uuid';

export interface GraceConfig {
    backendUrl: string;
    wsUrl: string;
    autoActivate: boolean;
    ghostLedger: {
        enabled: boolean;
        showInlineAnnotations: boolean;
    };
    memory: {
        autoStore: boolean;
        consolidationInterval: number;
    };
    cognitive: {
        inlineSuggestions: boolean;
        autoAnalyze: boolean;
    };
    genesis: {
        autoTrack: boolean;
        showLineage: boolean;
    };
    diagnostics: {
        autoRun: boolean;
        interval: number;
    };
    learning: {
        recordPatterns: boolean;
    };
    autonomous: {
        enabled: boolean;
    };
    telemetry: {
        enabled: boolean;
    };
}

export interface GraceSession {
    id: string;
    startTime: Date;
    workspaceUri?: vscode.Uri;
    activeFile?: string;
    userId?: string;
}

export interface GraceState {
    isConnected: boolean;
    isAuthenticated: boolean;
    activeFeatures: Set<string>;
    lastHealthCheck?: Date;
    healthStatus: 'healthy' | 'degraded' | 'unhealthy' | 'unknown';
    pendingTasks: number;
    memoryUsage: number;
    activeGenesisKeys: number;
}

export class GraceOSCore extends EventEmitter {
    private context: vscode.ExtensionContext;
    private config: GraceConfig;
    private session: GraceSession;
    private state: GraceState;
    private configChangeListener: vscode.Disposable;
    private diagnosticCollection: vscode.DiagnosticCollection;
    private outputChannel: vscode.OutputChannel;

    constructor(context: vscode.ExtensionContext) {
        super();
        this.context = context;
        this.config = this.loadConfig();
        this.session = this.createSession();
        this.state = this.initializeState();

        // Create output channel for Grace OS logs
        this.outputChannel = vscode.window.createOutputChannel('Grace OS');

        // Create diagnostic collection
        this.diagnosticCollection = vscode.languages.createDiagnosticCollection('graceOS');

        // Listen for config changes
        this.configChangeListener = vscode.workspace.onDidChangeConfiguration(e => {
            if (e.affectsConfiguration('graceOS')) {
                this.config = this.loadConfig();
                this.emit('configChanged', this.config);
                this.log('Configuration updated');
            }
        });
    }

    async initialize(): Promise<void> {
        this.log('Initializing Grace OS Core...');

        // Restore persisted state
        await this.restoreState();

        // Set up workspace listeners
        this.setupWorkspaceListeners();

        // Initialize telemetry if enabled
        if (this.config.telemetry.enabled) {
            await this.initializeTelemetry();
        }

        this.log('Grace OS Core initialized');
        this.emit('initialized');
    }

    private loadConfig(): GraceConfig {
        const vsConfig = vscode.workspace.getConfiguration('graceOS');

        return {
            backendUrl: vsConfig.get<string>('backendUrl') || 'http://localhost:8000',
            wsUrl: vsConfig.get<string>('wsUrl') || 'ws://localhost:8000/ws',
            autoActivate: vsConfig.get<boolean>('autoActivate') ?? true,
            ghostLedger: {
                enabled: vsConfig.get<boolean>('ghostLedger.enabled') ?? true,
                showInlineAnnotations: vsConfig.get<boolean>('ghostLedger.showInlineAnnotations') ?? true,
            },
            memory: {
                autoStore: vsConfig.get<boolean>('memory.autoStore') ?? true,
                consolidationInterval: vsConfig.get<number>('memory.consolidationInterval') ?? 300000,
            },
            cognitive: {
                inlineSuggestions: vsConfig.get<boolean>('cognitive.inlineSuggestions') ?? true,
                autoAnalyze: vsConfig.get<boolean>('cognitive.autoAnalyze') ?? false,
            },
            genesis: {
                autoTrack: vsConfig.get<boolean>('genesis.autoTrack') ?? true,
                showLineage: vsConfig.get<boolean>('genesis.showLineage') ?? true,
            },
            diagnostics: {
                autoRun: vsConfig.get<boolean>('diagnostics.autoRun') ?? true,
                interval: vsConfig.get<number>('diagnostics.interval') ?? 60000,
            },
            learning: {
                recordPatterns: vsConfig.get<boolean>('learning.recordPatterns') ?? true,
            },
            autonomous: {
                enabled: vsConfig.get<boolean>('autonomous.enabled') ?? true,
            },
            telemetry: {
                enabled: vsConfig.get<boolean>('telemetry.enabled') ?? true,
            },
        };
    }

    private createSession(): GraceSession {
        return {
            id: uuidv4(),
            startTime: new Date(),
            workspaceUri: vscode.workspace.workspaceFolders?.[0]?.uri,
        };
    }

    private initializeState(): GraceState {
        return {
            isConnected: false,
            isAuthenticated: false,
            activeFeatures: new Set(),
            healthStatus: 'unknown',
            pendingTasks: 0,
            memoryUsage: 0,
            activeGenesisKeys: 0,
        };
    }

    private async restoreState(): Promise<void> {
        const persistedState = this.context.globalState.get<Partial<GraceState>>('graceOS.state');
        if (persistedState) {
            this.state = { ...this.state, ...persistedState };
        }
    }

    private async persistState(): Promise<void> {
        await this.context.globalState.update('graceOS.state', {
            activeFeatures: Array.from(this.state.activeFeatures),
            healthStatus: this.state.healthStatus,
        });
    }

    private setupWorkspaceListeners(): void {
        // Track active editor changes
        vscode.window.onDidChangeActiveTextEditor(editor => {
            if (editor) {
                this.session.activeFile = editor.document.uri.fsPath;
                this.emit('activeFileChanged', this.session.activeFile);
            }
        });

        // Track document changes
        vscode.workspace.onDidChangeTextDocument(event => {
            this.emit('documentChanged', event);
        });

        // Track document saves
        vscode.workspace.onDidSaveTextDocument(document => {
            this.emit('documentSaved', document);
        });

        // Track workspace folder changes
        vscode.workspace.onDidChangeWorkspaceFolders(event => {
            this.emit('workspaceChanged', event);
        });
    }

    private async initializeTelemetry(): Promise<void> {
        // Telemetry initialization for Grace backend
        this.log('Telemetry initialized');
    }

    // Public API

    getConfig(): GraceConfig {
        return { ...this.config };
    }

    getSession(): GraceSession {
        return { ...this.session };
    }

    getState(): GraceState {
        return { ...this.state };
    }

    getContext(): vscode.ExtensionContext {
        return this.context;
    }

    getDiagnosticCollection(): vscode.DiagnosticCollection {
        return this.diagnosticCollection;
    }

    updateState(updates: Partial<GraceState>): void {
        this.state = { ...this.state, ...updates };
        this.emit('stateChanged', this.state);
        this.persistState();
    }

    setConnected(connected: boolean): void {
        this.state.isConnected = connected;
        this.emit('connectionChanged', connected);
    }

    setAuthenticated(authenticated: boolean): void {
        this.state.isAuthenticated = authenticated;
        this.emit('authenticationChanged', authenticated);
    }

    enableFeature(feature: string): void {
        this.state.activeFeatures.add(feature);
        this.emit('featureEnabled', feature);
    }

    disableFeature(feature: string): void {
        this.state.activeFeatures.delete(feature);
        this.emit('featureDisabled', feature);
    }

    isFeatureEnabled(feature: string): boolean {
        return this.state.activeFeatures.has(feature);
    }

    log(message: string, level: 'info' | 'warn' | 'error' = 'info'): void {
        const timestamp = new Date().toISOString();
        const formatted = `[${timestamp}] [${level.toUpperCase()}] ${message}`;
        this.outputChannel.appendLine(formatted);

        if (level === 'error') {
            console.error(`Grace OS: ${message}`);
        } else {
            console.log(`Grace OS: ${message}`);
        }
    }

    showOutput(): void {
        this.outputChannel.show();
    }

    // Storage helpers

    async getStoredData<T>(key: string): Promise<T | undefined> {
        return this.context.globalState.get<T>(`graceOS.${key}`);
    }

    async setStoredData<T>(key: string, value: T): Promise<void> {
        await this.context.globalState.update(`graceOS.${key}`, value);
    }

    async getWorkspaceData<T>(key: string): Promise<T | undefined> {
        return this.context.workspaceState.get<T>(`graceOS.${key}`);
    }

    async setWorkspaceData<T>(key: string, value: T): Promise<void> {
        await this.context.workspaceState.update(`graceOS.${key}`, value);
    }

    dispose(): void {
        this.configChangeListener.dispose();
        this.diagnosticCollection.dispose();
        this.outputChannel.dispose();
        this.removeAllListeners();
    }
}
