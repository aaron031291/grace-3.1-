/**
 * Sandbox Lab - Safe Experimentation Environment
 *
 * Provides isolated environment for:
 * - Code experimentation
 * - Safe execution
 * - A/B testing
 * - Rollback capabilities
 */

import * as vscode from 'vscode';
import * as path from 'path';
import { GraceOSCore } from '../core/GraceOSCore';
import { IDEBridge } from '../bridges/IDEBridge';

// ============================================================================
// Types
// ============================================================================

export interface Experiment {
    id: string;
    name: string;
    description: string;
    type: ExperimentType;
    status: ExperimentStatus;
    hypothesis: string;
    variables: ExperimentVariable[];
    metrics: ExperimentMetric[];
    results?: ExperimentResults;
    createdAt: Date;
    startedAt?: Date;
    completedAt?: Date;
}

export type ExperimentType = 'code_change' | 'feature_test' | 'performance' | 'a_b_test';
export type ExperimentStatus = 'draft' | 'running' | 'completed' | 'failed' | 'rolled_back';

export interface ExperimentVariable {
    name: string;
    controlValue: any;
    treatmentValue: any;
}

export interface ExperimentMetric {
    name: string;
    type: 'count' | 'duration' | 'percentage' | 'score';
    controlValue?: number;
    treatmentValue?: number;
}

export interface ExperimentResults {
    success: boolean;
    summary: string;
    metrics: Record<string, { control: number; treatment: number; improvement: number }>;
    recommendation: 'adopt' | 'reject' | 'continue';
    confidence: number;
}

export interface Snapshot {
    id: string;
    experimentId: string;
    timestamp: Date;
    files: FileSnapshot[];
    metadata: Record<string, any>;
}

export interface FileSnapshot {
    path: string;
    content: string;
    hash: string;
}

// ============================================================================
// Sandbox Lab
// ============================================================================

export class SandboxLab {
    private core: GraceOSCore;
    private bridge: IDEBridge;
    private experiments: Map<string, Experiment> = new Map();
    private snapshots: Map<string, Snapshot> = new Map();
    private outputChannel: vscode.OutputChannel;

    constructor(core: GraceOSCore, bridge: IDEBridge) {
        this.core = core;
        this.bridge = bridge;
        this.outputChannel = vscode.window.createOutputChannel('Grace Sandbox');
    }

    async initialize(): Promise<void> {
        this.core.log('Initializing Sandbox Lab...');
        this.core.enableFeature('sandboxLab');
        this.core.log('Sandbox Lab initialized');
    }

    // ============================================================================
    // Experiment Management
    // ============================================================================

    createExperiment(
        name: string,
        type: ExperimentType,
        options: {
            description?: string;
            hypothesis?: string;
            variables?: ExperimentVariable[];
            metrics?: ExperimentMetric[];
        } = {}
    ): Experiment {
        const experiment: Experiment = {
            id: `exp_${Date.now()}`,
            name,
            type,
            description: options.description || '',
            hypothesis: options.hypothesis || '',
            variables: options.variables || [],
            metrics: options.metrics || [],
            status: 'draft',
            createdAt: new Date(),
        };

        this.experiments.set(experiment.id, experiment);
        this.log(`Created experiment: ${name}`);

        return experiment;
    }

    async startExperiment(experimentId: string): Promise<boolean> {
        const experiment = this.experiments.get(experimentId);
        if (!experiment) return false;

        try {
            // Create snapshot before starting
            await this.createSnapshot(experimentId);

            experiment.status = 'running';
            experiment.startedAt = new Date();

            this.log(`Started experiment: ${experiment.name}`);
            return true;
        } catch (error: any) {
            experiment.status = 'failed';
            this.log(`Failed to start experiment: ${error.message}`);
            return false;
        }
    }

