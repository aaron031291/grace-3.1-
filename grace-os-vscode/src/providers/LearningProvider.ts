/**
 * Learning Provider
 *
 * Integrates Grace's learning and knowledge acquisition into VSCode.
 * Records insights, tracks patterns, and facilitates continuous learning.
 */

import * as vscode from 'vscode';
import { GraceOSCore } from '../core/GraceOSCore';
import { IDEBridge, LearningInsight } from '../bridges/IDEBridge';

export interface LearningNode {
    id: string;
    label: string;
    type: 'category' | 'insight';
    category?: string;
    insight?: LearningInsight;
    children?: LearningNode[];
}

export class LearningProvider implements vscode.TreeDataProvider<LearningNode> {
    private core: GraceOSCore;
    private bridge: IDEBridge;
    private insights: Map<string, LearningInsight[]> = new Map();
    private _onDidChangeTreeData = new vscode.EventEmitter<LearningNode | undefined>();
    readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

    private categories = [
        'coding_patterns',
        'best_practices',
        'debugging',
        'architecture',
        'performance',
        'security',
        'documentation',
        'general',
    ];

    constructor(core: GraceOSCore, bridge: IDEBridge) {
        this.core = core;
        this.bridge = bridge;

        // Listen for learning events
        this.core.on('learningEvent', (data: any) => {
            this.handleLearningEvent(data);
        });
    }

    private handleLearningEvent(data: any): void {
        if (data.insight) {
            const category = data.insight.category || 'general';
            const existing = this.insights.get(category) || [];
            existing.unshift(data.insight); // Add to beginning
            this.insights.set(category, existing.slice(0, 50)); // Keep last 50
            this.refresh();
        }
    }

    async initialize(): Promise<void> {
        await this.loadHistory();
        this.core.enableFeature('learning');
    }

    private async loadHistory(): Promise<void> {
        const response = await this.bridge.getLearningHistory(100);

        if (response.success && response.data) {
            // Organize by category
            for (const insight of response.data) {
                const category = insight.category || 'general';
                const existing = this.insights.get(category) || [];
                existing.push(insight);
                this.insights.set(category, existing);
            }
        }
    }

    // TreeDataProvider implementation

    getTreeItem(element: LearningNode): vscode.TreeItem {
        const item = new vscode.TreeItem(element.label);

        if (element.type === 'category') {
            item.collapsibleState = vscode.TreeItemCollapsibleState.Collapsed;
            item.iconPath = new vscode.ThemeIcon('mortar-board');
            const count = this.insights.get(element.category!)?.length || 0;
            item.description = `${count} insights`;
        } else {
            item.collapsibleState = vscode.TreeItemCollapsibleState.None;
            item.iconPath = this.getTrustIcon(element.insight?.trustScore || 0);
            item.description = element.insight?.timestamp
                ? new Date(element.insight.timestamp).toLocaleDateString()
                : '';
            item.tooltip = new vscode.MarkdownString(
                `**Trust Score:** ${((element.insight?.trustScore || 0) * 100).toFixed(0)}%\n\n` +
                element.insight?.content
            );

            item.command = {
                command: 'graceOS.learning.viewInsight',
                title: 'View Insight',
                arguments: [element.insight],
            };
        }

        item.contextValue = element.type;
        return item;
    }

    private getTrustIcon(trustScore: number): vscode.ThemeIcon {
        if (trustScore >= 0.8) {
            return new vscode.ThemeIcon('verified-filled', new vscode.ThemeColor('testing.iconPassed'));
        } else if (trustScore >= 0.5) {
            return new vscode.ThemeIcon('verified', new vscode.ThemeColor('warningForeground'));
        }
        return new vscode.ThemeIcon('unverified');
    }

