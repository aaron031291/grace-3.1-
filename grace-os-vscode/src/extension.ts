/**
 * Grace OS VSCode Extension
 *
 * Main entry point for the Grace Operating System integrated into VSCode.
 * Brings the entire Grace cognitive infrastructure through the IDE.
 */

import * as vscode from 'vscode';
import { GraceOSCore } from './core/GraceOSCore';
import { IDEBridge } from './bridges/IDEBridge';
import { GhostLedger } from './core/GhostLedger';
import { CognitiveIDEProvider } from './providers/CognitiveIDEProvider';
import { MemoryMeshProvider } from './providers/MemoryMeshProvider';
import { GenesisKeyProvider } from './providers/GenesisKeyProvider';
import { DiagnosticProvider } from './providers/DiagnosticProvider';
import { LearningProvider } from './providers/LearningProvider';
import { AutonomousScheduler } from './core/AutonomousScheduler';
import { GraceChatPanel } from './panels/GraceChatPanel';
import { GraceDashboardPanel } from './panels/GraceDashboardPanel';
import { GraceWebSocketBridge } from './bridges/WebSocketBridge';
import { registerCommands } from './commands/registerCommands';
import { InlineCodeIntelligence } from './providers/InlineCodeIntelligence';
import { GraceStatusBar } from './core/GraceStatusBar';

let graceOS: GraceOSCore | undefined;

export async function activate(context: vscode.ExtensionContext): Promise<void> {
    console.log('Grace OS: Activating cognitive IDE...');

    try {
        // Initialize core Grace OS system
        graceOS = new GraceOSCore(context);
        await graceOS.initialize();

        // Initialize IDE Bridge
        const ideBridge = new IDEBridge(graceOS);
        await ideBridge.connect();

        // Initialize WebSocket bridge for real-time communication
        const wsBridge = new GraceWebSocketBridge(graceOS);
        await wsBridge.connect();

        // Initialize Ghost Ledger for line-by-line tracking
        const ghostLedger = new GhostLedger(graceOS, context);
        await ghostLedger.initialize();

        // Initialize Cognitive IDE Provider
        const cognitiveProvider = new CognitiveIDEProvider(graceOS, ideBridge);
        await cognitiveProvider.initialize();

        // Initialize Memory Mesh Provider
        const memoryProvider = new MemoryMeshProvider(graceOS, ideBridge);
        const memoryTreeProvider = vscode.window.registerTreeDataProvider(
            'graceOS.memory',
            memoryProvider
        );

        // Initialize Genesis Key Provider
        const genesisProvider = new GenesisKeyProvider(graceOS, ideBridge);
        const genesisTreeProvider = vscode.window.registerTreeDataProvider(
            'graceOS.genesis',
            genesisProvider
        );

        // Initialize Diagnostic Provider
        const diagnosticProvider = new DiagnosticProvider(graceOS, ideBridge);
        const diagnosticTreeProvider = vscode.window.registerTreeDataProvider(
            'graceOS.diagnostics',
            diagnosticProvider
        );

        // Initialize Learning Provider
        const learningProvider = new LearningProvider(graceOS, ideBridge);
        const learningTreeProvider = vscode.window.registerTreeDataProvider(
            'graceOS.learning',
            learningProvider
        );

        // Initialize Autonomous Scheduler
        const autonomousScheduler = new AutonomousScheduler(graceOS, ideBridge);
        const tasksTreeProvider = vscode.window.registerTreeDataProvider(
            'graceOS.tasks',
            autonomousScheduler
        );

        // Initialize Inline Code Intelligence
        const inlineIntelligence = new InlineCodeIntelligence(graceOS, cognitiveProvider);
        await inlineIntelligence.initialize();

        // Initialize Status Bar
        const statusBar = new GraceStatusBar(graceOS);
        statusBar.show();

        // Register webview providers
        const dashboardProvider = new GraceDashboardPanel(graceOS, context);
        const dashboardWebviewProvider = vscode.window.registerWebviewViewProvider(
            'graceOS.dashboard',
            dashboardProvider
        );

        const chatProvider = new GraceChatPanel(graceOS, context, wsBridge);
        const chatWebviewProvider = vscode.window.registerWebviewViewProvider(
            'graceOS.chat',
            chatProvider
        );

        // Register all commands
        const commandDisposables = registerCommands(
            context,
            graceOS,
            ideBridge,
            ghostLedger,
            cognitiveProvider,
            memoryProvider,
            genesisProvider,
            diagnosticProvider,
            learningProvider,
            autonomousScheduler
        );

        // Store all components in context for cleanup
        context.subscriptions.push(
            memoryTreeProvider,
            genesisTreeProvider,
            diagnosticTreeProvider,
            learningTreeProvider,
            tasksTreeProvider,
            dashboardWebviewProvider,
            chatWebviewProvider,
            ...commandDisposables,
            { dispose: () => graceOS?.dispose() },
            { dispose: () => ideBridge.disconnect() },
            { dispose: () => wsBridge.disconnect() },
            { dispose: () => ghostLedger.dispose() },
            { dispose: () => cognitiveProvider.dispose() },
            { dispose: () => inlineIntelligence.dispose() },
            { dispose: () => statusBar.dispose() },
            { dispose: () => autonomousScheduler.dispose() }
        );

        // Start autonomous scheduler if enabled
        const config = vscode.workspace.getConfiguration('graceOS');
        if (config.get<boolean>('autonomous.enabled')) {
            await autonomousScheduler.start();
        }

        // Notify user
        vscode.window.showInformationMessage('Grace OS: Cognitive IDE activated');
        console.log('Grace OS: Activation complete');

    } catch (error) {
        console.error('Grace OS: Activation failed:', error);
        vscode.window.showErrorMessage(`Grace OS: Failed to activate - ${error}`);
    }
}

export function deactivate(): void {
    console.log('Grace OS: Deactivating...');
    if (graceOS) {
        graceOS.dispose();
        graceOS = undefined;
    }
}
