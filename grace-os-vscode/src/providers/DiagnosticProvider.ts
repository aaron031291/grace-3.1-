/**
 * Diagnostic Provider
 *
 * Integrates Grace's 4-layer diagnostic system into VSCode.
 * Provides real-time health monitoring and issue detection.
 */

import * as vscode from 'vscode';
import { GraceOSCore } from '../core/GraceOSCore';
import { IDEBridge, DiagnosticResult } from '../bridges/IDEBridge';

export interface DiagnosticNode {
    id: string;
    label: string;
    type: 'layer' | 'diagnostic' | 'recommendation';
    layer?: string;
    diagnostic?: DiagnosticResult;
    children?: DiagnosticNode[];
}

export class DiagnosticProvider implements vscode.TreeDataProvider<DiagnosticNode> {
    private core: GraceOSCore;
    private bridge: IDEBridge;
    private diagnostics: Map<string, DiagnosticResult[]> = new Map();
    private _onDidChangeTreeData = new vscode.EventEmitter<DiagnosticNode | undefined>();
    readonly onDidChangeTreeData = this._onDidChangeTreeData.event;
    private diagnosticOutputChannel: vscode.OutputChannel;

    // Grace's 4-layer diagnostic system
    private layers = [
        { id: 'sensors', name: 'Layer 1: Sensors', description: 'Raw data collection and monitoring' },
        { id: 'interpreters', name: 'Layer 2: Interpreters', description: 'Pattern recognition and analysis' },
        { id: 'judgement', name: 'Layer 3: Judgement', description: 'Decision making and assessment' },
        { id: 'actions', name: 'Layer 4: Actions', description: 'Healing and remediation' },
    ];

    constructor(core: GraceOSCore, bridge: IDEBridge) {
        this.core = core;
        this.bridge = bridge;
        this.diagnosticOutputChannel = vscode.window.createOutputChannel('Grace Diagnostics');

        // Listen for diagnostic updates
        this.core.on('diagnosticUpdate', (data: any) => {
            this.handleDiagnosticUpdate(data);
        });
    }

    private handleDiagnosticUpdate(data: any): void {
        if (data.layer && data.results) {
            this.diagnostics.set(data.layer, data.results);
            this.refresh();

            // Show notification for errors
            const errors = data.results.filter((d: DiagnosticResult) => d.status === 'error');
            if (errors.length > 0) {
                vscode.window.showWarningMessage(
                    `Grace Diagnostics: ${errors.length} issue(s) detected in ${data.layer}`
                );
            }
        }
    }

    // TreeDataProvider implementation

    getTreeItem(element: DiagnosticNode): vscode.TreeItem {
        const item = new vscode.TreeItem(element.label);

        if (element.type === 'layer') {
            item.collapsibleState = vscode.TreeItemCollapsibleState.Collapsed;

            const layerDiagnostics = this.diagnostics.get(element.layer!) || [];
            const hasErrors = layerDiagnostics.some(d => d.status === 'error');
            const hasWarnings = layerDiagnostics.some(d => d.status === 'warning');

            if (hasErrors) {
                item.iconPath = new vscode.ThemeIcon('error', new vscode.ThemeColor('errorForeground'));
            } else if (hasWarnings) {
                item.iconPath = new vscode.ThemeIcon('warning', new vscode.ThemeColor('warningForeground'));
            } else {
                item.iconPath = new vscode.ThemeIcon('check', new vscode.ThemeColor('testing.iconPassed'));
            }

            const layer = this.layers.find(l => l.id === element.layer);
            item.tooltip = layer?.description;
            item.description = `${layerDiagnostics.length} checks`;

        } else if (element.type === 'diagnostic') {
            item.collapsibleState = element.diagnostic?.recommendations?.length
                ? vscode.TreeItemCollapsibleState.Collapsed
                : vscode.TreeItemCollapsibleState.None;

            const statusIcons: Record<string, vscode.ThemeIcon> = {
                healthy: new vscode.ThemeIcon('check', new vscode.ThemeColor('testing.iconPassed')),
                warning: new vscode.ThemeIcon('warning', new vscode.ThemeColor('warningForeground')),
                error: new vscode.ThemeIcon('error', new vscode.ThemeColor('errorForeground')),
            };

            item.iconPath = statusIcons[element.diagnostic?.status || 'healthy'];
            item.tooltip = element.diagnostic?.message;

            item.command = {
                command: 'graceOS.diagnostic.viewDetail',
                title: 'View Diagnostic Detail',
                arguments: [element.diagnostic],
            };

        } else if (element.type === 'recommendation') {
            item.collapsibleState = vscode.TreeItemCollapsibleState.None;
            item.iconPath = new vscode.ThemeIcon('lightbulb');
        }

        item.contextValue = element.type;
        return item;
    }

