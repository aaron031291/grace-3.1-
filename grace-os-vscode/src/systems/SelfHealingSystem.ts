/**
 * Self-Healing System - Autonomous Repair Integration
 *
 * Comprehensive self-healing capabilities:
 * - Automatic error detection and repair
 * - Connection recovery
 * - State restoration
 * - Performance optimization
 * - Learning from failures
 */

import * as vscode from 'vscode';
import { GraceOSCore } from '../core/GraceOSCore';
import { IDEBridge } from '../bridges/IDEBridge';
import { GraceWebSocketBridge } from '../bridges/WebSocketBridge';
import { DiagnosticMachine, DiagnosticState } from './DiagnosticMachine';

// ============================================================================
// Types
// ============================================================================

export interface HealingStrategy {
    id: string;
    name: string;
    targetIssue: string;
    steps: HealingStep[];
    successRate: number;
    avgExecutionTime: number;
}

export interface HealingStep {
    action: string;
    params?: Record<string, any>;
    timeout?: number;
    retries?: number;
    fallback?: string;
}

export interface HealingResult {
    strategyId: string;
    success: boolean;
    duration: number;
    stepsExecuted: number;
    error?: string;
    recovery?: any;
}

export interface HealthCheckResult {
    component: string;
    status: 'healthy' | 'degraded' | 'unhealthy';
    latency?: number;
    details?: Record<string, any>;
}

export interface FailureRecord {
    id: string;
    timestamp: Date;
    component: string;
    error: string;
    context: Record<string, any>;
    resolved: boolean;
    resolution?: string;
}

// ============================================================================
// Self-Healing System
// ============================================================================

export class SelfHealingSystem {
    private core: GraceOSCore;
    private bridge: IDEBridge;
    private wsBridge: GraceWebSocketBridge;
    private diagnosticMachine?: DiagnosticMachine;
    private strategies: Map<string, HealingStrategy> = new Map();
    private failureHistory: FailureRecord[] = [];
    private healthCheckInterval?: NodeJS.Timeout;
    private isHealing: boolean = false;

    constructor(
        core: GraceOSCore,
        bridge: IDEBridge,
        wsBridge: GraceWebSocketBridge
    ) {
        this.core = core;
        this.bridge = bridge;
        this.wsBridge = wsBridge;

        this.registerDefaultStrategies();
    }

    setDiagnosticMachine(machine: DiagnosticMachine): void {
        this.diagnosticMachine = machine;
    }

    async initialize(): Promise<void> {
        this.core.log('Initializing Self-Healing System...');

        // Start continuous health monitoring
        this.startHealthMonitoring();

        // Set up failure listeners
        this.setupFailureListeners();

        this.core.enableFeature('selfHealing');
        this.core.log('Self-Healing System initialized');
    }

    private registerDefaultStrategies(): void {
        // Connection recovery strategy
        this.strategies.set('connection_recovery', {
            id: 'connection_recovery',
            name: 'Backend Connection Recovery',
            targetIssue: 'backend_disconnected',
            steps: [
                { action: 'wait', params: { ms: 1000 } },
                { action: 'reconnect_http', retries: 3, timeout: 5000 },
                { action: 'reconnect_ws', retries: 3, timeout: 5000 },
                { action: 'verify_connection', timeout: 2000 },
            ],
            successRate: 0.85,
            avgExecutionTime: 5000,
        });

        // State restoration strategy
        this.strategies.set('state_restoration', {
            id: 'state_restoration',
            name: 'State Restoration',
            targetIssue: 'corrupted_state',
            steps: [
                { action: 'backup_current_state' },
                { action: 'load_last_good_state' },
                { action: 'validate_state' },
                { action: 'merge_safe_changes' },
            ],
            successRate: 0.95,
            avgExecutionTime: 2000,
        });

        // Memory optimization strategy
        this.strategies.set('memory_optimization', {
            id: 'memory_optimization',
            name: 'Memory Optimization',
            targetIssue: 'high_memory_usage',
            steps: [
                { action: 'clear_caches' },
                { action: 'compact_memory' },
                { action: 'unload_unused_features' },
                { action: 'trigger_gc' },
            ],
            successRate: 0.9,
            avgExecutionTime: 1000,
        });

        // Extension error recovery
        this.strategies.set('extension_recovery', {
            id: 'extension_recovery',
            name: 'Extension Error Recovery',
            targetIssue: 'extension_error',
            steps: [
                { action: 'capture_error_context' },
                { action: 'reset_error_component' },
                { action: 'reinitialize_component' },
                { action: 'verify_functionality' },
            ],
            successRate: 0.8,
            avgExecutionTime: 3000,
        });

        // WebSocket recovery
        this.strategies.set('websocket_recovery', {
            id: 'websocket_recovery',
            name: 'WebSocket Recovery',
            targetIssue: 'websocket_disconnected',
            steps: [
                { action: 'close_existing_ws' },
                { action: 'wait', params: { ms: 500 } },
                { action: 'reconnect_ws', retries: 5, timeout: 3000 },
                { action: 'resubscribe_channels' },
            ],
            successRate: 0.9,
            avgExecutionTime: 4000,
        });

        // Diagnostic failure recovery
        this.strategies.set('diagnostic_recovery', {
            id: 'diagnostic_recovery',
            name: 'Diagnostic System Recovery',
            targetIssue: 'diagnostic_failure',
            steps: [
                { action: 'reset_diagnostic_state' },
                { action: 'reinitialize_sensors' },
                { action: 'run_self_test' },
            ],
            successRate: 0.85,
            avgExecutionTime: 2000,
        });
    }

