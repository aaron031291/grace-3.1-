/**
 * Autonomous Scheduler
 *
 * Background task orchestration for Grace OS.
 * Manages scheduled tasks, background jobs, and autonomous operations.
 */

import * as vscode from 'vscode';
import { GraceOSCore } from './GraceOSCore';
import { IDEBridge, AutonomousTask } from '../bridges/IDEBridge';
import { v4 as uuidv4 } from 'uuid';

export interface ScheduledTask {
    id: string;
    name: string;
    type: 'diagnostic' | 'memory_consolidation' | 'learning' | 'cicd' | 'custom';
    schedule: 'once' | 'interval' | 'cron';
    intervalMs?: number;
    cronExpression?: string;
    nextRun?: Date;
    lastRun?: Date;
    status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
    result?: any;
    error?: string;
    metadata?: Record<string, any>;
}

export class AutonomousScheduler implements vscode.TreeDataProvider<ScheduledTask> {
    private core: GraceOSCore;
    private bridge: IDEBridge;
    private tasks: Map<string, ScheduledTask> = new Map();
    private timers: Map<string, NodeJS.Timeout> = new Map();
    private isRunning: boolean = false;
    private _onDidChangeTreeData = new vscode.EventEmitter<ScheduledTask | undefined>();
    readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

    constructor(core: GraceOSCore, bridge: IDEBridge) {
        this.core = core;
        this.bridge = bridge;
    }

    async start(): Promise<void> {
        if (this.isRunning) return;

        this.core.log('Starting Autonomous Scheduler...');
        this.isRunning = true;

        // Schedule default tasks based on configuration
        const config = this.core.getConfig();

        // Diagnostic task
        if (config.diagnostics.autoRun) {
            this.scheduleTask({
                name: 'System Diagnostics',
                type: 'diagnostic',
                schedule: 'interval',
                intervalMs: config.diagnostics.interval,
            });
        }

        // Memory consolidation task
        if (config.memory.autoStore) {
            this.scheduleTask({
                name: 'Memory Consolidation',
                type: 'memory_consolidation',
                schedule: 'interval',
                intervalMs: config.memory.consolidationInterval,
            });
        }

        // Learning patterns task
        if (config.learning.recordPatterns) {
            this.scheduleTask({
                name: 'Learning Pattern Analysis',
                type: 'learning',
                schedule: 'interval',
                intervalMs: 600000, // 10 minutes
            });
        }

        this.core.log('Autonomous Scheduler started');
        this.core.enableFeature('autonomousScheduler');
    }

    stop(): void {
        this.core.log('Stopping Autonomous Scheduler...');
        this.isRunning = false;

        // Clear all timers
        this.timers.forEach((timer, id) => {
            clearTimeout(timer);
            clearInterval(timer);
        });
        this.timers.clear();

        this.core.disableFeature('autonomousScheduler');
    }

    scheduleTask(taskConfig: Partial<ScheduledTask>): string {
        const task: ScheduledTask = {
            id: uuidv4(),
            name: taskConfig.name || 'Unnamed Task',
            type: taskConfig.type || 'custom',
            schedule: taskConfig.schedule || 'once',
            intervalMs: taskConfig.intervalMs,
            cronExpression: taskConfig.cronExpression,
            status: 'pending',
            metadata: taskConfig.metadata,
        };

        this.tasks.set(task.id, task);
        this.core.log(`Scheduled task: ${task.name} (${task.id})`);

        // Set up execution
        if (task.schedule === 'once') {
            task.nextRun = new Date();
            this.executeTask(task.id);
        } else if (task.schedule === 'interval' && task.intervalMs) {
            task.nextRun = new Date(Date.now() + task.intervalMs);
            const timer = setInterval(() => this.executeTask(task.id), task.intervalMs);
            this.timers.set(task.id, timer);
        }

        this._onDidChangeTreeData.fire(undefined);
        return task.id;
    }

    cancelTask(taskId: string): boolean {
        const task = this.tasks.get(taskId);
        if (!task) return false;

        // Clear timer if exists
        const timer = this.timers.get(taskId);
        if (timer) {
            clearTimeout(timer);
            clearInterval(timer);
            this.timers.delete(taskId);
        }

        task.status = 'cancelled';
        this.tasks.set(taskId, task);
        this._onDidChangeTreeData.fire(undefined);

        this.core.log(`Cancelled task: ${task.name}`);
        return true;
    }