    getChildren(element?: DiagnosticNode): DiagnosticNode[] {
        if (!element) {
            // Root level - show layers
            return this.layers.map(layer => ({
                id: layer.id,
                label: layer.name,
                type: 'layer' as const,
                layer: layer.id,
            }));
        }

        if (element.type === 'layer' && element.layer) {
            // Show diagnostics for this layer
            const layerDiagnostics = this.diagnostics.get(element.layer) || [];
            return layerDiagnostics.map((diag, index) => ({
                id: `${element.layer}-${index}`,
                label: diag.message.substring(0, 50),
                type: 'diagnostic' as const,
                diagnostic: diag,
            }));
        }

        if (element.type === 'diagnostic' && element.diagnostic?.recommendations) {
            // Show recommendations
            return element.diagnostic.recommendations.map((rec, index) => ({
                id: `${element.id}-rec-${index}`,
                label: rec,
                type: 'recommendation' as const,
            }));
        }

        return [];
    }

    // Public API

    async runDiagnostics(): Promise<void> {
        await vscode.window.withProgress(
            {
                location: vscode.ProgressLocation.Notification,
                title: 'Running Grace Diagnostics...',
                cancellable: false,
            },
            async (progress) => {
                progress.report({ message: 'Collecting system data...' });

                const response = await this.bridge.runDiagnostics();

                if (response.success && response.data) {
                    // Organize results by layer
                    this.organizeDiagnostics(response.data);

                    // Update health status
                    const hasErrors = response.data.some(d => d.status === 'error');
                    const hasWarnings = response.data.some(d => d.status === 'warning');

                    this.core.updateState({
                        healthStatus: hasErrors ? 'unhealthy' : hasWarnings ? 'degraded' : 'healthy',
                        lastHealthCheck: new Date(),
                    });

                    this.refresh();

                    // Show summary
                    const errorCount = response.data.filter(d => d.status === 'error').length;
                    const warningCount = response.data.filter(d => d.status === 'warning').length;

                    if (errorCount > 0 || warningCount > 0) {
                        vscode.window.showWarningMessage(
                            `Diagnostics complete: ${errorCount} errors, ${warningCount} warnings`
                        );
                    } else {
                        vscode.window.showInformationMessage('All systems healthy');
                    }
                } else {
                    vscode.window.showErrorMessage(`Diagnostics failed: ${response.error}`);
                }
            }
        );
    }

    private organizeDiagnostics(results: DiagnosticResult[]): void {
        this.diagnostics.clear();

        for (const result of results) {
            const layer = result.layer || 'sensors';
            const existing = this.diagnostics.get(layer) || [];
            existing.push(result);
            this.diagnostics.set(layer, existing);
        }
    }

    async viewHealth(): Promise<void> {
        await vscode.window.withProgress(
            {
                location: vscode.ProgressLocation.Notification,
                title: 'Loading system health...',
            },
            async () => {
                const response = await this.bridge.getSystemHealth();

                if (response.success && response.data) {
                    this.showHealthReport(response.data);
                } else {
                    vscode.window.showErrorMessage(`Failed to load health: ${response.error}`);
                }
            }
        );
    }

    private async showHealthReport(health: any): Promise<void> {
        this.diagnosticOutputChannel.clear();
        this.diagnosticOutputChannel.appendLine('=== Grace System Health Report ===');
        this.diagnosticOutputChannel.appendLine(`Generated: ${new Date().toLocaleString()}\n`);

        this.diagnosticOutputChannel.appendLine('--- Overall Status ---');
        this.diagnosticOutputChannel.appendLine(`Status: ${health.status || 'unknown'}`);
        this.diagnosticOutputChannel.appendLine(`Uptime: ${health.uptime || 'N/A'}`);
        this.diagnosticOutputChannel.appendLine('');

        if (health.components) {
            this.diagnosticOutputChannel.appendLine('--- Components ---');
            for (const [name, status] of Object.entries(health.components)) {
                this.diagnosticOutputChannel.appendLine(`  ${name}: ${status}`);
            }
            this.diagnosticOutputChannel.appendLine('');
        }

        if (health.metrics) {
            this.diagnosticOutputChannel.appendLine('--- Metrics ---');
            this.diagnosticOutputChannel.appendLine(JSON.stringify(health.metrics, null, 2));
        }

        this.diagnosticOutputChannel.show();
    }

    viewDiagnosticDetail(diagnostic: DiagnosticResult): void {
        this.diagnosticOutputChannel.clear();
        this.diagnosticOutputChannel.appendLine('=== Diagnostic Detail ===\n');
        this.diagnosticOutputChannel.appendLine(`Status: ${diagnostic.status}`);
        this.diagnosticOutputChannel.appendLine(`Layer: ${diagnostic.layer}`);
        this.diagnosticOutputChannel.appendLine(`Message: ${diagnostic.message}\n`);

        if (diagnostic.details) {
            this.diagnosticOutputChannel.appendLine('--- Details ---');
            this.diagnosticOutputChannel.appendLine(JSON.stringify(diagnostic.details, null, 2));
            this.diagnosticOutputChannel.appendLine('');
        }

        if (diagnostic.recommendations && diagnostic.recommendations.length > 0) {
            this.diagnosticOutputChannel.appendLine('--- Recommendations ---');
            diagnostic.recommendations.forEach((rec, i) => {
                this.diagnosticOutputChannel.appendLine(`  ${i + 1}. ${rec}`);
            });
        }

        this.diagnosticOutputChannel.show();
    }

    refresh(): void {
        this._onDidChangeTreeData.fire(undefined);
    }

    dispose(): void {
        this.diagnosticOutputChannel.dispose();
        this._onDidChangeTreeData.dispose();
    }
}
