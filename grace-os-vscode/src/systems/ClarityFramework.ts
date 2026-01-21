/**
 * Clarity Framework - Transparent Decision Making
 *
 * Provides full transparency into Grace's decision-making:
 * - Clear intentions and reasoning
 * - Traceable decision chains
 * - Explainable actions
 * - User-understandable outputs
 */

import * as vscode from 'vscode';
import { GraceOSCore } from '../core/GraceOSCore';
import { IDEBridge } from '../bridges/IDEBridge';

// ============================================================================
// Types
// ============================================================================

export interface Intention {
    id: string;
    timestamp: Date;
    type: IntentionType;
    description: string;
    goals: string[];
    constraints: string[];
    expectedOutcome: string;
    confidence: number;
}

export type IntentionType =
    | 'assist'
    | 'improve'
    | 'protect'
    | 'inform'
    | 'suggest'
    | 'automate'
    | 'learn';

export interface DecisionTrace {
    id: string;
    timestamp: Date;
    intentionId: string;
    inputs: TraceInput[];
    reasoning: ReasoningStep[];
    output: TraceOutput;
    alternatives: Alternative[];
}

export interface TraceInput {
    name: string;
    value: any;
    source: string;
    relevance: number;
}

export interface ReasoningStep {
    step: number;
    description: string;
    logic: string;
    confidence: number;
    inputs: string[];
    output: string;
}

export interface TraceOutput {
    action: string;
    parameters: Record<string, any>;
    expectedImpact: string;
    reversible: boolean;
}

export interface Alternative {
    action: string;
    reason: string;
    whyNotChosen: string;
}

export interface Explanation {
    summary: string;
    details: string[];
    confidence: number;
    sources: string[];
    limitations: string[];
}

// ============================================================================
// Clarity Framework
// ============================================================================

export class ClarityFramework {
    private core: GraceOSCore;
    private bridge: IDEBridge;
    private intentions: Map<string, Intention> = new Map();
    private traces: Map<string, DecisionTrace> = new Map();
    private outputChannel: vscode.OutputChannel;

    constructor(core: GraceOSCore, bridge: IDEBridge) {
        this.core = core;
        this.bridge = bridge;
        this.outputChannel = vscode.window.createOutputChannel('Grace Clarity');
    }

    async initialize(): Promise<void> {
        this.core.log('Initializing Clarity Framework...');
        this.core.enableFeature('clarityFramework');
        this.core.log('Clarity Framework initialized');
    }

    // ============================================================================
    // Intention Management
    // ============================================================================

    declareIntention(
        type: IntentionType,
        description: string,
        options: {
            goals?: string[];
            constraints?: string[];
            expectedOutcome?: string;
            confidence?: number;
        } = {}
    ): Intention {
        const intention: Intention = {
            id: `intent_${Date.now()}`,
            timestamp: new Date(),
            type,
            description,
            goals: options.goals || [],
            constraints: options.constraints || [],
            expectedOutcome: options.expectedOutcome || 'Successful completion',
            confidence: options.confidence || 0.8,
        };

        this.intentions.set(intention.id, intention);
        this.logIntention(intention);

        return intention;
    }

    private logIntention(intention: Intention): void {
        this.outputChannel.appendLine(`\n=== Intention Declared ===`);
        this.outputChannel.appendLine(`Type: ${intention.type}`);
        this.outputChannel.appendLine(`Description: ${intention.description}`);
        this.outputChannel.appendLine(`Goals: ${intention.goals.join(', ') || 'None specified'}`);
        this.outputChannel.appendLine(`Constraints: ${intention.constraints.join(', ') || 'None specified'}`);
        this.outputChannel.appendLine(`Expected Outcome: ${intention.expectedOutcome}`);
        this.outputChannel.appendLine(`Confidence: ${(intention.confidence * 100).toFixed(0)}%`);
    }

    // ============================================================================
    // Decision Tracing
    // ============================================================================

    startTrace(intentionId: string): DecisionTrace {
        const trace: DecisionTrace = {
            id: `trace_${Date.now()}`,
            timestamp: new Date(),
            intentionId,
            inputs: [],
            reasoning: [],
            output: {
                action: '',
                parameters: {},
                expectedImpact: '',
                reversible: true,
            },
            alternatives: [],
        };

        this.traces.set(trace.id, trace);
        return trace;
    }