    getChildren(element?: LearningNode): LearningNode[] {
        if (!element) {
            // Root level - show categories
            return this.categories
                .filter(cat => (this.insights.get(cat)?.length || 0) > 0)
                .map(category => ({
                    id: category,
                    label: this.formatCategory(category),
                    type: 'category' as const,
                    category,
                }));
        }

        if (element.type === 'category' && element.category) {
            // Show insights for this category
            const categoryInsights = this.insights.get(element.category) || [];
            return categoryInsights.map(insight => ({
                id: insight.id,
                label: this.truncate(insight.content, 40),
                type: 'insight' as const,
                insight,
            }));
        }

        return [];
    }

    private formatCategory(category: string): string {
        return category
            .split('_')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    }

    private truncate(str: string, length: number): string {
        if (str.length <= length) return str;
        return str.substring(0, length) + '...';
    }

    // Public API

    async recordInsight(): Promise<void> {
        const editor = vscode.window.activeTextEditor;

        // Get content
        let content: string;
        if (editor && !editor.selection.isEmpty) {
            content = editor.document.getText(editor.selection);
        } else {
            const input = await vscode.window.showInputBox({
                prompt: 'Enter the learning insight',
                placeHolder: 'What did you learn?',
            });
            if (!input) return;
            content = input;
        }

        // Select category
        const category = await vscode.window.showQuickPick(
            this.categories.map(c => ({
                label: this.formatCategory(c),
                value: c,
            })),
            { placeHolder: 'Select category' }
        );

        if (!category) return;

        await vscode.window.withProgress(
            {
                location: vscode.ProgressLocation.Notification,
                title: 'Recording insight...',
            },
            async () => {
                const response = await this.bridge.recordLearningInsight(content, category.value, {
                    source: 'vscode',
                    filePath: editor?.document.uri.fsPath,
                    language: editor?.document.languageId,
                });

                if (response.success && response.data) {
                    vscode.window.showInformationMessage('Learning insight recorded');

                    // Add to local cache
                    const existing = this.insights.get(category.value) || [];
                    existing.unshift(response.data);
                    this.insights.set(category.value, existing);

                    this.refresh();
                } else {
                    vscode.window.showErrorMessage(`Failed to record insight: ${response.error}`);
                }
            }
        );
    }

    async viewHistory(): Promise<void> {
        await vscode.window.withProgress(
            {
                location: vscode.ProgressLocation.Notification,
                title: 'Loading learning history...',
            },
            async () => {
                await this.loadHistory();
                this.refresh();

                // Show in webview or quick pick
                const allInsights: LearningInsight[] = [];
                this.insights.forEach(insights => allInsights.push(...insights));

                allInsights.sort((a, b) =>
                    new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
                );

                const items = allInsights.slice(0, 50).map(insight => ({
                    label: this.truncate(insight.content, 50),
                    description: `${insight.category} - ${((insight.trustScore || 0) * 100).toFixed(0)}%`,
                    detail: insight.content,
                    insight,
                }));

                const selected = await vscode.window.showQuickPick(items, {
                    placeHolder: 'Learning History',
                    matchOnDetail: true,
                });

                if (selected) {
                    this.showInsightDetail(selected.insight);
                }
            }
        );
    }

    async viewInsight(insight: LearningInsight): Promise<void> {
        this.showInsightDetail(insight);
    }

    private async showInsightDetail(insight: LearningInsight): Promise<void> {
        const content = [
            `# Learning Insight`,
            '',
            `**ID:** \`${insight.id}\``,
            '',
            `**Category:** ${this.formatCategory(insight.category)}`,
            '',
            `**Trust Score:** ${((insight.trustScore || 0) * 100).toFixed(1)}%`,
            '',
            `**Recorded:** ${new Date(insight.timestamp).toLocaleString()}`,
            '',
            `## Content`,
            '',
            insight.content,
        ].join('\n');

        const doc = await vscode.workspace.openTextDocument({
            content,
            language: 'markdown',
        });

        await vscode.window.showTextDocument(doc, { preview: true });
    }

    refresh(): void {
        this._onDidChangeTreeData.fire(undefined);
    }

    dispose(): void {
        this._onDidChangeTreeData.dispose();
    }
}