    async stopExperiment(experimentId: string, success: boolean = true): Promise<ExperimentResults | null> {
        const experiment = this.experiments.get(experimentId);
        if (!experiment || experiment.status !== 'running') return null;

        experiment.status = success ? 'completed' : 'failed';
        experiment.completedAt = new Date();

        // Calculate results
        const results = this.calculateResults(experiment);
        experiment.results = results;

        this.log(`Completed experiment: ${experiment.name} - ${results.recommendation}`);
        return results;
    }

    async rollbackExperiment(experimentId: string): Promise<boolean> {
        const experiment = this.experiments.get(experimentId);
        const snapshot = this.snapshots.get(experimentId);

        if (!experiment || !snapshot) return false;

        try {
            // Restore files from snapshot
            for (const file of snapshot.files) {
                const uri = vscode.Uri.file(file.path);
                const edit = new vscode.WorkspaceEdit();

                try {
                    const doc = await vscode.workspace.openTextDocument(uri);
                    const fullRange = new vscode.Range(0, 0, doc.lineCount, 0);
                    edit.replace(uri, fullRange, file.content);
                } catch {
                    // File might not exist, create it
                    edit.createFile(uri, { overwrite: true });
                }

                await vscode.workspace.applyEdit(edit);
            }

            experiment.status = 'rolled_back';
            this.log(`Rolled back experiment: ${experiment.name}`);
            return true;
        } catch (error: any) {
            this.log(`Failed to rollback: ${error.message}`);
            return false;
        }
    }

    // ============================================================================
    // Snapshot Management
    // ============================================================================

    private async createSnapshot(experimentId: string): Promise<Snapshot> {
        const files: FileSnapshot[] = [];

        // Get all open files
        for (const doc of vscode.workspace.textDocuments) {
            if (doc.uri.scheme === 'file' && !doc.isUntitled) {
                files.push({
                    path: doc.uri.fsPath,
                    content: doc.getText(),
                    hash: this.hashContent(doc.getText()),
                });
            }
        }

        const snapshot: Snapshot = {
            id: `snap_${Date.now()}`,
            experimentId,
            timestamp: new Date(),
            files,
            metadata: {},
        };

        this.snapshots.set(experimentId, snapshot);
        return snapshot;
    }

    private hashContent(content: string): string {
        let hash = 0;
        for (let i = 0; i < content.length; i++) {
            const char = content.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash;
        }
        return hash.toString(16);
    }

    // ============================================================================
    // Isolated Execution
    // ============================================================================

    async executeInSandbox(
        code: string,
        language: string,
        options: { timeout?: number; inputs?: any[] } = {}
    ): Promise<{ output: any; error?: string; duration: number }> {
        const startTime = Date.now();

        try {
            // Send to backend for sandboxed execution
            const response = await this.bridge.invokeAgent('sandbox_execute', {
                code,
                language,
                timeout: options.timeout || 5000,
                inputs: options.inputs,
            });

            const duration = Date.now() - startTime;

            if (response.success) {
                return {
                    output: response.data?.output,
                    duration,
                };
            } else {
                return {
                    output: null,
                    error: response.error,
                    duration,
                };
            }
        } catch (error: any) {
            return {
                output: null,
                error: error.message,
                duration: Date.now() - startTime,
            };
        }
    }

    async testCodeChange(
        originalCode: string,
        modifiedCode: string,
        testCases: Array<{ input: any; expectedOutput: any }>
    ): Promise<{
        passed: number;
        failed: number;
        results: Array<{ input: any; expected: any; actual: any; passed: boolean }>;
    }> {
        const results: Array<{ input: any; expected: any; actual: any; passed: boolean }> = [];

        for (const testCase of testCases) {
            const execution = await this.executeInSandbox(modifiedCode, 'javascript', {
                inputs: [testCase.input],
            });

            const passed = JSON.stringify(execution.output) === JSON.stringify(testCase.expectedOutput);

            results.push({
                input: testCase.input,
                expected: testCase.expectedOutput,
                actual: execution.output,
                passed,
            });
        }

        return {
            passed: results.filter(r => r.passed).length,
            failed: results.filter(r => !r.passed).length,
            results,
        };
    }

