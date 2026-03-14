/**
 * Grace OS Integration Module
 *
 * Unifies all Grace systems into a cohesive IDE experience.
 * This module ties together:
 * - Core orchestration
 * - All 4-layer diagnostics
 * - Security systems
 * - Enterprise agent
 * - Self-healing
 * - TimeSense and OODA
 * - Clarity Framework
 * - Deep Magma Memory (4 relation types)
 * - Oracle ML Intelligence
 * - Neural-Symbolic AI
 * - Sandbox Lab
 * - Proactive Learning
 * - Ingestion Pipeline
 */

import * as vscode from 'vscode';
import { GraceOSCore } from './core/GraceOSCore';
import { GhostLedger } from './core/GhostLedger';
import { AutonomousScheduler } from './core/AutonomousScheduler';
import { IDEBridge } from './bridges/IDEBridge';
import { GraceWebSocketBridge } from './bridges/WebSocketBridge';

// Systems
import { DiagnosticMachine } from './systems/DiagnosticMachine';
import { SecurityLayer } from './systems/SecurityLayer';
import { EnterpriseAgent } from './systems/EnterpriseAgent';
import { SelfHealingSystem } from './systems/SelfHealingSystem';
import { TimeSense, OODALoop } from './systems/TimeSenseOODA';
import { ClarityFramework } from './systems/ClarityFramework';
import { DeepMagmaMemory } from './systems/DeepMagmaMemory';
import { OracleMLIntelligence } from './systems/OracleMLIntelligence';
import { NeuralSymbolicAI } from './systems/NeuralSymbolicAI';
import { SandboxLab } from './systems/SandboxLab';
import { ProactiveLearning } from './systems/ProactiveLearning';
import { IngestionPipeline } from './systems/IngestionPipeline';

// Providers
import { CognitiveIDEProvider } from './providers/CognitiveIDEProvider';
import { MemoryMeshProvider } from './providers/MemoryMeshProvider';
import { GenesisKeyProvider } from './providers/GenesisKeyProvider';
import { DiagnosticProvider } from './providers/DiagnosticProvider';
import { LearningProvider } from './providers/LearningProvider';
import { InlineCodeIntelligence } from './providers/InlineCodeIntelligence';

// Panels
import { GraceChatPanel } from './panels/GraceChatPanel';
import { GraceDashboardPanel } from './panels/GraceDashboardPanel';

// ============================================================================
// Types
// ============================================================================

export interface IntegrationConfig {
    enableAllSystems: boolean;
    enabledSystems?: string[];
    autoConnect: boolean;
    autoHeal: boolean;
    enableTelemetry: boolean;
}

export interface SystemStatus {
    name: string;
    status: 'active' | 'inactive' | 'error';
    initialized: boolean;
    lastActivity?: Date;
    metrics?: Record<string, any>;
}

export interface IntegrationState {
    initialized: boolean;
    connected: boolean;
    systems: Map<string, SystemStatus>;
    errors: string[];
    startTime: Date;
}

// ============================================================================
// Grace OS Integration
// ============================================================================

export class GraceOSIntegration {
    private context: vscode.ExtensionContext;
    private state: IntegrationState;

    // Core
    private core!: GraceOSCore;
    private ghostLedger!: GhostLedger;
    private scheduler!: AutonomousScheduler;

    // Bridges
    private ideBridge!: IDEBridge;
    private wsBridge!: GraceWebSocketBridge;

    // Systems
    private diagnosticMachine!: DiagnosticMachine;
    private securityLayer!: SecurityLayer;
    private enterpriseAgent!: EnterpriseAgent;
    private selfHealing!: SelfHealingSystem;
    private timeSense!: TimeSense;
    private oodaLoop!: OODALoop;
    private clarityFramework!: ClarityFramework;
    private magmaMemory!: DeepMagmaMemory;
    private oracleML!: OracleMLIntelligence;
    private neuralSymbolic!: NeuralSymbolicAI;
    private sandboxLab!: SandboxLab;
    private proactiveLearning!: ProactiveLearning;
    private ingestionPipeline!: IngestionPipeline;

