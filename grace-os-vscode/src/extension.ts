/**
 * Grace OS VSCode Extension
 *
 * Main entry point for the Grace Operating System integrated into VSCode.
 * Brings the entire Grace cognitive infrastructure through the IDE.
 *
 * Full System Integration:
 * - Layer 1-4 Diagnostic Machine (Sensors → Interpreters → Judgement → Actions)
 * - Security Layers (RBAC, Authentication, Validation, Secret Detection)
 * - Enterprise Coding Agent with full execution capabilities
 * - Self-Healing System with autonomous repair
 * - TimeSense temporal reasoning and OODA loop
 * - Clarity Framework for transparent decision making
 * - Deep Magma Memory Mesh (4 relation types: semantic, temporal, causal, entity)
 * - Oracle ML Intelligence (predictions, trust scoring, bandits, anomaly detection)
 * - Neural-Symbolic AI reasoning layer
 * - Sandbox Lab for safe experimentation
 * - Proactive Learning with autonomous improvements
 * - Full Ingestion Pipeline with bidirectional sync
 */

import * as vscode from 'vscode';
import { GraceOSIntegration, createGraceOSIntegration } from './GraceOSIntegration';
import { GraceStatusBar } from './core/GraceStatusBar';

let graceOSIntegration: GraceOSIntegration | undefined;

export async function activate(context: vscode.ExtensionContext): Promise<void> {
    console.log('Grace OS: Activating cognitive IDE with full system integration...');

    try {
        // Initialize complete Grace OS integration
        // This unifies all systems:
        // - Core, GhostLedger, AutonomousScheduler
        // - IDEBridge, WebSocketBridge
        // - DiagnosticMachine (4 layers)
        // - SecurityLayer (RBAC, Auth, Validation, Secrets)
        // - EnterpriseAgent (full execution)
        // - SelfHealingSystem
        // - TimeSense + OODALoop
        // - ClarityFramework
        // - DeepMagmaMemory (4 relation types)
        // - OracleMLIntelligence
        // - NeuralSymbolicAI
        // - SandboxLab
        // - ProactiveLearning
        // - IngestionPipeline
        graceOSIntegration = await createGraceOSIntegration(context, {
            enableAllSystems: true,
            autoConnect: true,
            autoHeal: true,
            enableTelemetry: true,
        });

        // Initialize Status Bar
        const statusBar = new GraceStatusBar(graceOSIntegration.getCore());
        statusBar.show();

        // Add status bar to subscriptions
        context.subscriptions.push(
            { dispose: () => statusBar.dispose() },
            { dispose: () => graceOSIntegration?.dispose() }
        );

        // Notify user
        vscode.window.showInformationMessage('Grace OS: Full cognitive IDE activated');
        console.log('Grace OS: Activation complete with all systems integrated');

    } catch (error) {
        console.error('Grace OS: Activation failed:', error);
        vscode.window.showErrorMessage(`Grace OS: Failed to activate - ${error}`);
    }
}

export function deactivate(): void {
    console.log('Grace OS: Deactivating...');
    if (graceOSIntegration) {
        graceOSIntegration.dispose();
        graceOSIntegration = undefined;
    }
}

// Export integration for external access
export function getGraceOSIntegration(): GraceOSIntegration | undefined {
    return graceOSIntegration;
}
