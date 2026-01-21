/**
 * Genesis Key Provider
 *
 * Integrates Grace's genesis key provenance system into VSCode.
 * Tracks code lineage and provides full audit trail capabilities.
 */

import * as vscode from 'vscode';
import { GraceOSCore } from '../core/GraceOSCore';
import { IDEBridge, GenesisKey } from '../bridges/IDEBridge';

export interface GenesisNode {
    id: string;
    label: string;
    type: 'file' | 'key' | 'lineage';
    genesisKey?: GenesisKey;
    filePath?: string;
    children?: GenesisNode[];
}

export class GenesisKeyProvider implements vscode.TreeDataProvider<GenesisNode> {
    private core: GraceOSCore;
    private bridge: IDEBridge;
    private fileKeys: Map<string, GenesisKey[]> = new Map();
    private _onDidChangeTreeData = new vscode.EventEmitter<GenesisNode | undefined>();
    readonly onDidChangeTreeData = this._onDidChangeTreeData.event;
    private hoverProvider: vscode.Disposable | undefined;
    private decorationType: vscode.TextEditorDecorationType;

    constructor(core: GraceOSCore, bridge: IDEBridge) {
        this.core = core;
        this.bridge = bridge;

        // Create decoration for genesis-tracked lines
        this.decorationType = vscode.window.createTextEditorDecorationType({
            gutterIconPath: vscode.Uri.parse('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxNiIgaGVpZ2h0PSIxNiIgdmlld0JveD0iMCAwIDE2IDE2Ij48cGF0aCBmaWxsPSIjNEVDOUI1IiBkPSJNOCAxYTcgNyAwIDEgMCAwIDE0QTcgNyAwIDAgMCA4IDF6bTAgMTJhNSA1IDAgMSAxIDAtMTAgNSA1IDAgMCAxIDAgMTB6Ii8+PC9zdmc+'),
            gutterIconSize: '12px',
            overviewRulerColor: 'rgba(78, 201, 181, 0.7)',
            overviewRulerLane: vscode.OverviewRulerLane.Right,
        });

        // Listen for genesis updates
        this.core.on('genesisUpdate', () => this.refresh());

        // Register hover provider
        this.registerHoverProvider();
    }

    private registerHoverProvider(): void {
        this.hoverProvider = vscode.languages.registerHoverProvider({ scheme: 'file' }, {
            provideHover: async (document, position) => {
                const config = this.core.getConfig();
                if (!config.genesis.showLineage) return undefined;

                return this.provideGenesisHover(document, position);
            },
        });
    }

    private async provideGenesisHover(
        document: vscode.TextDocument,
        position: vscode.Position
    ): Promise<vscode.Hover | undefined> {
        const filePath = document.uri.fsPath;
        const lineNumber = position.line + 1;

        const response = await this.bridge.getCodeLineage(filePath, lineNumber);
        if (!response.success || !response.data || response.data.length === 0) {
            return undefined;
        }

        const key = response.data[0];
        const markdown = new vscode.MarkdownString();
        markdown.isTrusted = true;

        markdown.appendMarkdown('### Genesis Key\n\n');
        markdown.appendMarkdown(`**Key:** \`${key.id.substring(0, 12)}...\`\n\n`);
        markdown.appendMarkdown(`**Type:** ${key.type}\n\n`);
        markdown.appendMarkdown(`**Created:** ${new Date(key.timestamp).toLocaleString()}\n\n`);

        if (key.parentKey) {
            markdown.appendMarkdown(`**Parent:** \`${key.parentKey.substring(0, 12)}...\`\n\n`);
        }

        markdown.appendMarkdown(`[View Full Lineage](command:graceOS.genesis.viewLineage?${encodeURIComponent(JSON.stringify({ keyId: key.id }))})`);

        return new vscode.Hover(markdown);
    }

    // TreeDataProvider implementation