    // Providers
    private cognitiveProvider!: CognitiveIDEProvider;
    private memoryProvider!: MemoryMeshProvider;
    private genesisProvider!: GenesisKeyProvider;
    private diagnosticProvider!: DiagnosticProvider;
    private learningProvider!: LearningProvider;
    private inlineIntelligence!: InlineCodeIntelligence;

    constructor(context: vscode.ExtensionContext) {
        this.context = context;
        this.state = {
            initialized: false,
            connected: false,
            systems: new Map(),
            errors: [],
            startTime: new Date(),
        };
    }

    // ============================================================================
    // Initialization
    // ============================================================================

    async initialize(config: IntegrationConfig = {
        enableAllSystems: true,
        autoConnect: true,
        autoHeal: true,
        enableTelemetry: true,
    }): Promise<boolean> {
        try {
            this.logIntegration('Grace OS Integration starting...');

            // Initialize core
            await this.initializeCore();

            // Initialize bridges
            await this.initializeBridges(config.autoConnect);

            // Initialize systems
            await this.initializeSystems(config);

            // Initialize providers
            await this.initializeProviders();

            // Set up cross-system connections
            await this.setupSystemConnections();

            // Register commands
            this.registerCommands();

            // Start autonomous operations
            if (config.autoHeal) {
                this.startAutonomousOperations();
            }

            this.state.initialized = true;
            this.logIntegration('Grace OS Integration complete');

            return true;
        } catch (error: any) {
            this.state.errors.push(error.message);
            this.logIntegration(`Integration failed: ${error.message}`, 'error');
            return false;
        }
    }

    private async initializeCore(): Promise<void> {
        this.logIntegration('Initializing core systems...');

        this.core = new GraceOSCore(this.context);
        this.updateSystemStatus('core', 'active', true);

        this.ghostLedger = new GhostLedger(this.core);
        await this.ghostLedger.initialize();
        this.updateSystemStatus('ghostLedger', 'active', true);

        this.scheduler = new AutonomousScheduler(this.core);
        await this.scheduler.initialize();
        this.updateSystemStatus('scheduler', 'active', true);
    }

    private async initializeBridges(autoConnect: boolean): Promise<void> {
        this.logIntegration('Initializing communication bridges...');

        this.ideBridge = new IDEBridge(this.core);
        this.wsBridge = new GraceWebSocketBridge(this.core);

        if (autoConnect) {
            const httpConnected = await this.ideBridge.connect();
            const wsConnected = await this.wsBridge.connect();

            this.state.connected = httpConnected;
            this.updateSystemStatus('ideBridge', httpConnected ? 'active' : 'error', true);
            this.updateSystemStatus('wsBridge', wsConnected ? 'active' : 'inactive', true);
        }
    }