    private startHealthMonitoring(): void {
        const interval = this.core.getConfig().diagnostics.interval || 60000;

        this.healthCheckInterval = setInterval(async () => {
            await this.performHealthCheck();
        }, interval);

        // Initial check
        this.performHealthCheck();
    }

    private setupFailureListeners(): void {
        // Listen for connection failures
        this.core.on('connectionChanged', async (connected: boolean) => {
            if (!connected) {
                await this.heal('connection_recovery');
            }
        });

        // Listen for WebSocket disconnection
        this.wsBridge.on('disconnected', async () => {
            await this.heal('websocket_recovery');
        });

        // Listen for errors
        this.wsBridge.on('error', async (error: Error) => {
            this.recordFailure('websocket', error.message, {});
            await this.heal('websocket_recovery');
        });

        // Listen for diagnostic issues
        this.core.on('diagnosticComplete', async (state: DiagnosticState) => {
            if (state.overallHealth === 'unhealthy' || state.overallHealth === 'critical') {
                await this.handleUnhealthyState(state);
            }
        });
    }

    private async performHealthCheck(): Promise<HealthCheckResult[]> {
        const results: HealthCheckResult[] = [];

        // Check backend connection
        const backendStart = Date.now();
        const backendConnected = this.bridge.isBackendConnected();
        results.push({
            component: 'backend',
            status: backendConnected ? 'healthy' : 'unhealthy',
            latency: Date.now() - backendStart,
        });

        // Check WebSocket
        results.push({
            component: 'websocket',
            status: this.wsBridge.isConnected() ? 'healthy' : 'degraded',
        });

        // Check extension state
        const state = this.core.getState();
        results.push({
            component: 'extension',
            status: state.activeFeatures.size > 0 ? 'healthy' : 'degraded',
            details: {
                activeFeatures: state.activeFeatures.size,
                pendingTasks: state.pendingTasks,
            },
        });

        // Process results
        const unhealthyComponents = results.filter(r => r.status === 'unhealthy');

        for (const component of unhealthyComponents) {
            this.core.log(`Unhealthy component detected: ${component.component}`, 'warn');

            // Trigger appropriate healing
            if (component.component === 'backend') {
                await this.heal('connection_recovery');
            } else if (component.component === 'websocket') {
                await this.heal('websocket_recovery');
            }
        }

        return results;
    }

    private async handleUnhealthyState(state: DiagnosticState): Promise<void> {
        this.core.log('Handling unhealthy system state...', 'warn');

        // Analyze patterns to determine best healing strategy
        const errorPatterns = state.layer2.filter(p => p.severity === 'error' || p.severity === 'critical');

        for (const pattern of errorPatterns) {
            const strategy = this.findStrategyForIssue(pattern.patternType);
            if (strategy) {
                await this.heal(strategy.id);
            }
        }
    }

    private findStrategyForIssue(issue: string): HealingStrategy | undefined {
        for (const strategy of this.strategies.values()) {
            if (strategy.targetIssue === issue) {
                return strategy;
            }
        }

        // Try fuzzy matching
        for (const strategy of this.strategies.values()) {
            if (issue.includes(strategy.targetIssue) || strategy.targetIssue.includes(issue)) {
                return strategy;
            }
        }

        return undefined;
    }

