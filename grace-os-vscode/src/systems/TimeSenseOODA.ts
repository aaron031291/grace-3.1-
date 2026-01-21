/**
 * TimeSense & OODA Loop Integration
 *
 * Temporal reasoning and decision-making framework:
 * - TimeSense: Temporal context awareness
 * - OODA Loop: Observe → Orient → Decide → Act
 * - Predictive analysis
 * - Context-aware timing
 */

import * as vscode from 'vscode';
import { GraceOSCore } from '../core/GraceOSCore';
import { IDEBridge } from '../bridges/IDEBridge';

// ============================================================================
// Types
// ============================================================================

export interface TemporalContext {
    currentTime: Date;
    sessionDuration: number;
    timeSinceLastAction: number;
    timeOfDay: 'morning' | 'afternoon' | 'evening' | 'night';
    workPattern: 'focused' | 'distracted' | 'idle';
    recentActivityRate: number;
}

export interface OODAState {
    phase: 'observe' | 'orient' | 'decide' | 'act';
    observations: Observation[];
    orientation: Orientation | null;
    decision: Decision | null;
    action: Action | null;
    cycleCount: number;
    avgCycleTime: number;
}

export interface Observation {
    id: string;
    timestamp: Date;
    source: string;
    type: string;
    data: any;
    relevance: number;
}

export interface Orientation {
    id: string;
    timestamp: Date;
    observations: string[];
    analysis: string;
    patterns: string[];
    threats: string[];
    opportunities: string[];
    confidence: number;
}

export interface Decision {
    id: string;
    timestamp: Date;
    orientationId: string;
    options: DecisionOption[];
    selectedOption: string;
    reasoning: string;
    confidence: number;
    urgency: 'low' | 'medium' | 'high' | 'critical';
}

export interface DecisionOption {
    id: string;
    description: string;
    expectedOutcome: string;
    riskLevel: number;
    resourceCost: number;
    timeToExecute: number;
    score: number;
}

export interface Action {
    id: string;
    timestamp: Date;
    decisionId: string;
    type: string;
    params: Record<string, any>;
    status: 'pending' | 'executing' | 'completed' | 'failed';
    result?: any;
    feedback?: ActionFeedback;
}

export interface ActionFeedback {
    success: boolean;
    actualOutcome: string;
    deviationFromExpected: number;
    lessonsLearned: string[];
}

// ============================================================================
// TimeSense System
// ============================================================================

export class TimeSense {
    private core: GraceOSCore;
    private activityLog: Array<{ timestamp: Date; type: string }> = [];
    private sessionStart: Date;

    constructor(core: GraceOSCore) {
        this.core = core;
        this.sessionStart = new Date();
    }

    async initialize(): Promise<void> {
        // Track user activity
        vscode.window.onDidChangeActiveTextEditor(() => {
            this.recordActivity('editor_change');
        });

        vscode.workspace.onDidChangeTextDocument(() => {
            this.recordActivity('text_change');
        });

        vscode.window.onDidChangeTextEditorSelection(() => {
            this.recordActivity('selection_change');
        });

        this.core.log('TimeSense initialized');
    }

    private recordActivity(type: string): void {
        this.activityLog.push({ timestamp: new Date(), type });

        // Keep only last 1000 activities
        if (this.activityLog.length > 1000) {
            this.activityLog = this.activityLog.slice(-1000);
        }
    }

    getTemporalContext(): TemporalContext {
        const now = new Date();
        const hour = now.getHours();

        // Calculate session duration
        const sessionDuration = now.getTime() - this.sessionStart.getTime();

        // Calculate time since last action
        const lastActivity = this.activityLog[this.activityLog.length - 1];
        const timeSinceLastAction = lastActivity
            ? now.getTime() - lastActivity.timestamp.getTime()
            : 0;

        // Determine time of day
        let timeOfDay: TemporalContext['timeOfDay'];
        if (hour >= 6 && hour < 12) timeOfDay = 'morning';
        else if (hour >= 12 && hour < 17) timeOfDay = 'afternoon';
        else if (hour >= 17 && hour < 21) timeOfDay = 'evening';
        else timeOfDay = 'night';

        // Determine work pattern
        const recentActivities = this.activityLog.filter(
            a => now.getTime() - a.timestamp.getTime() < 300000 // Last 5 minutes
        );
        const activityRate = recentActivities.length / 300; // Activities per second

        let workPattern: TemporalContext['workPattern'];
        if (activityRate > 0.1) workPattern = 'focused';
        else if (activityRate > 0.01) workPattern = 'distracted';
        else workPattern = 'idle';

        return {
            currentTime: now,
            sessionDuration,
            timeSinceLastAction,
            timeOfDay,
            workPattern,
            recentActivityRate: activityRate,
        };
    }

