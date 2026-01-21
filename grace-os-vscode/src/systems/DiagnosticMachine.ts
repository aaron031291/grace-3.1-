/**
 * Diagnostic Machine - Full 4-Layer Integration
 *
 * Complete integration with Grace's diagnostic system:
 * Layer 1: Sensors - Raw data collection and monitoring
 * Layer 2: Interpreters - Pattern recognition and analysis
 * Layer 3: Judgement - Decision making and assessment
 * Layer 4: Actions - Healing and remediation
 */

import * as vscode from 'vscode';
import { GraceOSCore } from '../core/GraceOSCore';
import { IDEBridge } from '../bridges/IDEBridge';
import { GraceWebSocketBridge } from '../bridges/WebSocketBridge';

// ============================================================================
// Types
// ============================================================================

export interface SensorReading {
    id: string;
    sensorType: string;
    value: any;
    timestamp: string;
    metadata?: Record<string, any>;
}

export interface InterpretedPattern {
    id: string;
    patternType: string;
    confidence: number;
    sourceReadings: string[];
    interpretation: string;
    severity: 'info' | 'warning' | 'error' | 'critical';
}

export interface JudgementDecision {
    id: string;
    patterns: string[];
    decision: string;
    reasoning: string;
    confidence: number;
    recommendedActions: string[];
    urgency: 'low' | 'medium' | 'high' | 'critical';
}

export interface HealingAction {
    id: string;
    type: string;
    target: string;
    status: 'pending' | 'executing' | 'completed' | 'failed';
    result?: any;
    timestamp: string;
}

export interface DiagnosticState {
    layer1: SensorReading[];
    layer2: InterpretedPattern[];
    layer3: JudgementDecision[];
    layer4: HealingAction[];
    overallHealth: 'healthy' | 'degraded' | 'unhealthy' | 'critical';
    lastUpdate: Date;
}

// ============================================================================
// Layer 1: Sensors
// ============================================================================

export class SensorLayer {
    private core: GraceOSCore;
    private readings: Map<string, SensorReading[]> = new Map();
    private sensorTypes = [
        'system_metrics',
        'code_quality',
        'error_rates',
        'response_times',
        'memory_usage',
        'cognitive_load',
        'learning_progress',
        'security_events',
    ];

    constructor(core: GraceOSCore) {
        this.core = core;
    }

    async collectReadings(): Promise<SensorReading[]> {
        const readings: SensorReading[] = [];

        // System metrics sensor
        readings.push(await this.collectSystemMetrics());

        // Code quality sensor (from current file)
        const editor = vscode.window.activeTextEditor;
        if (editor) {
            readings.push(await this.collectCodeQualityMetrics(editor));
        }

        // Extension performance sensor
        readings.push(await this.collectExtensionMetrics());

        // Error rate sensor
        readings.push(await this.collectErrorRates());

        return readings;
    }

    private async collectSystemMetrics(): Promise<SensorReading> {
        return {
            id: `sensor_${Date.now()}_system`,
            sensorType: 'system_metrics',
            value: {
                activeEditors: vscode.window.visibleTextEditors.length,
                openDocuments: vscode.workspace.textDocuments.length,
                workspaceFolders: vscode.workspace.workspaceFolders?.length || 0,
                diagnosticCount: vscode.languages.getDiagnostics().length,
            },
            timestamp: new Date().toISOString(),
        };
    }

    private async collectCodeQualityMetrics(editor: vscode.TextEditor): Promise<SensorReading> {
        const doc = editor.document;
        const text = doc.getText();
        const lines = text.split('\n');

        // Calculate metrics
        const metrics = {
            lineCount: lines.length,
            characterCount: text.length,
            emptyLines: lines.filter(l => l.trim() === '').length,
            avgLineLength: text.length / lines.length,
            diagnostics: vscode.languages.getDiagnostics(doc.uri).length,
            complexityIndicators: this.detectComplexity(text),
        };

        return {
            id: `sensor_${Date.now()}_code`,
            sensorType: 'code_quality',
            value: metrics,
            timestamp: new Date().toISOString(),
            metadata: { filePath: doc.uri.fsPath, language: doc.languageId },
        };
    }