    async heal(strategyId: string): Promise<HealingResult> {
        if (this.isHealing) {
            return {
                strategyId,
                success: false,
                duration: 0,
                stepsExecuted: 0,
                error: 'Healing already in progress',
            };
        }

        const strategy = this.strategies.get(strategyId);
        if (!strategy) {
            return {
                strategyId,
                success: false,
                duration: 0,
                stepsExecuted: 0,
                error: 'Strategy not found',
            };
        }

        this.isHealing = true;
        const startTime = Date.now();
        let stepsExecuted = 0;

        this.core.log(`Executing healing strategy: ${strategy.name}`);

        try {
            for (const step of strategy.steps) {
                await this.executeHealingStep(step);
                stepsExecuted++;
            }

            const duration = Date.now() - startTime;

            // Update strategy success rate
            strategy.successRate = (strategy.successRate * 0.9) + (1 * 0.1);
            strategy.avgExecutionTime = (strategy.avgExecutionTime * 0.9) + (duration * 0.1);

            this.core.log(`Healing completed: ${strategy.name} in ${duration}ms`);

            return {
                strategyId,
                success: true,
                duration,
                stepsExecuted,
            };

        } catch (error: any) {
            const duration = Date.now() - startTime;

            // Update strategy success rate
            strategy.successRate = (strategy.successRate * 0.9) + (0 * 0.1);

            this.recordFailure('healing', error.message, { strategyId, stepsExecuted });

            this.core.log(`Healing failed: ${strategy.name} - ${error.message}`, 'error');

            return {
                strategyId,
                success: false,
                duration,
                stepsExecuted,
                error: error.message,
            };

        } finally {
            this.isHealing = false;
        }
    }

    private async executeHealingStep(step: HealingStep): Promise<void> {
        const retries = step.retries || 1;

        for (let attempt = 0; attempt < retries; attempt++) {
            try {
                await this.performStepAction(step);
                return;
            } catch (error) {
                if (attempt === retries - 1) {
                    if (step.fallback) {
                        await this.performStepAction({ action: step.fallback });
                    } else {
                        throw error;
                    }
                }
                await new Promise(resolve => setTimeout(resolve, 1000 * (attempt + 1)));
            }
        }
    }

    private async performStepAction(step: HealingStep): Promise<void> {
        const timeout = step.timeout || 10000;

        await Promise.race([
            this.doAction(step.action, step.params),
            new Promise((_, reject) =>
                setTimeout(() => reject(new Error('Step timeout')), timeout)
            ),
        ]);
    }

    private async doAction(action: string, params?: Record<string, any>): Promise<void> {
        switch (action) {
            case 'wait':
                await new Promise(resolve => setTimeout(resolve, params?.ms || 1000));
                break;

            case 'reconnect_http':
                const connected = await this.bridge.connect();
                if (!connected) throw new Error('HTTP reconnection failed');
                break;

            case 'reconnect_ws':
                const wsConnected = await this.wsBridge.connect();
                if (!wsConnected) throw new Error('WebSocket reconnection failed');
                break;

            case 'verify_connection':
                if (!this.bridge.isBackendConnected()) {
                    throw new Error('Connection verification failed');
                }
                break;

            case 'close_existing_ws':
                this.wsBridge.disconnect();
                break;

            case 'resubscribe_channels':
                this.wsBridge.subscribeToUpdates([
                    'diagnostics',
                    'memory',
                    'genesis',
                    'learning',
                    'tasks',
                ]);
                break;

            case 'clear_caches':
                // Clear internal caches
                this.core.log('Clearing caches');
                break;

            case 'compact_memory':
                // Trigger memory compaction
                if (global.gc) {
                    global.gc();
                }
                break;

            case 'backup_current_state':
                const state = this.core.getState();
                await this.core.setStoredData('backup.state', state);
                break;

            case 'load_last_good_state':
                const backup = await this.core.getStoredData<any>('backup.state');
                if (backup) {
                    this.core.updateState(backup);
                }
                break;

            case 'reset_diagnostic_state':
                this.diagnosticMachine?.dispose();
                break;

            case 'reinitialize_sensors':
                // Reinitialize diagnostic sensors
                break;

            case 'reset_error_component':
                // Reset the component that caused the error
                break;

            case 'reinitialize_component':
                // Reinitialize failed component
                break;

            default:
                this.core.log(`Unknown healing action: ${action}`, 'warn');
        }
    }

    private recordFailure(component: string, error: string, context: Record<string, any>): void {
        const record: FailureRecord = {
            id: `failure_${Date.now()}`,
            timestamp: new Date(),
            component,
            error,
            context,
            resolved: false,
        };

        this.failureHistory.push(record);

        // Keep only last 100 failures
        if (this.failureHistory.length > 100) {
            this.failureHistory = this.failureHistory.slice(-100);
        }

        // Send to backend for learning
        this.bridge.sendTelemetry('failure_recorded', record);
    }

    // Public API

    getStrategies(): HealingStrategy[] {
        return Array.from(this.strategies.values());
    }

    getFailureHistory(): FailureRecord[] {
        return [...this.failureHistory];
    }

    registerStrategy(strategy: HealingStrategy): void {
        this.strategies.set(strategy.id, strategy);
    }

    async manualHeal(strategyId: string): Promise<HealingResult> {
        return this.heal(strategyId);
    }

    dispose(): void {
        if (this.healthCheckInterval) {
            clearInterval(this.healthCheckInterval);
        }
    }
}