    private async executeTask(taskId: string): Promise<void> {
        const task = this.tasks.get(taskId);
        if (!task || task.status === 'cancelled') return;

        this.core.log(`Executing task: ${task.name}`);
        task.status = 'running';
        task.lastRun = new Date();
        this._onDidChangeTreeData.fire(undefined);

        this.core.updateState({
            pendingTasks: Array.from(this.tasks.values()).filter(t => t.status === 'running').length,
        });

        try {
            let result: any;

            switch (task.type) {
                case 'diagnostic':
                    result = await this.runDiagnosticTask();
                    break;
                case 'memory_consolidation':
                    result = await this.runMemoryConsolidationTask();
                    break;
                case 'learning':
                    result = await this.runLearningTask();
                    break;
                case 'cicd':
                    result = await this.runCICDTask(task.metadata);
                    break;
                case 'custom':
                    result = await this.runCustomTask(task.metadata);
                    break;
            }

            task.result = result;
            task.status = task.schedule === 'once' ? 'completed' : 'pending';
            task.error = undefined;

            this.core.log(`Task completed: ${task.name}`);

        } catch (error: any) {
            task.status = 'failed';
            task.error = error.message;
            this.core.log(`Task failed: ${task.name} - ${error.message}`, 'error');
        }

        if (task.schedule === 'interval' && task.intervalMs) {
            task.nextRun = new Date(Date.now() + task.intervalMs);
        }

        this.tasks.set(taskId, task);
        this._onDidChangeTreeData.fire(undefined);

        this.core.updateState({
            pendingTasks: Array.from(this.tasks.values()).filter(t => t.status === 'running').length,
        });
    }

    private async runDiagnosticTask(): Promise<any> {
        const response = await this.bridge.runDiagnostics();
        if (response.success && response.data) {
            // Update health status based on diagnostics
            const hasErrors = response.data.some((d: any) => d.status === 'error');
            const hasWarnings = response.data.some((d: any) => d.status === 'warning');

            this.core.updateState({
                healthStatus: hasErrors ? 'unhealthy' : hasWarnings ? 'degraded' : 'healthy',
                lastHealthCheck: new Date(),
            });
        }
        return response.data;
    }

    private async runMemoryConsolidationTask(): Promise<any> {
        const response = await this.bridge.triggerMemoryConsolidation();
        return response.success ? { consolidated: true } : { error: response.error };
    }

    private async runLearningTask(): Promise<any> {
        // Analyze recent coding patterns
        const history = await this.core.getWorkspaceData<any>('ghostLedger.history');
        if (history) {
            // Extract patterns and send to backend for learning
            const patterns = this.extractCodingPatterns(history);
            if (patterns.length > 0) {
                await this.bridge.recordLearningInsight(
                    JSON.stringify(patterns),
                    'coding_patterns',
                    { source: 'autonomous_scheduler' }
                );
            }
        }
        return { analyzed: true };
    }

    private extractCodingPatterns(history: Record<string, any[]>): any[] {
        const patterns: any[] = [];

        for (const [filePath, changes] of Object.entries(history)) {
            // Analyze change frequency
            const changeCount = changes.length;
            if (changeCount > 10) {
                patterns.push({
                    type: 'high_activity_file',
                    filePath,
                    changeCount,
                });
            }

            // Analyze change types
            const changeTypes = changes.reduce((acc: Record<string, number>, c: any) => {
                acc[c.changeType] = (acc[c.changeType] || 0) + 1;
                return acc;
            }, {});

            if (changeTypes.modify > changeTypes.insert * 2) {
                patterns.push({
                    type: 'refactoring_activity',
                    filePath,
                    ratio: changeTypes.modify / (changeTypes.insert || 1),
                });
            }
        }

        return patterns;
    }

    private async runCICDTask(metadata?: Record<string, any>): Promise<any> {
        const response = await this.bridge.triggerCICDPipeline(metadata?.pipelineId);
        return response.data;
    }

    private async runCustomTask(metadata?: Record<string, any>): Promise<any> {
        if (metadata?.action) {
            // Execute custom action via agent
            const response = await this.bridge.invokeAgent(metadata.action, metadata);
            return response.data;
        }
        return { executed: true };
    }

    // TreeDataProvider implementation

    getTreeItem(element: ScheduledTask): vscode.TreeItem {
        const item = new vscode.TreeItem(element.name);

        const statusIcons: Record<string, string> = {
            pending: '$(clock)',
            running: '$(sync~spin)',
            completed: '$(check)',
            failed: '$(error)',
            cancelled: '$(circle-slash)',
        };

        item.iconPath = new vscode.ThemeIcon(statusIcons[element.status].replace('$(', '').replace(')', ''));
        item.description = `${element.type} - ${element.status}`;

        if (element.nextRun) {
            item.tooltip = `Next run: ${element.nextRun.toLocaleString()}`;
        }

        item.contextValue = element.status === 'running' ? 'runningTask' : 'pendingTask';

        return item;
    }

    getChildren(element?: ScheduledTask): ScheduledTask[] {
        if (element) {
            return [];
        }

        return Array.from(this.tasks.values()).sort((a, b) => {
            // Running tasks first, then by next run time
            if (a.status === 'running' && b.status !== 'running') return -1;
            if (b.status === 'running' && a.status !== 'running') return 1;
            if (a.nextRun && b.nextRun) {
                return a.nextRun.getTime() - b.nextRun.getTime();
            }
            return 0;
        });
    }

    refresh(): void {
        this._onDidChangeTreeData.fire(undefined);
    }

    getTasks(): ScheduledTask[] {
        return Array.from(this.tasks.values());
    }

    getTask(taskId: string): ScheduledTask | undefined {
        return this.tasks.get(taskId);
    }

    dispose(): void {
        this.stop();
        this._onDidChangeTreeData.dispose();
    }
}
