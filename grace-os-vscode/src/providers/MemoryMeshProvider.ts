/**
 * Memory Mesh Provider
 *
 * Integrates Grace's memory mesh into VSCode.
 * Provides context-aware suggestions and memory operations.
 */

import * as vscode from 'vscode';
import { GraceOSCore } from '../core/GraceOSCore';
import { IDEBridge, MemoryEntry, MemoryQuery } from '../bridges/IDEBridge';

export interface MemoryNode {
    id: string;
    label: string;
    type: 'category' | 'memory';
    memoryType?: string;
    content?: string;
    timestamp?: string;
    score?: number;
    children?: MemoryNode[];
}

export class MemoryMeshProvider implements vscode.TreeDataProvider<MemoryNode> {
    private core: GraceOSCore;
    private bridge: IDEBridge;
    private memories: Map<string, MemoryEntry[]> = new Map();
    private _onDidChangeTreeData = new vscode.EventEmitter<MemoryNode | undefined>();
    readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

    private memoryTypes = ['episodic', 'semantic', 'procedural', 'learning', 'context'];

    constructor(core: GraceOSCore, bridge: IDEBridge) {
        this.core = core;
        this.bridge = bridge;

        // Listen for memory updates
        this.core.on('memoryUpdate', () => this.refresh());
    }

    async initialize(): Promise<void> {
        await this.loadMemories();
        this.core.enableFeature('memoryMesh');
    }

    private async loadMemories(): Promise<void> {
        for (const memoryType of this.memoryTypes) {
            try {
                const response = await this.bridge.queryMemory({
                    query: '*',
                    limit: 20,
                    memoryTypes: [memoryType],
                });

                if (response.success && response.data) {
                    this.memories.set(memoryType, response.data);
                }
            } catch (error) {
                this.core.log(`Failed to load ${memoryType} memories`, 'error');
            }
        }
    }

    // TreeDataProvider implementation

    getTreeItem(element: MemoryNode): vscode.TreeItem {
        const item = new vscode.TreeItem(element.label);

        if (element.type === 'category') {
            item.collapsibleState = vscode.TreeItemCollapsibleState.Collapsed;
            item.iconPath = new vscode.ThemeIcon('database');
            const count = this.memories.get(element.memoryType!)?.length || 0;
            item.description = `${count} entries`;
        } else {
            item.collapsibleState = vscode.TreeItemCollapsibleState.None;
            item.iconPath = new vscode.ThemeIcon('note');
            item.description = element.timestamp ? new Date(element.timestamp).toLocaleDateString() : '';
            item.tooltip = element.content;

            item.command = {
                command: 'graceOS.memory.view',
                title: 'View Memory',
                arguments: [element],
            };
        }

        item.contextValue = element.type;
        return item;
    }

    getChildren(element?: MemoryNode): MemoryNode[] {
        if (!element) {
            // Root level - show memory types as categories
            return this.memoryTypes.map(type => ({
                id: type,
                label: this.formatMemoryType(type),
                type: 'category' as const,
                memoryType: type,
            }));
        }

        if (element.type === 'category' && element.memoryType) {
            // Show memories under category
            const memories = this.memories.get(element.memoryType) || [];
            return memories.map(memory => ({
                id: memory.id,
                label: this.truncate(memory.content, 50),
                type: 'memory' as const,
                memoryType: memory.memoryType,
                content: memory.content,
                timestamp: memory.timestamp,
                score: memory.score,
            }));
        }

        return [];
    }

    private formatMemoryType(type: string): string {
        return type.charAt(0).toUpperCase() + type.slice(1) + ' Memory';
    }

    private truncate(str: string, length: number): string {
        if (str.length <= length) return str;
        return str.substring(0, length) + '...';
    }

    // Public API

    async queryMemory(query: string): Promise<void> {
        const response = await this.bridge.queryMemory({
            query,
            limit: 20,
        });

        if (response.success && response.data) {
            // Show results in quick pick
            const items = response.data.map(memory => ({
                label: this.truncate(memory.content, 60),
                description: `${memory.memoryType} - ${(memory.score! * 100).toFixed(0)}% match`,
                detail: memory.content,
                memory,
            }));

            const selected = await vscode.window.showQuickPick(items, {
                placeHolder: 'Memory search results',
                matchOnDetail: true,
            });

            if (selected) {
                this.showMemoryDetail(selected.memory);
            }
        } else {
            vscode.window.showWarningMessage('No memories found');
        }
    }

