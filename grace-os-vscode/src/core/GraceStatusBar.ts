/**
 * Grace Status Bar
 *
 * Status bar integration showing Grace OS status, health, and quick actions.
 */

import * as vscode from 'vscode';
import { GraceOSCore } from './GraceOSCore';

export class GraceStatusBar {
    private core: GraceOSCore;
    private mainStatusItem: vscode.StatusBarItem;
    private healthStatusItem: vscode.StatusBarItem;
    private memoryStatusItem: vscode.StatusBarItem;
    private tasksStatusItem: vscode.StatusBarItem;

    constructor(core: GraceOSCore) {
        this.core = core;

        // Main Grace OS status
        this.mainStatusItem = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Left,
            100
        );
        this.mainStatusItem.command = 'graceOS.activate';

        // Health status
        this.healthStatusItem = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Left,
            99
        );
        this.healthStatusItem.command = 'graceOS.diagnostic.viewHealth';

        // Memory status
        this.memoryStatusItem = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Left,
            98
        );
        this.memoryStatusItem.command = 'graceOS.memory.query';

        // Tasks status
        this.tasksStatusItem = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Left,
            97
        );
        this.tasksStatusItem.command = 'graceOS.autonomous.viewTasks';

        // Listen for state changes
        this.core.on('stateChanged', () => this.update());
        this.core.on('connectionChanged', () => this.update());
    }

    show(): void {
        this.update();
        this.mainStatusItem.show();
        this.healthStatusItem.show();
        this.memoryStatusItem.show();
        this.tasksStatusItem.show();
    }

    hide(): void {
        this.mainStatusItem.hide();
        this.healthStatusItem.hide();
        this.memoryStatusItem.hide();
        this.tasksStatusItem.hide();
    }

    private update(): void {
        const state = this.core.getState();

        // Main status
        if (state.isConnected) {
            this.mainStatusItem.text = '$(brain) Grace OS';
            this.mainStatusItem.backgroundColor = undefined;
            this.mainStatusItem.tooltip = 'Grace OS - Connected';
        } else {
            this.mainStatusItem.text = '$(brain) Grace OS (Offline)';
            this.mainStatusItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
            this.mainStatusItem.tooltip = 'Grace OS - Disconnected. Click to reconnect.';
        }

        // Health status
        const healthIcons: Record<string, string> = {
            healthy: '$(check)',
            degraded: '$(warning)',
            unhealthy: '$(error)',
            unknown: '$(question)',
        };
        const healthColors: Record<string, vscode.ThemeColor | undefined> = {
            healthy: undefined,
            degraded: new vscode.ThemeColor('statusBarItem.warningBackground'),
            unhealthy: new vscode.ThemeColor('statusBarItem.errorBackground'),
            unknown: undefined,
        };
        this.healthStatusItem.text = `${healthIcons[state.healthStatus]} Health`;
        this.healthStatusItem.backgroundColor = healthColors[state.healthStatus];
        this.healthStatusItem.tooltip = `System health: ${state.healthStatus}`;

        // Memory status
        this.memoryStatusItem.text = `$(database) ${state.activeGenesisKeys} keys`;
        this.memoryStatusItem.tooltip = `Active Genesis Keys: ${state.activeGenesisKeys}`;

        // Tasks status
        if (state.pendingTasks > 0) {
            this.tasksStatusItem.text = `$(sync~spin) ${state.pendingTasks} tasks`;
            this.tasksStatusItem.tooltip = `${state.pendingTasks} autonomous tasks running`;
        } else {
            this.tasksStatusItem.text = '$(check-all) Tasks';
            this.tasksStatusItem.tooltip = 'No pending tasks';
        }
    }

    setHealth(status: 'healthy' | 'degraded' | 'unhealthy' | 'unknown'): void {
        this.core.updateState({ healthStatus: status });
    }

    setPendingTasks(count: number): void {
        this.core.updateState({ pendingTasks: count });
    }

    setActiveGenesisKeys(count: number): void {
        this.core.updateState({ activeGenesisKeys: count });
    }

    dispose(): void {
        this.mainStatusItem.dispose();
        this.healthStatusItem.dispose();
        this.memoryStatusItem.dispose();
        this.tasksStatusItem.dispose();
    }
}
