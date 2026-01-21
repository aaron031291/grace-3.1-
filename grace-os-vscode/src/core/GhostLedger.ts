/**
 * Ghost Ledger
 *
 * Line-by-line code tracking system with genesis key integration.
 * Tracks every code change, maintains provenance, and provides
 * visual annotations in the editor.
 */

import * as vscode from 'vscode';
import { GraceOSCore } from './GraceOSCore';
import { v4 as uuidv4 } from 'uuid';

export interface LineChange {
    id: string;
    lineNumber: number;
    previousContent: string;
    newContent: string;
    changeType: 'insert' | 'delete' | 'modify';
    timestamp: string;
    genesisKey?: string;
    userId?: string;
    reason?: string;
}

export interface FileSnapshot {
    filePath: string;
    content: string;
    lineCount: number;
    timestamp: string;
    hash: string;
}

export interface LineMetadata {
    lineNumber: number;
    genesisKey?: string;
    lastModified: string;
    changeCount: number;
    contributors: string[];
    annotations: LineAnnotation[];
}

export interface LineAnnotation {
    id: string;
    type: 'change' | 'genesis' | 'learning' | 'warning';
    message: string;
    timestamp: string;
    severity?: 'info' | 'warning' | 'error';
}

export class GhostLedger {
    private core: GraceOSCore;
    private context: vscode.ExtensionContext;
    private changeHistory: Map<string, LineChange[]> = new Map();
    private fileSnapshots: Map<string, FileSnapshot> = new Map();
    private lineMetadata: Map<string, Map<number, LineMetadata>> = new Map();
    private decorationType: vscode.TextEditorDecorationType;
    private genesisDecorationType: vscode.TextEditorDecorationType;
    private changeDecorationType: vscode.TextEditorDecorationType;
    private documentListener: vscode.Disposable | undefined;
    private saveListener: vscode.Disposable | undefined;
    private activeEditorListener: vscode.Disposable | undefined;
    private hoverProvider: vscode.Disposable | undefined;
    private isEnabled: boolean = false;

    constructor(core: GraceOSCore, context: vscode.ExtensionContext) {
        this.core = core;
        this.context = context;

        // Create decoration types for visual annotations
        this.decorationType = vscode.window.createTextEditorDecorationType({
            after: {
                margin: '0 0 0 1em',
                color: new vscode.ThemeColor('editorCodeLens.foreground'),
            },
            isWholeLine: true,
        });

        this.genesisDecorationType = vscode.window.createTextEditorDecorationType({
            backgroundColor: new vscode.ThemeColor('graceOS.genesisKeyHighlight'),
            overviewRulerColor: new vscode.ThemeColor('editorOverviewRuler.infoForeground'),
            overviewRulerLane: vscode.OverviewRulerLane.Right,
            isWholeLine: true,
        });

        this.changeDecorationType = vscode.window.createTextEditorDecorationType({
            backgroundColor: new vscode.ThemeColor('graceOS.ghostLedgerChange'),
            borderRadius: '2px',
            isWholeLine: true,
        });
    }

    async initialize(): Promise<void> {
        this.core.log('Initializing Ghost Ledger...');

        // Load configuration
        const config = this.core.getConfig();
        this.isEnabled = config.ghostLedger.enabled;

        if (!this.isEnabled) {
            this.core.log('Ghost Ledger is disabled');
            return;
        }

        // Restore persisted data
        await this.restoreState();

        // Set up listeners
        this.setupListeners();

        // Register hover provider for line metadata
        this.registerHoverProvider();

        // Initialize current editor
        if (vscode.window.activeTextEditor) {
            await this.snapshotFile(vscode.window.activeTextEditor.document);
            this.updateDecorations(vscode.window.activeTextEditor);
        }

        this.core.log('Ghost Ledger initialized');
        this.core.enableFeature('ghostLedger');
    }

    private async restoreState(): Promise<void> {
        const storedHistory = await this.core.getWorkspaceData<Record<string, LineChange[]>>('ghostLedger.history');
        if (storedHistory) {
            this.changeHistory = new Map(Object.entries(storedHistory));
        }

        const storedMetadata = await this.core.getWorkspaceData<Record<string, Record<number, LineMetadata>>>('ghostLedger.metadata');
        if (storedMetadata) {
            for (const [filePath, metadata] of Object.entries(storedMetadata)) {
                this.lineMetadata.set(filePath, new Map(Object.entries(metadata).map(([k, v]) => [parseInt(k), v])));
            }
        }
    }