    getTreeItem(element: GenesisNode): vscode.TreeItem {
        const item = new vscode.TreeItem(element.label);

        if (element.type === 'file') {
            item.collapsibleState = vscode.TreeItemCollapsibleState.Collapsed;
            item.iconPath = new vscode.ThemeIcon('file-code');
            const count = this.fileKeys.get(element.filePath!)?.length || 0;
            item.description = `${count} keys`;
        } else if (element.type === 'key') {
            item.collapsibleState = vscode.TreeItemCollapsibleState.None;
            item.iconPath = new vscode.ThemeIcon('key');
            item.description = element.genesisKey?.type;
            item.tooltip = new vscode.MarkdownString(
                `**ID:** ${element.genesisKey?.id}\n\n` +
                `**Type:** ${element.genesisKey?.type}\n\n` +
                `**Created:** ${element.genesisKey?.timestamp}`
            );

            item.command = {
                command: 'graceOS.genesis.viewKey',
                title: 'View Genesis Key',
                arguments: [element.genesisKey],
            };
        }

        item.contextValue = element.type;
        return item;
    }

    async getChildren(element?: GenesisNode): Promise<GenesisNode[]> {
        if (!element) {
            // Root level - show files with genesis keys
            const workspaceFolders = vscode.workspace.workspaceFolders;
            if (!workspaceFolders) return [];

            // Get files with recent activity
            const files = new Set<string>();
            this.fileKeys.forEach((_, filePath) => files.add(filePath));

            // Also add currently open files
            vscode.window.visibleTextEditors.forEach(editor => {
                if (editor.document.uri.scheme === 'file') {
                    files.add(editor.document.uri.fsPath);
                }
            });

            const nodes: GenesisNode[] = [];
            for (const filePath of files) {
                const fileName = filePath.split('/').pop() || filePath;
                nodes.push({
                    id: filePath,
                    label: fileName,
                    type: 'file',
                    filePath,
                });
            }

            return nodes;
        }

        if (element.type === 'file' && element.filePath) {
            // Load keys for this file
            const response = await this.bridge.getCodeLineage(element.filePath);
            if (response.success && response.data) {
                this.fileKeys.set(element.filePath, response.data);

                return response.data.map(key => ({
                    id: key.id,
                    label: key.id.substring(0, 12) + '...',
                    type: 'key' as const,
                    genesisKey: key,
                }));
            }
        }

        return [];
    }

    // Public API

    async createGenesisKey(): Promise<void> {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('No active editor');
            return;
        }

        const selection = editor.selection;
        const filePath = editor.document.uri.fsPath;

        // Get key type
        const keyType = await vscode.window.showQuickPick(
            ['code_change', 'feature', 'bugfix', 'refactor', 'documentation', 'custom'],
            { placeHolder: 'Select genesis key type' }
        );

        if (!keyType) return;

        // Get optional description
        const description = await vscode.window.showInputBox({
            prompt: 'Enter a description for this genesis key (optional)',
            placeHolder: 'Description...',
        });