    addTraceInput(traceId: string, input: TraceInput): void {
        const trace = this.traces.get(traceId);
        if (trace) {
            trace.inputs.push(input);
        }
    }

    addReasoningStep(traceId: string, step: Omit<ReasoningStep, 'step'>): void {
        const trace = this.traces.get(traceId);
        if (trace) {
            const stepNumber = trace.reasoning.length + 1;
            trace.reasoning.push({
                ...step,
                step: stepNumber,
            });
        }
    }

    addAlternative(traceId: string, alternative: Alternative): void {
        const trace = this.traces.get(traceId);
        if (trace) {
            trace.alternatives.push(alternative);
        }
    }

    completeTrace(traceId: string, output: TraceOutput): DecisionTrace | undefined {
        const trace = this.traces.get(traceId);
        if (trace) {
            trace.output = output;
            this.logTrace(trace);
            return trace;
        }
        return undefined;
    }

    private logTrace(trace: DecisionTrace): void {
        this.outputChannel.appendLine(`\n=== Decision Trace ===`);
        this.outputChannel.appendLine(`Trace ID: ${trace.id}`);
        this.outputChannel.appendLine(`Intention: ${trace.intentionId}`);

        this.outputChannel.appendLine(`\n--- Inputs ---`);
        for (const input of trace.inputs) {
            this.outputChannel.appendLine(`  ${input.name}: ${JSON.stringify(input.value)} (from ${input.source})`);
        }

        this.outputChannel.appendLine(`\n--- Reasoning ---`);
        for (const step of trace.reasoning) {
            this.outputChannel.appendLine(`  ${step.step}. ${step.description}`);
            this.outputChannel.appendLine(`     Logic: ${step.logic}`);
            this.outputChannel.appendLine(`     Confidence: ${(step.confidence * 100).toFixed(0)}%`);
        }

        this.outputChannel.appendLine(`\n--- Output ---`);
        this.outputChannel.appendLine(`  Action: ${trace.output.action}`);
        this.outputChannel.appendLine(`  Parameters: ${JSON.stringify(trace.output.parameters)}`);
        this.outputChannel.appendLine(`  Expected Impact: ${trace.output.expectedImpact}`);
        this.outputChannel.appendLine(`  Reversible: ${trace.output.reversible}`);

        if (trace.alternatives.length > 0) {
            this.outputChannel.appendLine(`\n--- Alternatives Considered ---`);
            for (const alt of trace.alternatives) {
                this.outputChannel.appendLine(`  - ${alt.action}: ${alt.whyNotChosen}`);
            }
        }
    }

    // ============================================================================
    // Explanation Generation
    // ============================================================================

    async explainAction(action: string, context?: Record<string, any>): Promise<Explanation> {
        // Try to get explanation from backend
        try {
            const response = await this.bridge.invokeAgent('explain_action', { action, context });
            if (response.success && response.data) {
                return response.data;
            }
        } catch {
            // Generate local explanation
        }

        // Generate local explanation
        return this.generateLocalExplanation(action, context);
    }

    private generateLocalExplanation(action: string, context?: Record<string, any>): Explanation {
        const explanations: Record<string, Explanation> = {
            analyze: {
                summary: 'Analyzing code to identify patterns, issues, and improvement opportunities',
                details: [
                    'Scanning code structure and syntax',
                    'Identifying potential issues and code smells',
                    'Looking for patterns that match known problems',
                    'Generating suggestions based on best practices',
                ],
                confidence: 0.85,
                sources: ['Code analysis engine', 'Pattern database', 'Best practices knowledge base'],
                limitations: [
                    'May not catch all context-specific issues',
                    'Suggestions are based on general patterns',
                ],
            },
            refactor: {
                summary: 'Suggesting code improvements while preserving functionality',
                details: [
                    'Analyzing code complexity and readability',
                    'Identifying opportunities for simplification',
                    'Checking for design pattern applications',
                    'Ensuring backward compatibility',
                ],
                confidence: 0.8,
                sources: ['Refactoring patterns', 'Clean code principles'],
                limitations: [
                    'Requires human review for complex changes',
                    'May not understand all business logic',
                ],
            },
            fix: {
                summary: 'Attempting to automatically fix detected issues',
                details: [
                    'Identifying the root cause of the issue',
                    'Applying known fix patterns',
                    'Validating the fix does not break existing code',
                ],
                confidence: 0.7,
                sources: ['Error pattern database', 'Common fix strategies'],
                limitations: [
                    'May not fix all types of issues',
                    'Complex issues require manual intervention',
                ],
            },
        };

        return explanations[action] || {
            summary: `Performing ${action} operation`,
            details: [`Executing ${action} based on current context`],
            confidence: 0.6,
            sources: ['Grace knowledge base'],
            limitations: ['Limited explanation available for this action'],
        };
    }