    predictBestTimeForAction(actionType: string): Date {
        const context = this.getTemporalContext();

        // Don't interrupt focused work
        if (context.workPattern === 'focused') {
            // Wait for natural break
            return new Date(Date.now() + 300000); // 5 minutes
        }

        // During idle, now is good
        if (context.workPattern === 'idle') {
            return new Date();
        }

        // For distracted patterns, slight delay
        return new Date(Date.now() + 60000); // 1 minute
    }

    shouldInterrupt(): boolean {
        const context = this.getTemporalContext();

        // Never interrupt focused work unless critical
        if (context.workPattern === 'focused') {
            return false;
        }

        // OK to interrupt idle users
        if (context.workPattern === 'idle') {
            return true;
        }

        // Interrupt distracted users after some delay
        return context.timeSinceLastAction > 30000; // 30 seconds
    }

    getProductivityInsights(): Record<string, any> {
        const context = this.getTemporalContext();

        // Analyze activity patterns
        const hourlyActivity: Record<number, number> = {};
        for (const activity of this.activityLog) {
            const hour = activity.timestamp.getHours();
            hourlyActivity[hour] = (hourlyActivity[hour] || 0) + 1;
        }

        const peakHour = Object.entries(hourlyActivity)
            .sort(([, a], [, b]) => b - a)[0]?.[0];

        return {
            sessionDuration: Math.round(context.sessionDuration / 60000), // minutes
            currentPattern: context.workPattern,
            activityRate: context.recentActivityRate,
            peakProductivityHour: peakHour ? parseInt(peakHour) : null,
            totalActivities: this.activityLog.length,
        };
    }
}

// ============================================================================
// OODA Loop System
// ============================================================================

export class OODALoop {
    private core: GraceOSCore;
    private bridge: IDEBridge;
    private timeSense: TimeSense;
    private state: OODAState;
    private cycleHistory: OODAState[] = [];
    private isRunning: boolean = false;

    constructor(core: GraceOSCore, bridge: IDEBridge, timeSense: TimeSense) {
        this.core = core;
        this.bridge = bridge;
        this.timeSense = timeSense;

        this.state = {
            phase: 'observe',
            observations: [],
            orientation: null,
            decision: null,
            action: null,
            cycleCount: 0,
            avgCycleTime: 0,
        };
    }

    async initialize(): Promise<void> {
        this.core.log('OODA Loop initialized');
    }

    async runCycle(): Promise<OODAState> {
        if (this.isRunning) {
            return this.state;
        }

        this.isRunning = true;
        const cycleStart = Date.now();

        try {
            // Phase 1: Observe
            this.state.phase = 'observe';
            const observations = await this.observe();
            this.state.observations = observations;

            // Phase 2: Orient
            this.state.phase = 'orient';
            const orientation = await this.orient(observations);
            this.state.orientation = orientation;

            // Phase 3: Decide
            this.state.phase = 'decide';
            const decision = await this.decide(orientation);
            this.state.decision = decision;

            // Phase 4: Act
            this.state.phase = 'act';
            const action = await this.act(decision);
            this.state.action = action;

            // Update cycle stats
            this.state.cycleCount++;
            const cycleTime = Date.now() - cycleStart;
            this.state.avgCycleTime =
                (this.state.avgCycleTime * (this.state.cycleCount - 1) + cycleTime) /
                this.state.cycleCount;

            // Record cycle
            this.cycleHistory.push({ ...this.state });
            if (this.cycleHistory.length > 100) {
                this.cycleHistory = this.cycleHistory.slice(-100);
            }

        } finally {
            this.isRunning = false;
        }

        return this.state;
    }