    // ============================================================================
    // A/B Testing
    // ============================================================================

    createABTest(
        name: string,
        controlCode: string,
        treatmentCode: string,
        testCases: Array<{ input: any; expectedOutput: any }>
    ): Experiment {
        return this.createExperiment(name, 'a_b_test', {
            description: 'A/B test between control and treatment code',
            hypothesis: 'Treatment code performs better than control',
            variables: [
                { name: 'code', controlValue: controlCode, treatmentValue: treatmentCode },
            ],
            metrics: [
                { name: 'correctness', type: 'percentage' },
                { name: 'execution_time', type: 'duration' },
            ],
        });
    }

    async runABTest(experimentId: string): Promise<ExperimentResults | null> {
        const experiment = this.experiments.get(experimentId);
        if (!experiment || experiment.type !== 'a_b_test') return null;

        await this.startExperiment(experimentId);

        const codeVariable = experiment.variables.find(v => v.name === 'code');
        if (!codeVariable) {
            return this.stopExperiment(experimentId, false);
        }

        // Run control
        const controlResult = await this.executeInSandbox(
            codeVariable.controlValue,
            'javascript',
            { timeout: 5000 }
        );

        // Run treatment
        const treatmentResult = await this.executeInSandbox(
            codeVariable.treatmentValue,
            'javascript',
            { timeout: 5000 }
        );

        // Record metrics
        const correctnessMetric = experiment.metrics.find(m => m.name === 'correctness');
        const timeMetric = experiment.metrics.find(m => m.name === 'execution_time');

        if (correctnessMetric) {
            correctnessMetric.controlValue = controlResult.error ? 0 : 100;
            correctnessMetric.treatmentValue = treatmentResult.error ? 0 : 100;
        }

        if (timeMetric) {
            timeMetric.controlValue = controlResult.duration;
            timeMetric.treatmentValue = treatmentResult.duration;
        }

        return this.stopExperiment(experimentId, true);
    }

    // ============================================================================
    // Results Analysis
    // ============================================================================

    private calculateResults(experiment: Experiment): ExperimentResults {
        const metrics: ExperimentResults['metrics'] = {};

        for (const metric of experiment.metrics) {
            if (metric.controlValue !== undefined && metric.treatmentValue !== undefined) {
                const improvement =
                    metric.type === 'duration'
                        ? ((metric.controlValue - metric.treatmentValue) / metric.controlValue) * 100
                        : ((metric.treatmentValue - metric.controlValue) / metric.controlValue) * 100;

                metrics[metric.name] = {
                    control: metric.controlValue,
                    treatment: metric.treatmentValue,
                    improvement,
                };
            }
        }

        // Calculate overall success
        const improvements = Object.values(metrics).map(m => m.improvement);
        const avgImprovement = improvements.length > 0
            ? improvements.reduce((a, b) => a + b, 0) / improvements.length
            : 0;

        const success = avgImprovement > 0;
        const recommendation: ExperimentResults['recommendation'] =
            avgImprovement > 10 ? 'adopt' :
            avgImprovement < -10 ? 'reject' : 'continue';

        return {
            success,
            summary: `Average improvement: ${avgImprovement.toFixed(1)}%`,
            metrics,
            recommendation,
            confidence: Math.min(0.95, 0.5 + Math.abs(avgImprovement) / 100),
        };
    }

    // ============================================================================
    // Utilities
    // ============================================================================

    private log(message: string): void {
        const timestamp = new Date().toISOString();
        this.outputChannel.appendLine(`[${timestamp}] ${message}`);
        this.core.log(`Sandbox: ${message}`);
    }

    showOutput(): void {
        this.outputChannel.show();
    }

    getExperiments(): Experiment[] {
        return Array.from(this.experiments.values());
    }

    getExperiment(id: string): Experiment | undefined {
        return this.experiments.get(id);
    }

    dispose(): void {
        this.outputChannel.dispose();
    }
}