    private async initializeSystems(config: IntegrationConfig): Promise<void> {
        this.logIntegration('Initializing Grace systems...');

        const systemsToInit = config.enableAllSystems
            ? ['all']
            : (config.enabledSystems || []);

        const shouldInit = (name: string) =>
            systemsToInit.includes('all') || systemsToInit.includes(name);

        // Diagnostic Machine (Layer 1-4)
        if (shouldInit('diagnostics')) {
            this.diagnosticMachine = new DiagnosticMachine(this.core, this.ideBridge);
            await this.diagnosticMachine.initialize();
            this.updateSystemStatus('diagnosticMachine', 'active', true);
        }

        // Security Layer (RBAC, Auth, Validation)
        if (shouldInit('security')) {
            this.securityLayer = new SecurityLayer(this.core, this.ideBridge);
            await this.securityLayer.initialize();
            this.updateSystemStatus('securityLayer', 'active', true);
        }

        // Enterprise Agent
        if (shouldInit('agent')) {
            this.enterpriseAgent = new EnterpriseAgent(this.core, this.ideBridge);
            await this.enterpriseAgent.initialize();
            this.updateSystemStatus('enterpriseAgent', 'active', true);
        }

        // Self-Healing System
        if (shouldInit('selfHealing')) {
            this.selfHealing = new SelfHealingSystem(this.core, this.ideBridge, this.wsBridge);
            this.selfHealing.setDiagnosticMachine(this.diagnosticMachine);
            await this.selfHealing.initialize();
            this.updateSystemStatus('selfHealing', 'active', true);
        }

        // TimeSense and OODA Loop
        if (shouldInit('timeSense')) {
            this.timeSense = new TimeSense(this.core);
            await this.timeSense.initialize();
            this.updateSystemStatus('timeSense', 'active', true);

            this.oodaLoop = new OODALoop(this.core, this.ideBridge, this.timeSense);
            await this.oodaLoop.initialize();
            this.updateSystemStatus('oodaLoop', 'active', true);
        }

        // Clarity Framework
        if (shouldInit('clarity')) {
            this.clarityFramework = new ClarityFramework(this.core);
            await this.clarityFramework.initialize();
            this.updateSystemStatus('clarityFramework', 'active', true);
        }

        // Deep Magma Memory (4 relation types)
        if (shouldInit('memory')) {
            this.magmaMemory = new DeepMagmaMemory(this.core, this.ideBridge);
            await this.magmaMemory.initialize();
            this.updateSystemStatus('magmaMemory', 'active', true);
        }

        // Oracle ML Intelligence
        if (shouldInit('oracle')) {
            this.oracleML = new OracleMLIntelligence(this.core, this.ideBridge);
            await this.oracleML.initialize();
            this.updateSystemStatus('oracleML', 'active', true);
        }

        // Neural-Symbolic AI
        if (shouldInit('neuralSymbolic')) {
            this.neuralSymbolic = new NeuralSymbolicAI(this.core);
            await this.neuralSymbolic.initialize();
            this.updateSystemStatus('neuralSymbolic', 'active', true);
        }

        // Sandbox Lab
        if (shouldInit('sandbox')) {
            this.sandboxLab = new SandboxLab(this.core, this.ideBridge);
            await this.sandboxLab.initialize();
            this.updateSystemStatus('sandboxLab', 'active', true);
        }

        // Proactive Learning
        if (shouldInit('learning')) {
            this.proactiveLearning = new ProactiveLearning(this.core, this.ideBridge);
            this.proactiveLearning.setMemory(this.magmaMemory);
            await this.proactiveLearning.initialize();
            this.updateSystemStatus('proactiveLearning', 'active', true);
        }

        // Ingestion Pipeline
        if (shouldInit('ingestion')) {
            this.ingestionPipeline = new IngestionPipeline(this.core, this.ideBridge, this.wsBridge);
            this.ingestionPipeline.setMemory(this.magmaMemory);
            await this.ingestionPipeline.initialize();
            this.updateSystemStatus('ingestionPipeline', 'active', true);
        }
    }