    async explainDecision(traceId: string): Promise<string> {
        const trace = this.traces.get(traceId);
        if (!trace) {
            return 'Decision trace not found';
        }

        const intention = this.intentions.get(trace.intentionId);

        const parts: string[] = [
            `## Decision Explanation`,
            '',
            `### Why this decision was made`,
            intention
                ? `Grace decided to ${trace.output.action} because the goal was to "${intention.description}".`
                : `Grace decided to ${trace.output.action}.`,
            '',
            `### Reasoning Process`,
        ];

        for (const step of trace.reasoning) {
            parts.push(`${step.step}. **${step.description}**`);
            parts.push(`   - Logic: ${step.logic}`);
            parts.push(`   - Confidence: ${(step.confidence * 100).toFixed(0)}%`);
        }

        if (trace.alternatives.length > 0) {
            parts.push('', `### Why alternatives were not chosen`);
            for (const alt of trace.alternatives) {
                parts.push(`- **${alt.action}**: ${alt.whyNotChosen}`);
            }
        }

        parts.push('', `### Expected Impact`);
        parts.push(trace.output.expectedImpact);

        if (!trace.output.reversible) {
            parts.push('', `⚠️ **Note**: This action cannot be automatically reversed.`);
        }

        return parts.join('\n');
    }

    // ============================================================================
    // User Interface
    // ============================================================================

    showClarity(): void {
        this.outputChannel.show();
    }

    async showDecisionExplanation(traceId?: string): Promise<void> {
        if (!traceId) {
            // Get most recent trace
            const traces = Array.from(this.traces.values());
            if (traces.length === 0) {
                vscode.window.showInformationMessage('No decisions to explain');
                return;
            }
            traceId = traces[traces.length - 1].id;
        }

        const explanation = await this.explainDecision(traceId);

        const doc = await vscode.workspace.openTextDocument({
            content: explanation,
            language: 'markdown',
        });

        await vscode.window.showTextDocument(doc, { preview: true });
    }

    async showActionExplanation(action: string): Promise<void> {
        const explanation = await this.explainAction(action);

        const content = [
            `# ${action.charAt(0).toUpperCase() + action.slice(1)} Action`,
            '',
            `## Summary`,
            explanation.summary,
            '',
            `## How it Works`,
            ...explanation.details.map(d => `- ${d}`),
            '',
            `## Confidence: ${(explanation.confidence * 100).toFixed(0)}%`,
            '',
            `## Sources`,
            ...explanation.sources.map(s => `- ${s}`),
            '',
            `## Limitations`,
            ...explanation.limitations.map(l => `- ${l}`),
        ].join('\n');

        const doc = await vscode.workspace.openTextDocument({
            content,
            language: 'markdown',
        });

        await vscode.window.showTextDocument(doc, { preview: true });
    }

    // ============================================================================
    // Transparency Helpers
    // ============================================================================

    getIntentionHistory(): Intention[] {
        return Array.from(this.intentions.values());
    }

    getTraceHistory(): DecisionTrace[] {
        return Array.from(this.traces.values());
    }

    getLatestTrace(): DecisionTrace | undefined {
        const traces = Array.from(this.traces.values());
        return traces[traces.length - 1];
    }

    dispose(): void {
        this.outputChannel.dispose();
    }
}