    private async observe(): Promise<Observation[]> {
        const observations: Observation[] = [];
        const temporalContext = this.timeSense.getTemporalContext();

        // Observe editor state
        const editor = vscode.window.activeTextEditor;
        if (editor) {
            observations.push({
                id: `obs_${Date.now()}_editor`,
                timestamp: new Date(),
                source: 'editor',
                type: 'editor_state',
                data: {
                    filePath: editor.document.uri.fsPath,
                    language: editor.document.languageId,
                    lineCount: editor.document.lineCount,
                    hasSelection: !editor.selection.isEmpty,
                    cursorPosition: editor.selection.active.line,
                },
                relevance: 0.9,
            });

            // Observe diagnostics
            const diagnostics = vscode.languages.getDiagnostics(editor.document.uri);
            if (diagnostics.length > 0) {
                observations.push({
                    id: `obs_${Date.now()}_diag`,
                    timestamp: new Date(),
                    source: 'diagnostics',
                    type: 'code_issues',
                    data: {
                        errors: diagnostics.filter(d => d.severity === vscode.DiagnosticSeverity.Error).length,
                        warnings: diagnostics.filter(d => d.severity === vscode.DiagnosticSeverity.Warning).length,
                    },
                    relevance: 0.85,
                });
            }
        }

        // Observe user patterns
        observations.push({
            id: `obs_${Date.now()}_temporal`,
            timestamp: new Date(),
            source: 'timesense',
            type: 'temporal_context',
            data: temporalContext,
            relevance: 0.7,
        });

        // Observe system state
        const graceState = this.core.getState();
        observations.push({
            id: `obs_${Date.now()}_system`,
            timestamp: new Date(),
            source: 'grace',
            type: 'system_state',
            data: {
                connected: graceState.isConnected,
                healthStatus: graceState.healthStatus,
                pendingTasks: graceState.pendingTasks,
            },
            relevance: 0.8,
        });

        return observations;
    }

    private async orient(observations: Observation[]): Promise<Orientation> {
        const patterns: string[] = [];
        const threats: string[] = [];
        const opportunities: string[] = [];

        // Analyze observations
        for (const obs of observations) {
            switch (obs.type) {
                case 'code_issues':
                    if (obs.data.errors > 0) {
                        threats.push(`${obs.data.errors} code errors detected`);
                    }
                    if (obs.data.warnings > 5) {
                        patterns.push('High warning count - code quality concern');
                    }
                    break;

                case 'temporal_context':
                    if (obs.data.workPattern === 'focused') {
                        patterns.push('User in focused work mode');
                    } else if (obs.data.workPattern === 'idle') {
                        opportunities.push('User available for suggestions');
                    }
                    break;

                case 'system_state':
                    if (!obs.data.connected) {
                        threats.push('Backend disconnected');
                    }
                    if (obs.data.healthStatus !== 'healthy') {
                        threats.push(`System health: ${obs.data.healthStatus}`);
                    }
                    break;
            }
        }

        // Build analysis
        const analysis = this.buildAnalysis(observations, patterns, threats, opportunities);

        return {
            id: `orient_${Date.now()}`,
            timestamp: new Date(),
            observations: observations.map(o => o.id),
            analysis,
            patterns,
            threats,
            opportunities,
            confidence: this.calculateConfidence(observations),
        };
    }

    private buildAnalysis(
        observations: Observation[],
        patterns: string[],
        threats: string[],
        opportunities: string[]
    ): string {
        const parts: string[] = [];

        if (threats.length > 0) {
            parts.push(`Threats: ${threats.join(', ')}`);
        }

        if (opportunities.length > 0) {
            parts.push(`Opportunities: ${opportunities.join(', ')}`);
        }

        if (patterns.length > 0) {
            parts.push(`Patterns: ${patterns.join(', ')}`);
        }

        return parts.join('. ') || 'Normal operation - no significant findings';
    }

    private calculateConfidence(observations: Observation[]): number {
        if (observations.length === 0) return 0;

        const avgRelevance = observations.reduce((sum, o) => sum + o.relevance, 0) / observations.length;
        const dataQuality = observations.filter(o => o.data !== null).length / observations.length;

        return avgRelevance * dataQuality;
    }