    private async initializeProviders(): Promise<void> {
        this.logIntegration('Initializing IDE providers...');

        // Cognitive provider
        this.cognitiveProvider = new CognitiveIDEProvider(this.core, this.ideBridge);
        await this.cognitiveProvider.initialize();
        this.updateSystemStatus('cognitiveProvider', 'active', true);

        // Memory mesh provider (matches package.json view id: graceOS.memory)
        this.memoryProvider = new MemoryMeshProvider(this.core, this.ideBridge);
        this.context.subscriptions.push(
            vscode.window.registerTreeDataProvider('graceOS.memory', this.memoryProvider)
        );
        await this.memoryProvider.initialize();
        this.updateSystemStatus('memoryProvider', 'active', true);

        // Genesis key provider (matches package.json view id: graceOS.genesis)
        this.genesisProvider = new GenesisKeyProvider(this.core, this.ideBridge);
        this.context.subscriptions.push(
            vscode.window.registerTreeDataProvider('graceOS.genesis', this.genesisProvider)
        );
        this.updateSystemStatus('genesisProvider', 'active', true);

        // Diagnostic provider (matches package.json view id: graceOS.diagnostics)
        this.diagnosticProvider = new DiagnosticProvider(this.core, this.ideBridge);
        this.context.subscriptions.push(
            vscode.window.registerTreeDataProvider('graceOS.diagnostics', this.diagnosticProvider)
        );
        this.updateSystemStatus('diagnosticProvider', 'active', true);

        // Learning provider (matches package.json view id: graceOS.learning)
        this.learningProvider = new LearningProvider(this.core, this.ideBridge);
        this.context.subscriptions.push(
            vscode.window.registerTreeDataProvider('graceOS.learning', this.learningProvider)
        );
        this.updateSystemStatus('learningProvider', 'active', true);

        // Inline code intelligence
        this.inlineIntelligence = new InlineCodeIntelligence(this.core, this.ideBridge);
        await this.inlineIntelligence.register(this.context);
        this.updateSystemStatus('inlineIntelligence', 'active', true);
    }

    private async setupSystemConnections(): Promise<void> {
        this.logIntegration('Setting up cross-system connections...');

        // Connect memory to learning
        if (this.proactiveLearning && this.magmaMemory) {
            this.proactiveLearning.setMemory(this.magmaMemory);
        }

        // Connect diagnostic to self-healing
        if (this.selfHealing && this.diagnosticMachine) {
            this.selfHealing.setDiagnosticMachine(this.diagnosticMachine);
        }

        // Connect Oracle to Memory for predictions
        if (this.oracleML && this.magmaMemory) {
            this.oracleML.setMemory(this.magmaMemory);
        }

        // Connect Neural-Symbolic to Memory
        if (this.neuralSymbolic && this.magmaMemory) {
            this.neuralSymbolic.setMemory(this.magmaMemory);
        }

        // Connect OODA to Clarity for decision transparency
        if (this.oodaLoop && this.clarityFramework) {
            this.oodaLoop.setClarityFramework(this.clarityFramework);
        }

        // Connect Ingestion to Memory
        if (this.ingestionPipeline && this.magmaMemory) {
            this.ingestionPipeline.setMemory(this.magmaMemory);
        }

        // Set up event forwarding
        this.setupEventForwarding();
    }

    private setupEventForwarding(): void {
        // Forward diagnostic events to self-healing
        this.core.on('diagnosticComplete', async (state) => {
            if (this.selfHealing && (state.overallHealth === 'unhealthy' || state.overallHealth === 'critical')) {
                this.logIntegration('Triggering self-healing from diagnostic event');
                // Self-healing will handle based on patterns
            }
        });

        // Forward learning to Oracle for prediction updates
        this.core.on('learningComplete', async (result) => {
            if (this.oracleML) {
                await this.oracleML.integrateLearnedPatterns(result.patternsLearned);
            }
        });

        // Forward code changes to genesis tracking
        this.core.on('codeChanged', async (change) => {
            if (this.ghostLedger) {
                await this.ghostLedger.trackChange(change);
            }
        });

        // Forward user feedback to learning
        this.core.on('userFeedback', async (feedback) => {
            if (this.proactiveLearning) {
                this.proactiveLearning.recordFeedback(
                    feedback.target,
                    feedback.rating,
                    'explicit',
                    feedback.comment
                );
            }
        });
    }