    private detectComplexity(code: string): Record<string, number> {
        return {
            nestingDepth: (code.match(/\{/g) || []).length,
            conditionals: (code.match(/if\s*\(|switch\s*\(|\?/g) || []).length,
            loops: (code.match(/for\s*\(|while\s*\(|\.forEach|\.map|\.filter/g) || []).length,
            functions: (code.match(/function\s+|=>\s*\{|async\s+/g) || []).length,
        };
    }

    private async collectExtensionMetrics(): Promise<SensorReading> {
        const state = this.core.getState();

        return {
            id: `sensor_${Date.now()}_ext`,
            sensorType: 'extension_metrics',
            value: {
                isConnected: state.isConnected,
                activeFeatures: Array.from(state.activeFeatures),
                pendingTasks: state.pendingTasks,
                healthStatus: state.healthStatus,
            },
            timestamp: new Date().toISOString(),
        };
    }

    private async collectErrorRates(): Promise<SensorReading> {
        // Collect error diagnostics across workspace
        const allDiagnostics = vscode.languages.getDiagnostics();
        let errorCount = 0;
        let warningCount = 0;

        for (const [_, diagnostics] of allDiagnostics) {
            for (const diag of diagnostics) {
                if (diag.severity === vscode.DiagnosticSeverity.Error) errorCount++;
                if (diag.severity === vscode.DiagnosticSeverity.Warning) warningCount++;
            }
        }

        return {
            id: `sensor_${Date.now()}_errors`,
            sensorType: 'error_rates',
            value: {
                errors: errorCount,
                warnings: warningCount,
                total: errorCount + warningCount,
            },
            timestamp: new Date().toISOString(),
        };
    }
}

// ============================================================================
// Layer 2: Interpreters
// ============================================================================

export class InterpreterLayer {
    private core: GraceOSCore;

    constructor(core: GraceOSCore) {
        this.core = core;
    }

    async interpretReadings(readings: SensorReading[]): Promise<InterpretedPattern[]> {
        const patterns: InterpretedPattern[] = [];

        // Interpret each reading
        for (const reading of readings) {
            const interpreted = await this.interpretReading(reading);
            if (interpreted) {
                patterns.push(interpreted);
            }
        }

        // Cross-reading pattern detection
        const crossPatterns = await this.detectCrossPatterns(readings);
        patterns.push(...crossPatterns);

        return patterns;
    }

    private async interpretReading(reading: SensorReading): Promise<InterpretedPattern | null> {
        switch (reading.sensorType) {
            case 'code_quality':
                return this.interpretCodeQuality(reading);
            case 'error_rates':
                return this.interpretErrorRates(reading);
            case 'extension_metrics':
                return this.interpretExtensionMetrics(reading);
            default:
                return null;
        }
    }

    private interpretCodeQuality(reading: SensorReading): InterpretedPattern | null {
        const { value } = reading;
        const complexity = value.complexityIndicators;

        // Detect high complexity
        if (complexity.nestingDepth > 10 || complexity.conditionals > 15) {
            return {
                id: `pattern_${Date.now()}_complexity`,
                patternType: 'high_complexity',
                confidence: 0.85,
                sourceReadings: [reading.id],
                interpretation: `High code complexity detected: ${complexity.nestingDepth} nesting levels, ${complexity.conditionals} conditionals`,
                severity: complexity.nestingDepth > 15 ? 'warning' : 'info',
            };
        }

        // Detect large file
        if (value.lineCount > 500) {
            return {
                id: `pattern_${Date.now()}_large_file`,
                patternType: 'large_file',
                confidence: 0.9,
                sourceReadings: [reading.id],
                interpretation: `Large file detected: ${value.lineCount} lines`,
                severity: value.lineCount > 1000 ? 'warning' : 'info',
            };
        }

        return null;
    }

    private interpretErrorRates(reading: SensorReading): InterpretedPattern | null {
        const { value } = reading;

        if (value.errors > 0) {
            return {
                id: `pattern_${Date.now()}_errors`,
                patternType: 'active_errors',
                confidence: 1.0,
                sourceReadings: [reading.id],
                interpretation: `${value.errors} errors and ${value.warnings} warnings detected`,
                severity: value.errors > 5 ? 'error' : 'warning',
            };
        }

        return null;
    }

    private interpretExtensionMetrics(reading: SensorReading): InterpretedPattern | null {
        const { value } = reading;

        if (!value.isConnected) {
            return {
                id: `pattern_${Date.now()}_disconnected`,
                patternType: 'backend_disconnected',
                confidence: 1.0,
                sourceReadings: [reading.id],
                interpretation: 'Grace backend connection lost',
                severity: 'error',
            };
        }

        return null;
    }

    private async detectCrossPatterns(readings: SensorReading[]): Promise<InterpretedPattern[]> {
        const patterns: InterpretedPattern[] = [];

        // Detect correlation between complexity and errors
        const codeReading = readings.find(r => r.sensorType === 'code_quality');
        const errorReading = readings.find(r => r.sensorType === 'error_rates');

        if (codeReading && errorReading) {
            const complexity = codeReading.value.complexityIndicators;
            const errors = errorReading.value.errors;

            if (complexity.nestingDepth > 5 && errors > 3) {
                patterns.push({
                    id: `pattern_${Date.now()}_complexity_errors`,
                    patternType: 'complexity_error_correlation',
                    confidence: 0.75,
                    sourceReadings: [codeReading.id, errorReading.id],
                    interpretation: 'High complexity correlating with error count - refactoring may help',
                    severity: 'warning',
                });
            }
        }

        return patterns;
    }
}

// ============================================================================
// Layer 3: Judgement
// ============================================================================

export class JudgementLayer {
    private core: GraceOSCore;
    private bridge: IDEBridge;

    constructor(core: GraceOSCore, bridge: IDEBridge) {
        this.core = core;
        this.bridge = bridge;
    }

    async makeDecisions(patterns: InterpretedPattern[]): Promise<JudgementDecision[]> {
        const decisions: JudgementDecision[] = [];

        // Group patterns by severity
        const criticalPatterns = patterns.filter(p => p.severity === 'critical');
        const errorPatterns = patterns.filter(p => p.severity === 'error');
        const warningPatterns = patterns.filter(p => p.severity === 'warning');

        // Critical decisions
        for (const pattern of criticalPatterns) {
            decisions.push(await this.createDecision(pattern, 'critical'));
        }

        // Error decisions
        for (const pattern of errorPatterns) {
            decisions.push(await this.createDecision(pattern, 'high'));
        }

        // Warning decisions (batched)
        if (warningPatterns.length > 0) {
            decisions.push(await this.createBatchedDecision(warningPatterns, 'medium'));
        }

        return decisions;
    }

    private async createDecision(
        pattern: InterpretedPattern,
        urgency: JudgementDecision['urgency']
    ): Promise<JudgementDecision> {
        const actions = this.determineActions(pattern);

        return {
            id: `decision_${Date.now()}_${pattern.id}`,
            patterns: [pattern.id],
            decision: this.generateDecisionText(pattern),
            reasoning: `Based on ${pattern.patternType} with ${pattern.confidence * 100}% confidence`,
            confidence: pattern.confidence,
            recommendedActions: actions,
            urgency,
        };
    }

    private async createBatchedDecision(
        patterns: InterpretedPattern[],
        urgency: JudgementDecision['urgency']
    ): Promise<JudgementDecision> {
        const actions: string[] = [];
        for (const pattern of patterns) {
            actions.push(...this.determineActions(pattern));
        }

        return {
            id: `decision_${Date.now()}_batch`,
            patterns: patterns.map(p => p.id),
            decision: `${patterns.length} issues require attention`,
            reasoning: `Aggregated from ${patterns.length} warning patterns`,
            confidence: patterns.reduce((sum, p) => sum + p.confidence, 0) / patterns.length,
            recommendedActions: [...new Set(actions)],
            urgency,
        };
    }

    private generateDecisionText(pattern: InterpretedPattern): string {
        switch (pattern.patternType) {
            case 'backend_disconnected':
                return 'Reconnect to Grace backend to restore functionality';
            case 'high_complexity':
                return 'Consider refactoring to reduce code complexity';
            case 'active_errors':
                return 'Address code errors before proceeding';
            case 'large_file':
                return 'Consider splitting large file into modules';
            case 'complexity_error_correlation':
                return 'Reduce complexity to potentially reduce errors';
            default:
                return `Address ${pattern.patternType} issue`;
        }
    }

    private determineActions(pattern: InterpretedPattern): string[] {
        switch (pattern.patternType) {
            case 'backend_disconnected':
                return ['reconnect_backend', 'notify_user'];
            case 'high_complexity':
                return ['suggest_refactoring', 'add_complexity_marker'];
            case 'active_errors':
                return ['highlight_errors', 'suggest_fixes'];
            case 'large_file':
                return ['suggest_split', 'add_size_warning'];
            default:
                return ['log_issue', 'notify_user'];
        }
    }
}

// ============================================================================
// Layer 4: Actions (Healing)
// ============================================================================

export class ActionLayer {
    private core: GraceOSCore;
    private bridge: IDEBridge;

    constructor(core: GraceOSCore, bridge: IDEBridge) {
        this.core = core;
        this.bridge = bridge;
    }

    async executeActions(decisions: JudgementDecision[]): Promise<HealingAction[]> {
        const actions: HealingAction[] = [];

        for (const decision of decisions) {
            for (const actionType of decision.recommendedActions) {
                const action = await this.executeAction(actionType, decision);
                actions.push(action);
            }
        }

        return actions;
    }

    private async executeAction(
        actionType: string,
        decision: JudgementDecision
    ): Promise<HealingAction> {
        const action: HealingAction = {
            id: `action_${Date.now()}_${actionType}`,
            type: actionType,
            target: decision.id,
            status: 'executing',
            timestamp: new Date().toISOString(),
        };

        try {
            switch (actionType) {
                case 'reconnect_backend':
                    await this.reconnectBackend();
                    action.result = { success: true };
                    break;

                case 'notify_user':
                    await this.notifyUser(decision);
                    action.result = { notified: true };
                    break;

                case 'suggest_refactoring':
                    await this.suggestRefactoring(decision);
                    action.result = { suggested: true };
                    break;

                case 'highlight_errors':
                    await this.highlightErrors();
                    action.result = { highlighted: true };
                    break;

                case 'suggest_fixes':
                    await this.suggestFixes(decision);
                    action.result = { suggested: true };
                    break;

                case 'add_complexity_marker':
                    await this.addComplexityMarker();
                    action.result = { marked: true };
                    break;

                default:
                    action.result = { action: 'logged' };
            }

            action.status = 'completed';
        } catch (error: any) {
            action.status = 'failed';
            action.result = { error: error.message };
        }

        return action;
    }

    private async reconnectBackend(): Promise<void> {
        const connected = await this.bridge.connect();
        if (!connected) {
            throw new Error('Failed to reconnect');
        }
    }

    private async notifyUser(decision: JudgementDecision): Promise<void> {
        const urgencyPrefix: Record<string, string> = {
            critical: '[CRITICAL] ',
            high: '[HIGH] ',
            medium: '',
            low: '',
        };

        const message = `${urgencyPrefix[decision.urgency]}${decision.decision}`;

        if (decision.urgency === 'critical' || decision.urgency === 'high') {
            vscode.window.showErrorMessage(`Grace: ${message}`);
        } else {
            vscode.window.showWarningMessage(`Grace: ${message}`);
        }
    }

    private async suggestRefactoring(decision: JudgementDecision): Promise<void> {
        const editor = vscode.window.activeTextEditor;
        if (editor) {
            // Add diagnostic
            const diagnostics = this.core.getDiagnosticCollection();
            diagnostics.set(editor.document.uri, [
                new vscode.Diagnostic(
                    new vscode.Range(0, 0, 0, 0),
                    `Grace: ${decision.decision}`,
                    vscode.DiagnosticSeverity.Information
                ),
            ]);
        }
    }

    private async highlightErrors(): Promise<void> {
        // VS Code already highlights errors, just ensure they're visible
        vscode.commands.executeCommand('workbench.action.problems.focus');
    }

    private async suggestFixes(decision: JudgementDecision): Promise<void> {
        // Trigger code actions for current position
        const editor = vscode.window.activeTextEditor;
        if (editor) {
            vscode.commands.executeCommand('editor.action.quickFix');
        }
    }

    private async addComplexityMarker(): Promise<void> {
        const editor = vscode.window.activeTextEditor;
        if (editor) {
            // Add complexity indicator in status bar or as decoration
            this.core.log('Complexity marker added');
        }
    }
}

// ============================================================================
// Main Diagnostic Machine
// ============================================================================

export class DiagnosticMachine {
    private core: GraceOSCore;
    private bridge: IDEBridge;
    private wsBridge: GraceWebSocketBridge;
    private sensorLayer: SensorLayer;
    private interpreterLayer: InterpreterLayer;
    private judgementLayer: JudgementLayer;
    private actionLayer: ActionLayer;
    private state: DiagnosticState;
    private diagnosticInterval?: NodeJS.Timeout;

    constructor(core: GraceOSCore, bridge: IDEBridge, wsBridge: GraceWebSocketBridge) {
        this.core = core;
        this.bridge = bridge;
        this.wsBridge = wsBridge;

        this.sensorLayer = new SensorLayer(core);
        this.interpreterLayer = new InterpreterLayer(core);
        this.judgementLayer = new JudgementLayer(core, bridge);
        this.actionLayer = new ActionLayer(core, bridge);

        this.state = {
            layer1: [],
            layer2: [],
            layer3: [],
            layer4: [],
            overallHealth: 'healthy',
            lastUpdate: new Date(),
        };

        // Listen for real-time diagnostic updates from backend
        this.wsBridge.on('diagnosticUpdate', (data: any) => {
            this.handleBackendDiagnostic(data);
        });
    }

    async initialize(): Promise<void> {
        const config = this.core.getConfig();

        if (config.diagnostics.autoRun) {
            this.startContinuousDiagnostics(config.diagnostics.interval);
        }

        this.core.enableFeature('diagnosticMachine');
        this.core.log('Diagnostic Machine initialized');
    }

    async runFullDiagnostic(): Promise<DiagnosticState> {
        this.core.log('Running full 4-layer diagnostic...');

        // Layer 1: Collect sensor readings
        const readings = await this.sensorLayer.collectReadings();
        this.state.layer1 = readings;

        // Layer 2: Interpret patterns
        const patterns = await this.interpreterLayer.interpretReadings(readings);
        this.state.layer2 = patterns;

        // Layer 3: Make judgements
        const decisions = await this.judgementLayer.makeDecisions(patterns);
        this.state.layer3 = decisions;

        // Layer 4: Execute healing actions
        const actions = await this.actionLayer.executeActions(decisions);
        this.state.layer4 = actions;

        // Update overall health
        this.state.overallHealth = this.calculateOverallHealth(patterns, decisions);
        this.state.lastUpdate = new Date();

        // Update core state
        this.core.updateState({ healthStatus: this.state.overallHealth });

        // Emit update event
        this.core.emit('diagnosticComplete', this.state);

        return this.state;
    }

    private calculateOverallHealth(
        patterns: InterpretedPattern[],
        decisions: JudgementDecision[]
    ): DiagnosticState['overallHealth'] {
        const hasCritical = patterns.some(p => p.severity === 'critical') ||
                          decisions.some(d => d.urgency === 'critical');
        const hasError = patterns.some(p => p.severity === 'error') ||
                        decisions.some(d => d.urgency === 'high');
        const hasWarning = patterns.some(p => p.severity === 'warning') ||
                          decisions.some(d => d.urgency === 'medium');

        if (hasCritical) return 'critical';
        if (hasError) return 'unhealthy';
        if (hasWarning) return 'degraded';
        return 'healthy';
    }

    private startContinuousDiagnostics(interval: number): void {
        this.diagnosticInterval = setInterval(async () => {
            await this.runFullDiagnostic();
        }, interval);
    }

    private handleBackendDiagnostic(data: any): void {
        // Merge backend diagnostics with local state
        if (data.readings) {
            this.state.layer1 = [...this.state.layer1, ...data.readings];
        }
        if (data.patterns) {
            this.state.layer2 = [...this.state.layer2, ...data.patterns];
        }
    }

    getState(): DiagnosticState {
        return { ...this.state };
    }

    dispose(): void {
        if (this.diagnosticInterval) {
            clearInterval(this.diagnosticInterval);
        }
    }
}