    private async persistState(): Promise<void> {
        const historyObj: Record<string, LineChange[]> = {};
        this.changeHistory.forEach((value, key) => {
            historyObj[key] = value.slice(-100); // Keep last 100 changes per file
        });

        const metadataObj: Record<string, Record<number, LineMetadata>> = {};
        this.lineMetadata.forEach((value, key) => {
            const lineObj: Record<number, LineMetadata> = {};
            value.forEach((meta, lineNum) => {
                lineObj[lineNum] = meta;
            });
            metadataObj[key] = lineObj;
        });

        await this.core.setWorkspaceData('ghostLedger.history', historyObj);
        await this.core.setWorkspaceData('ghostLedger.metadata', metadataObj);
    }

    private setupListeners(): void {
        // Listen for document changes
        this.documentListener = vscode.workspace.onDidChangeTextDocument(event => {
            if (event.document.uri.scheme === 'file') {
                this.handleDocumentChange(event);
            }
        });

        // Listen for document saves
        this.saveListener = vscode.workspace.onDidSaveTextDocument(document => {
            if (document.uri.scheme === 'file') {
                this.handleDocumentSave(document);
            }
        });

        // Listen for active editor changes
        this.activeEditorListener = vscode.window.onDidChangeActiveTextEditor(editor => {
            if (editor && editor.document.uri.scheme === 'file') {
                this.snapshotFile(editor.document);
                this.updateDecorations(editor);
            }
        });
    }

    private registerHoverProvider(): void {
        this.hoverProvider = vscode.languages.registerHoverProvider({ scheme: 'file' }, {
            provideHover: (document, position) => {
                return this.provideLineHover(document, position);
            },
        });
    }

    private provideLineHover(document: vscode.TextDocument, position: vscode.Position): vscode.Hover | undefined {
        const config = this.core.getConfig();
        if (!config.genesis.showLineage) {
            return undefined;
        }

        const filePath = document.uri.fsPath;
        const lineNumber = position.line + 1;
        const fileMetadata = this.lineMetadata.get(filePath);

        if (!fileMetadata) {
            return undefined;
        }

        const lineMeta = fileMetadata.get(lineNumber);
        if (!lineMeta) {
            return undefined;
        }

        const markdown = new vscode.MarkdownString();
        markdown.isTrusted = true;

        markdown.appendMarkdown('### Ghost Ledger\n\n');

        if (lineMeta.genesisKey) {
            markdown.appendMarkdown(`**Genesis Key:** \`${lineMeta.genesisKey.substring(0, 8)}...\`\n\n`);
        }

        markdown.appendMarkdown(`**Last Modified:** ${new Date(lineMeta.lastModified).toLocaleString()}\n\n`);
        markdown.appendMarkdown(`**Change Count:** ${lineMeta.changeCount}\n\n`);

        if (lineMeta.contributors.length > 0) {
            markdown.appendMarkdown(`**Contributors:** ${lineMeta.contributors.join(', ')}\n\n`);
        }

        if (lineMeta.annotations.length > 0) {
            markdown.appendMarkdown('**Annotations:**\n');
            for (const annotation of lineMeta.annotations.slice(-3)) {
                const icon = annotation.type === 'warning' ? '$(warning)' : annotation.type === 'genesis' ? '$(key)' : '$(info)';
                markdown.appendMarkdown(`- ${icon} ${annotation.message}\n`);
            }
        }

        // Add command to view full history
        markdown.appendMarkdown(`\n[View Full History](command:graceOS.ghostLedger.viewChanges?${encodeURIComponent(JSON.stringify({ filePath, lineNumber }))})`);

        return new vscode.Hover(markdown);
    }

    private async handleDocumentChange(event: vscode.TextDocumentChangeEvent): Promise<void> {
        if (!this.isEnabled) return;

        const filePath = event.document.uri.fsPath;
        const previousSnapshot = this.fileSnapshots.get(filePath);

        for (const change of event.contentChanges) {
            const startLine = change.range.start.line + 1;
            const endLine = change.range.end.line + 1;
            const newLines = change.text.split('\n').length;

            const lineChange: LineChange = {
                id: uuidv4(),
                lineNumber: startLine,
                previousContent: previousSnapshot?.content.split('\n')[startLine - 1] || '',
                newContent: change.text,
                changeType: this.determineChangeType(change, previousSnapshot),
                timestamp: new Date().toISOString(),
                userId: this.core.getSession().userId,
            };

            this.recordChange(filePath, lineChange);
            this.updateLineMetadata(filePath, startLine, lineChange);
        }

        // Update decorations
        const editor = vscode.window.activeTextEditor;
        if (editor && editor.document.uri.fsPath === filePath) {
            this.updateDecorations(editor);
        }
    }