        await vscode.window.withProgress(
            {
                location: vscode.ProgressLocation.Notification,
                title: 'Creating genesis key...',
            },
            async () => {
                const entityId = `${filePath}:${selection.start.line + 1}-${selection.end.line + 1}`;
                const response = await this.bridge.createGenesisKey(keyType, entityId, {
                    filePath,
                    lineStart: selection.start.line + 1,
                    lineEnd: selection.end.line + 1,
                    description,
                    content: editor.document.getText(selection),
                });

                if (response.success && response.data) {
                    vscode.window.showInformationMessage(
                        `Genesis key created: ${response.data.id.substring(0, 12)}...`
                    );

                    // Update decorations
                    this.updateDecorations(editor);
                    this.refresh();

                    // Update ghost ledger if available
                    this.core.emit('genesisKeyCreated', {
                        key: response.data,
                        filePath,
                        lineStart: selection.start.line + 1,
                        lineEnd: selection.end.line + 1,
                    });
                } else {
                    vscode.window.showErrorMessage(`Failed to create genesis key: ${response.error}`);
                }
            }
        );
    }

    async viewLineage(): Promise<void> {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('No active editor');
            return;
        }

        const filePath = editor.document.uri.fsPath;
        const lineNumber = editor.selection.active.line + 1;

        await vscode.window.withProgress(
            {
                location: vscode.ProgressLocation.Notification,
                title: 'Loading code lineage...',
            },
            async () => {
                const response = await this.bridge.getCodeLineage(filePath, lineNumber);

                if (response.success && response.data && response.data.length > 0) {
                    this.showLineageTree(response.data);
                } else {
                    vscode.window.showInformationMessage('No lineage found for this line');
                }
            }
        );
    }

    private async showLineageTree(keys: GenesisKey[]): Promise<void> {
        // Build lineage tree
        const content = this.buildLineageContent(keys);

        const doc = await vscode.workspace.openTextDocument({
            content,
            language: 'markdown',
        });

        await vscode.window.showTextDocument(doc, { preview: true });
    }

    private buildLineageContent(keys: GenesisKey[]): string {
        const lines = ['# Code Lineage', ''];

        // Build parent-child relationships
        const keyMap = new Map<string, GenesisKey>();
        keys.forEach(key => keyMap.set(key.id, key));

        const rootKeys = keys.filter(k => !k.parentKey || !keyMap.has(k.parentKey));

        const renderKey = (key: GenesisKey, indent: number = 0): string[] => {
            const prefix = '  '.repeat(indent);
            const lines = [
                `${prefix}- **${key.type}** (\`${key.id.substring(0, 12)}...\`)`,
                `${prefix}  - Created: ${new Date(key.timestamp).toLocaleString()}`,
            ];

            if (key.metadata) {
                if (key.metadata.description) {
                    lines.push(`${prefix}  - Description: ${key.metadata.description}`);
                }
                if (key.metadata.filePath) {
                    lines.push(`${prefix}  - File: ${key.metadata.filePath}`);
                }
            }

            // Find children
            const children = keys.filter(k => k.parentKey === key.id);
            children.forEach(child => {
                lines.push('');
                lines.push(...renderKey(child, indent + 1));
            });

            return lines;
        };

        rootKeys.forEach(key => {
            lines.push(...renderKey(key));
            lines.push('');
        });

        return lines.join('\n');
    }

    async viewGenesisKey(key: GenesisKey): Promise<void> {
        const content = [
            `# Genesis Key Details`,
            '',
            `**ID:** \`${key.id}\``,
            '',
            `**Type:** ${key.type}`,
            '',
            `**Entity ID:** ${key.entityId}`,
            '',
            `**Created:** ${new Date(key.timestamp).toLocaleString()}`,
            '',
            `**Hash:** \`${key.hash}\``,
            '',
            key.parentKey ? `**Parent Key:** \`${key.parentKey}\`` : '',
            '',
            key.metadata ? `## Metadata\n\`\`\`json\n${JSON.stringify(key.metadata, null, 2)}\n\`\`\`` : '',
        ].filter(Boolean).join('\n');

        const doc = await vscode.workspace.openTextDocument({
            content,
            language: 'markdown',
        });

        await vscode.window.showTextDocument(doc, { preview: true });
    }

    private updateDecorations(editor: vscode.TextEditor): void {
        const filePath = editor.document.uri.fsPath;
        const keys = this.fileKeys.get(filePath) || [];

        const decorations: vscode.DecorationOptions[] = [];

        keys.forEach(key => {
            if (key.metadata?.lineStart && key.metadata?.lineEnd) {
                const startLine = key.metadata.lineStart - 1;
                const endLine = key.metadata.lineEnd - 1;

                for (let line = startLine; line <= endLine; line++) {
                    if (line < editor.document.lineCount) {
                        decorations.push({
                            range: new vscode.Range(line, 0, line, 0),
                            hoverMessage: `Genesis Key: ${key.id.substring(0, 12)}...`,
                        });
                    }
                }
            }
        });

        editor.setDecorations(this.decorationType, decorations);
    }

    refresh(): void {
        this._onDidChangeTreeData.fire(undefined);

        // Update decorations for active editor
        const editor = vscode.window.activeTextEditor;
        if (editor) {
            this.updateDecorations(editor);
        }
    }

    dispose(): void {
        this.hoverProvider?.dispose();
        this.decorationType.dispose();
        this._onDidChangeTreeData.dispose();
    }
}