    async storeMemory(): Promise<void> {
        const editor = vscode.window.activeTextEditor;

        // Get content to store
        let content: string;
        if (editor && !editor.selection.isEmpty) {
            content = editor.document.getText(editor.selection);
        } else {
            const input = await vscode.window.showInputBox({
                prompt: 'Enter content to store in memory',
                placeHolder: 'Memory content...',
            });
            if (!input) return;
            content = input;
        }

        // Select memory type
        const memoryType = await vscode.window.showQuickPick(
            this.memoryTypes.map(t => ({
                label: this.formatMemoryType(t),
                value: t,
            })),
            { placeHolder: 'Select memory type' }
        );

        if (!memoryType) return;

        // Store the memory
        const response = await this.bridge.storeMemory(content, memoryType.value, {
            source: 'vscode',
            filePath: editor?.document.uri.fsPath,
        });

        if (response.success) {
            vscode.window.showInformationMessage('Memory stored successfully');
            this.refresh();
        } else {
            vscode.window.showErrorMessage(`Failed to store memory: ${response.error}`);
        }
    }

    async ingestToMagma(): Promise<void> {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('No active editor');
            return;
        }

        const content = editor.selection.isEmpty
            ? editor.document.getText()
            : editor.document.getText(editor.selection);

        const sourceType = await vscode.window.showQuickPick(
            ['code', 'documentation', 'learning', 'context'],
            { placeHolder: 'Select source type' }
        );

        if (!sourceType) return;

        await vscode.window.withProgress(
            {
                location: vscode.ProgressLocation.Notification,
                title: 'Ingesting to Magma Memory...',
            },
            async () => {
                const response = await this.bridge.ingestToMagma(content, sourceType, {
                    filePath: editor.document.uri.fsPath,
                    language: editor.document.languageId,
                });

                if (response.success) {
                    vscode.window.showInformationMessage('Content ingested to Magma Memory');
                } else {
                    vscode.window.showErrorMessage(`Ingestion failed: ${response.error}`);
                }
            }
        );
    }

    async triggerConsolidation(): Promise<void> {
        await vscode.window.withProgress(
            {
                location: vscode.ProgressLocation.Notification,
                title: 'Triggering memory consolidation...',
            },
            async () => {
                const response = await this.bridge.triggerMemoryConsolidation();

                if (response.success) {
                    vscode.window.showInformationMessage('Memory consolidation triggered');
                    this.refresh();
                } else {
                    vscode.window.showErrorMessage(`Consolidation failed: ${response.error}`);
                }
            }
        );
    }

    private async showMemoryDetail(memory: MemoryEntry): Promise<void> {
        const doc = await vscode.workspace.openTextDocument({
            content: [
                `=== Memory Entry ===`,
                ``,
                `ID: ${memory.id}`,
                `Type: ${memory.memoryType}`,
                `Timestamp: ${new Date(memory.timestamp).toLocaleString()}`,
                memory.score ? `Relevance Score: ${(memory.score * 100).toFixed(1)}%` : '',
                ``,
                `--- Content ---`,
                memory.content,
                ``,
                memory.metadata ? `--- Metadata ---\n${JSON.stringify(memory.metadata, null, 2)}` : '',
            ].filter(Boolean).join('\n'),
            language: 'markdown',
        });

        await vscode.window.showTextDocument(doc, { preview: true });
    }

    viewMemory(node: MemoryNode): void {
        if (node.content) {
            this.showMemoryDetail({
                id: node.id,
                content: node.content,
                memoryType: node.memoryType || 'unknown',
                timestamp: node.timestamp || new Date().toISOString(),
                score: node.score,
            });
        }
    }

    refresh(): void {
        this.loadMemories().then(() => {
            this._onDidChangeTreeData.fire(undefined);
        });
    }

    dispose(): void {
        this._onDidChangeTreeData.dispose();
    }
}