    private determineChangeType(change: vscode.TextDocumentContentChangeEvent, snapshot?: FileSnapshot): 'insert' | 'delete' | 'modify' {
        if (change.rangeLength === 0 && change.text.length > 0) {
            return 'insert';
        } else if (change.rangeLength > 0 && change.text.length === 0) {
            return 'delete';
        }
        return 'modify';
    }

    private recordChange(filePath: string, change: LineChange): void {
        if (!this.changeHistory.has(filePath)) {
            this.changeHistory.set(filePath, []);
        }

        const history = this.changeHistory.get(filePath)!;
        history.push(change);

        // Limit history size
        if (history.length > 1000) {
            history.shift();
        }
    }

    private updateLineMetadata(filePath: string, lineNumber: number, change: LineChange): void {
        if (!this.lineMetadata.has(filePath)) {
            this.lineMetadata.set(filePath, new Map());
        }

        const fileMetadata = this.lineMetadata.get(filePath)!;
        let lineMeta = fileMetadata.get(lineNumber);

        if (!lineMeta) {
            lineMeta = {
                lineNumber,
                lastModified: change.timestamp,
                changeCount: 0,
                contributors: [],
                annotations: [],
            };
        }

        lineMeta.changeCount++;
        lineMeta.lastModified = change.timestamp;

        if (change.userId && !lineMeta.contributors.includes(change.userId)) {
            lineMeta.contributors.push(change.userId);
        }

        // Add annotation for significant changes
        if (change.changeType === 'insert' && change.newContent.length > 50) {
            lineMeta.annotations.push({
                id: uuidv4(),
                type: 'change',
                message: 'Significant content added',
                timestamp: change.timestamp,
            });
        }

        fileMetadata.set(lineNumber, lineMeta);
    }

    private handleDocumentSave(document: vscode.TextDocument): void {
        this.snapshotFile(document);
        this.persistState();

        // Emit event for Genesis integration
        this.core.emit('fileSaved', {
            filePath: document.uri.fsPath,
            changeHistory: this.changeHistory.get(document.uri.fsPath) || [],
        });
    }

    private async snapshotFile(document: vscode.TextDocument): Promise<void> {
        const content = document.getText();
        const snapshot: FileSnapshot = {
            filePath: document.uri.fsPath,
            content,
            lineCount: document.lineCount,
            timestamp: new Date().toISOString(),
            hash: this.simpleHash(content),
        };

        this.fileSnapshots.set(document.uri.fsPath, snapshot);
    }