    private async decide(orientation: Orientation): Promise<Decision> {
        const options: DecisionOption[] = [];

        // Generate options based on orientation
        if (orientation.threats.length > 0) {
            // Threat response options
            for (const threat of orientation.threats) {
                if (threat.includes('error')) {
                    options.push({
                        id: 'fix_errors',
                        description: 'Fix code errors',
                        expectedOutcome: 'Errors resolved',
                        riskLevel: 0.2,
                        resourceCost: 0.3,
                        timeToExecute: 5000,
                        score: 0.8,
                    });
                }

                if (threat.includes('disconnected')) {
                    options.push({
                        id: 'reconnect',
                        description: 'Reconnect to backend',
                        expectedOutcome: 'Connection restored',
                        riskLevel: 0.1,
                        resourceCost: 0.1,
                        timeToExecute: 3000,
                        score: 0.9,
                    });
                }
            }
        }

        if (orientation.opportunities.length > 0) {
            // Opportunity response options
            for (const opportunity of orientation.opportunities) {
                if (opportunity.includes('suggestions')) {
                    options.push({
                        id: 'suggest_improvements',
                        description: 'Offer code suggestions',
                        expectedOutcome: 'User receives helpful suggestions',
                        riskLevel: 0.1,
                        resourceCost: 0.2,
                        timeToExecute: 2000,
                        score: 0.7,
                    });
                }
            }
        }

        // Always have a "do nothing" option
        options.push({
            id: 'wait',
            description: 'Continue monitoring',
            expectedOutcome: 'No change',
            riskLevel: 0,
            resourceCost: 0,
            timeToExecute: 0,
            score: 0.5,
        });

        // Select best option
        options.sort((a, b) => b.score - a.score);
        const selectedOption = options[0];

        return {
            id: `decision_${Date.now()}`,
            timestamp: new Date(),
            orientationId: orientation.id,
            options,
            selectedOption: selectedOption.id,
            reasoning: `Selected "${selectedOption.description}" based on score ${selectedOption.score}`,
            confidence: orientation.confidence * selectedOption.score,
            urgency: orientation.threats.length > 0 ? 'high' : 'low',
        };
    }

    private async act(decision: Decision): Promise<Action> {
        const action: Action = {
            id: `action_${Date.now()}`,
            timestamp: new Date(),
            decisionId: decision.id,
            type: decision.selectedOption,
            params: {},
            status: 'pending',
        };

        // Check if we should interrupt
        if (!this.timeSense.shouldInterrupt() && decision.urgency !== 'critical') {
            action.status = 'completed';
            action.result = { skipped: true, reason: 'User busy' };
            return action;
        }

        action.status = 'executing';

        try {
            switch (decision.selectedOption) {
                case 'fix_errors':
                    vscode.commands.executeCommand('graceOS.cognitive.refactor');
                    action.result = { triggered: 'refactor_command' };
                    break;

                case 'reconnect':
                    vscode.commands.executeCommand('graceOS.activate');
                    action.result = { triggered: 'reconnect_command' };
                    break;

                case 'suggest_improvements':
                    // Trigger inline suggestions
                    vscode.commands.executeCommand('graceOS.cognitive.analyze');
                    action.result = { triggered: 'analyze_command' };
                    break;

                case 'wait':
                default:
                    action.result = { action: 'none' };
            }

            action.status = 'completed';

        } catch (error: any) {
            action.status = 'failed';
            action.result = { error: error.message };
        }

        return action;
    }

    getState(): OODAState {
        return { ...this.state };
    }

    getHistory(): OODAState[] {
        return [...this.cycleHistory];
    }
}

// ============================================================================
// Combined TimeSense & OODA System
// ============================================================================

export class TimeSenseOODA {
    private core: GraceOSCore;
    private bridge: IDEBridge;
    public timeSense: TimeSense;
    public oodaLoop: OODALoop;
    private autoRunInterval?: NodeJS.Timeout;

    constructor(core: GraceOSCore, bridge: IDEBridge) {
        this.core = core;
        this.bridge = bridge;

        this.timeSense = new TimeSense(core);
        this.oodaLoop = new OODALoop(core, bridge, this.timeSense);
    }

    async initialize(): Promise<void> {
        await this.timeSense.initialize();
        await this.oodaLoop.initialize();

        // Start auto-running OODA cycles
        this.autoRunInterval = setInterval(async () => {
            await this.oodaLoop.runCycle();
        }, 60000); // Every minute

        this.core.enableFeature('timeSenseOODA');
        this.core.log('TimeSense & OODA initialized');
    }

    async runOODACycle(): Promise<OODAState> {
        return this.oodaLoop.runCycle();
    }

    getTemporalContext(): TemporalContext {
        return this.timeSense.getTemporalContext();
    }

    getProductivityInsights(): Record<string, any> {
        return this.timeSense.getProductivityInsights();
    }

    dispose(): void {
        if (this.autoRunInterval) {
            clearInterval(this.autoRunInterval);
        }
    }
}