    private registerCommands(): void {
        // Register all graceOS.* commands from package.json using registerCommands helper
        const { registerCommands } = require('./commands/registerCommands');
        const disposables = registerCommands(
            this.context,
            this.core,
            this.ideBridge,
            this.ghostLedger,
            this.cognitiveProvider,
            this.memoryProvider,
            this.genesisProvider,
            this.diagnosticProvider,
            this.learningProvider,
            this.scheduler,
        );
        this.context.subscriptions.push(...disposables);

        // Register chat webview provider for sidebar
        const chatProvider = new GraceChatPanel(this.core, this.context, this.wsBridge);
        this.context.subscriptions.push(
            vscode.window.registerWebviewViewProvider('graceOS.chat', chatProvider)
        );

        // Additional system commands
        this.context.subscriptions.push(
            vscode.commands.registerCommand('grace.showDashboard', () => {
                this.showSystemStatus();
            })
        );

        this.context.subscriptions.push(
            vscode.commands.registerCommand('grace.showChat', () => {
                vscode.commands.executeCommand('graceOS.chat.focus');
            })
        );

        this.context.subscriptions.push(
            vscode.commands.registerCommand('grace.runDiagnostics', async () => {
                if (this.diagnosticMachine) {
                    const state = await this.diagnosticMachine.runCycle();
                    vscode.window.showInformationMessage(`Diagnostics: ${state.overallHealth}`);
                }
            })
        );

        this.context.subscriptions.push(
            vscode.commands.registerCommand('grace.triggerHealing', async () => {
                if (this.selfHealing) {
                    await this.selfHealing.manualHeal('connection_recovery');
                    vscode.window.showInformationMessage('Self-healing triggered');
                }
            })
        );

        this.context.subscriptions.push(
            vscode.commands.registerCommand('grace.queryMemory', async () => {
                const query = await vscode.window.showInputBox({
                    prompt: 'Enter memory query',
                    placeHolder: 'Search memories...',
                });
                if (query && this.magmaMemory) {
                    const results = await this.magmaMemory.query(query);
                    vscode.window.showInformationMessage(`Found ${results.length} memories`);
                }
            })
        );

        this.context.subscriptions.push(
            vscode.commands.registerCommand('grace.showOracleInsights', async () => {
                if (this.oracleML) {
                    const insights = await this.oracleML.getInsights();
                    const panel = vscode.window.createWebviewPanel(
                        'graceOracle',
                        'Oracle Insights',
                        vscode.ViewColumn.Two,
                        {}
                    );
                    panel.webview.html = `<pre>${JSON.stringify(insights, null, 2)}</pre>`;
                }
            })
        );

        this.context.subscriptions.push(
            vscode.commands.registerCommand('grace.startExperiment', async () => {
                const name = await vscode.window.showInputBox({
                    prompt: 'Experiment name',
                });
                if (name && this.sandboxLab) {
                    const experiment = this.sandboxLab.createExperiment(name, 'code_change');
                    vscode.window.showInformationMessage(`Created experiment: ${experiment.id}`);
                }
            })
        );

        this.context.subscriptions.push(
            vscode.commands.registerCommand('grace.getSystemStatus', () => {
                this.showSystemStatus();
            })
        );
    }

    private startAutonomousOperations(): void {
        this.logIntegration('Starting autonomous operations...');

        // Schedule periodic diagnostics
        this.scheduler.scheduleTask({
            id: 'periodic_diagnostics',
            name: 'Periodic Diagnostics',
            handler: async () => {
                if (this.diagnosticMachine) {
                    await this.diagnosticMachine.runCycle();
                }
            },
            interval: 60000, // Every minute
            priority: 5,
        });

        // Schedule memory consolidation
        this.scheduler.scheduleTask({
            id: 'memory_consolidation',
            name: 'Memory Consolidation',
            handler: async () => {
                if (this.magmaMemory) {
                    await this.magmaMemory.consolidate();
                }
            },
            interval: 300000, // Every 5 minutes
            priority: 3,
        });

        // Schedule OODA cycle
        this.scheduler.scheduleTask({
            id: 'ooda_cycle',
            name: 'OODA Cycle',
            handler: async () => {
                if (this.oodaLoop) {
                    await this.oodaLoop.runCycle({
                        trigger: 'scheduled',
                        priority: 'normal',
                    });
                }
            },
            interval: 30000, // Every 30 seconds
            priority: 7,
        });
    }