    private simpleHash(str: string): string {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash;
        }
        return hash.toString(16);
    }

    private updateDecorations(editor: vscode.TextEditor): void {
        const config = this.core.getConfig();
        if (!config.ghostLedger.showInlineAnnotations) {
            editor.setDecorations(this.decorationType, []);
            editor.setDecorations(this.changeDecorationType, []);
            editor.setDecorations(this.genesisDecorationType, []);
            return;
        }

        const filePath = editor.document.uri.fsPath;
        const fileMetadata = this.lineMetadata.get(filePath);

        if (!fileMetadata) {
            return;
        }

        const changeDecorations: vscode.DecorationOptions[] = [];
        const genesisDecorations: vscode.DecorationOptions[] = [];
        const inlineDecorations: vscode.DecorationOptions[] = [];

        const now = Date.now();
        const recentThreshold = 60000; // 1 minute

        fileMetadata.forEach((meta, lineNumber) => {
            const line = lineNumber - 1;
            if (line >= editor.document.lineCount) return;

            const range = new vscode.Range(line, 0, line, editor.document.lineAt(line).text.length);

            // Highlight recently changed lines
            const changeAge = now - new Date(meta.lastModified).getTime();
            if (changeAge < recentThreshold) {
                changeDecorations.push({ range });
            }

            // Highlight lines with genesis keys
            if (meta.genesisKey) {
                genesisDecorations.push({ range });
            }

            // Add inline annotations
            if (meta.changeCount > 5) {
                inlineDecorations.push({
                    range,
                    renderOptions: {
                        after: {
                            contentText: ` [${meta.changeCount} changes]`,
                        },
                    },
                });
            }
        });

        editor.setDecorations(this.changeDecorationType, changeDecorations);
        editor.setDecorations(this.genesisDecorationType, genesisDecorations);
        editor.setDecorations(this.decorationType, inlineDecorations);
    }

    // Public API

    toggle(): void {
        this.isEnabled = !this.isEnabled;

        if (this.isEnabled) {
            this.setupListeners();
            this.registerHoverProvider();
            this.core.enableFeature('ghostLedger');
            vscode.window.showInformationMessage('Ghost Ledger enabled');
        } else {
            this.documentListener?.dispose();
            this.saveListener?.dispose();
            this.activeEditorListener?.dispose();
            this.hoverProvider?.dispose();
            this.core.disableFeature('ghostLedger');

            // Clear decorations
            const editor = vscode.window.activeTextEditor;
            if (editor) {
                editor.setDecorations(this.decorationType, []);
                editor.setDecorations(this.changeDecorationType, []);
                editor.setDecorations(this.genesisDecorationType, []);
            }

            vscode.window.showInformationMessage('Ghost Ledger disabled');
        }
    }

    getChangeHistory(filePath: string): LineChange[] {
        return this.changeHistory.get(filePath) || [];
    }

    getLineMetadata(filePath: string, lineNumber: number): LineMetadata | undefined {
        return this.lineMetadata.get(filePath)?.get(lineNumber);
    }

    getFileMetadata(filePath: string): Map<number, LineMetadata> | undefined {
        return this.lineMetadata.get(filePath);
    }

    setGenesisKey(filePath: string, lineNumber: number, genesisKey: string): void {
        if (!this.lineMetadata.has(filePath)) {
            this.lineMetadata.set(filePath, new Map());
        }

        const fileMetadata = this.lineMetadata.get(filePath)!;
        let lineMeta = fileMetadata.get(lineNumber);

        if (!lineMeta) {
            lineMeta = {
                lineNumber,
                lastModified: new Date().toISOString(),
                changeCount: 0,
                contributors: [],
                annotations: [],
            };
        }

        lineMeta.genesisKey = genesisKey;
        lineMeta.annotations.push({
            id: uuidv4(),
            type: 'genesis',
            message: `Genesis key assigned: ${genesisKey.substring(0, 8)}...`,
            timestamp: new Date().toISOString(),
        });

        fileMetadata.set(lineNumber, lineMeta);
        this.persistState();

        // Update decorations
        const editor = vscode.window.activeTextEditor;
        if (editor && editor.document.uri.fsPath === filePath) {
            this.updateDecorations(editor);
        }
    }

    addAnnotation(filePath: string, lineNumber: number, annotation: Omit<LineAnnotation, 'id'>): void {
        if (!this.lineMetadata.has(filePath)) {
            this.lineMetadata.set(filePath, new Map());
        }

        const fileMetadata = this.lineMetadata.get(filePath)!;
        let lineMeta = fileMetadata.get(lineNumber);

        if (!lineMeta) {
            lineMeta = {
                lineNumber,
                lastModified: new Date().toISOString(),
                changeCount: 0,
                contributors: [],
                annotations: [],
            };
        }

        lineMeta.annotations.push({
            ...annotation,
            id: uuidv4(),
        });

        fileMetadata.set(lineNumber, lineMeta);
    }

    async viewLineChanges(filePath: string, lineNumber: number): Promise<void> {
        const history = this.changeHistory.get(filePath) || [];
        const lineChanges = history.filter(c => c.lineNumber === lineNumber);

        if (lineChanges.length === 0) {
            vscode.window.showInformationMessage('No change history for this line');
            return;
        }

        // Create a virtual document showing the history
        const content = lineChanges.map(change => {
            return [
                `=== ${new Date(change.timestamp).toLocaleString()} ===`,
                `Type: ${change.changeType}`,
                `Previous: ${change.previousContent || '(none)'}`,
                `New: ${change.newContent || '(deleted)'}`,
                change.genesisKey ? `Genesis Key: ${change.genesisKey}` : '',
                '',
            ].filter(Boolean).join('\n');
        }).join('\n');

        const doc = await vscode.workspace.openTextDocument({
            content,
            language: 'markdown',
        });

        await vscode.window.showTextDocument(doc, { preview: true });
    }

    dispose(): void {
        this.documentListener?.dispose();
        this.saveListener?.dispose();
        this.activeEditorListener?.dispose();
        this.hoverProvider?.dispose();
        this.decorationType.dispose();
        this.genesisDecorationType.dispose();
        this.changeDecorationType.dispose();
    }
}