    // ============================================================================
    // Status and Monitoring
    // ============================================================================

    private updateSystemStatus(name: string, status: 'active' | 'inactive' | 'error', initialized: boolean): void {
        this.state.systems.set(name, {
            name,
            status,
            initialized,
            lastActivity: new Date(),
        });
    }

    private showSystemStatus(): void {
        const statusItems: string[] = [];

        for (const [name, status] of this.state.systems) {
            const icon = status.status === 'active' ? '✓' : status.status === 'error' ? '✗' : '○';
            statusItems.push(`${icon} ${name}: ${status.status}`);
        }

        const panel = vscode.window.createWebviewPanel(
            'graceStatus',
            'Grace OS Status',
            vscode.ViewColumn.Two,
            {}
        );

        panel.webview.html = `
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body { font-family: system-ui; padding: 20px; }
                    .system { padding: 10px; margin: 5px 0; border-radius: 5px; }
                    .active { background: #1a3d1a; }
                    .inactive { background: #3d3d1a; }
                    .error { background: #3d1a1a; }
                </style>
            </head>
            <body>
                <h1>Grace OS System Status</h1>
                <p>Initialized: ${this.state.initialized}</p>
                <p>Connected: ${this.state.connected}</p>
                <p>Uptime: ${Math.floor((Date.now() - this.state.startTime.getTime()) / 1000)}s</p>
                <h2>Systems</h2>
                ${Array.from(this.state.systems.values()).map(s => `
                    <div class="system ${s.status}">
                        <strong>${s.name}</strong>: ${s.status}
                        <br><small>Initialized: ${s.initialized}</small>
                    </div>
                `).join('')}
            </body>
            </html>
        `;
    }

    // ============================================================================
    // Public API
    // ============================================================================

    getState(): IntegrationState {
        return { ...this.state };
    }

    getCore(): GraceOSCore {
        return this.core;
    }

    getBridge(): IDEBridge {
        return this.ideBridge;
    }

    getMemory(): DeepMagmaMemory {
        return this.magmaMemory;
    }

    getDiagnostics(): DiagnosticMachine {
        return this.diagnosticMachine;
    }

    getOracle(): OracleMLIntelligence {
        return this.oracleML;
    }

    getAgent(): EnterpriseAgent {
        return this.enterpriseAgent;
    }

    private logIntegration(message: string, level: 'info' | 'warn' | 'error' = 'info'): void {
        const prefix = '[Grace Integration]';
        if (this.core) {
            this.core.log(`${prefix} ${message}`, level);
        } else {
            console.log(`${prefix} ${message}`);
        }
    }

    // ============================================================================
    // Cleanup
    // ============================================================================

    dispose(): void {
        this.logIntegration('Disposing Grace OS Integration...');

        // Dispose systems in reverse order
        this.ingestionPipeline?.dispose();
        this.proactiveLearning?.dispose();
        this.sandboxLab?.dispose();
        this.neuralSymbolic?.dispose();
        this.oracleML?.dispose();
        this.magmaMemory?.dispose();
        this.clarityFramework?.dispose();
        this.oodaLoop?.dispose();
        this.timeSense?.dispose();
        this.selfHealing?.dispose();
        this.enterpriseAgent?.dispose();
        this.securityLayer?.dispose();
        this.diagnosticMachine?.dispose();

        // Dispose core
        this.scheduler?.dispose();
        this.ghostLedger?.dispose();
        this.wsBridge?.disconnect();
        this.core?.dispose();

        this.state.initialized = false;
    }
}

// ============================================================================
// Factory Export
// ============================================================================

export async function createGraceOSIntegration(
    context: vscode.ExtensionContext,
    config?: IntegrationConfig
): Promise<GraceOSIntegration> {
    const integration = new GraceOSIntegration(context);
    await integration.initialize(config);
    return integration;
}
