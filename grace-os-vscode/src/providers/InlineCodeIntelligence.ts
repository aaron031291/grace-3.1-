/**
 * Inline Code Intelligence
 *
 * Provides intelligent code suggestions, completions, and insights
 * directly in the editor using Grace's cognitive capabilities.
 */

import * as vscode from 'vscode';
import { GraceOSCore } from '../core/GraceOSCore';
import { CognitiveIDEProvider } from './CognitiveIDEProvider';

export interface CodeInsight {
    range: vscode.Range;
    message: string;
    type: 'suggestion' | 'warning' | 'info' | 'pattern';
    severity: vscode.DiagnosticSeverity;
    actions?: vscode.CodeAction[];
}

export class InlineCodeIntelligence {
    private core: GraceOSCore;
    private cognitiveProvider: CognitiveIDEProvider;
    private disposables: vscode.Disposable[] = [];
    private insightDecoration: vscode.TextEditorDecorationType;
    private warningDecoration: vscode.TextEditorDecorationType;
    private inlayHintsProvider: vscode.Disposable | undefined;
    private debounceTimer: NodeJS.Timeout | undefined;

    constructor(core: GraceOSCore, cognitiveProvider: CognitiveIDEProvider) {
        this.core = core;
        this.cognitiveProvider = cognitiveProvider;

        // Create decoration types
        this.insightDecoration = vscode.window.createTextEditorDecorationType({
            after: {
                margin: '0 0 0 2em',
                color: new vscode.ThemeColor('editorCodeLens.foreground'),
                fontStyle: 'italic',
            },
        });

        this.warningDecoration = vscode.window.createTextEditorDecorationType({
            backgroundColor: new vscode.ThemeColor('graceOS.diagnosticWarning'),
            borderRadius: '2px',
        });
    }

    async initialize(): Promise<void> {
        this.core.log('Initializing Inline Code Intelligence...');

        const config = this.core.getConfig();

        if (config.cognitive.inlineSuggestions) {
            this.setupInlineSuggestions();
        }

        if (config.cognitive.autoAnalyze) {
            this.setupAutoAnalysis();
        }

        // Register inlay hints provider
        this.registerInlayHints();

        this.core.enableFeature('inlineIntelligence');
        this.core.log('Inline Code Intelligence initialized');
    }

    private setupInlineSuggestions(): void {
        // Listen for cursor position changes
        const cursorChangeListener = vscode.window.onDidChangeTextEditorSelection(
            event => this.handleCursorChange(event)
        );
        this.disposables.push(cursorChangeListener);
    }

    private setupAutoAnalysis(): void {
        // Listen for document saves
        const saveListener = vscode.workspace.onDidSaveTextDocument(
            document => this.handleDocumentSave(document)
        );
        this.disposables.push(saveListener);

        // Listen for document changes (debounced)
        const changeListener = vscode.workspace.onDidChangeTextDocument(
            event => this.handleDocumentChange(event)
        );
        this.disposables.push(changeListener);
    }

    private registerInlayHints(): void {
        this.inlayHintsProvider = vscode.languages.registerInlayHintsProvider(
            { scheme: 'file' },
            {
                provideInlayHints: (document, range) =>
                    this.provideInlayHints(document, range),
            }
        );
        this.disposables.push(this.inlayHintsProvider);
    }

    private async provideInlayHints(
        document: vscode.TextDocument,
        range: vscode.Range
    ): Promise<vscode.InlayHint[]> {
        const hints: vscode.InlayHint[] = [];
        const config = this.core.getConfig();

        if (!config.cognitive.inlineSuggestions) {
            return hints;
        }

        // Get analysis for this file if available
        const analysis = this.cognitiveProvider.getAnalysisForFile(document.uri.fsPath);

        if (analysis && analysis.analysis.patterns.length > 0) {
            // Add pattern hints
            for (const pattern of analysis.analysis.patterns.slice(0, 3)) {
                const hint = new vscode.InlayHint(
                    new vscode.Position(range.start.line, 0),
                    `$(lightbulb) ${pattern}`,
                    vscode.InlayHintKind.Type
                );
                hint.paddingLeft = true;
                hint.tooltip = new vscode.MarkdownString(`**Grace Pattern:** ${pattern}`);
                hints.push(hint);
            }
        }

        return hints;
    }

    private handleCursorChange(event: vscode.TextEditorSelectionChangeEvent): void {
        // Clear debounce timer
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }

        // Debounce to avoid excessive API calls
        this.debounceTimer = setTimeout(() => {
            this.analyzeAtCursor(event.textEditor);
        }, 1000);
    }

    private async analyzeAtCursor(editor: vscode.TextEditor): Promise<void> {
        const config = this.core.getConfig();
        if (!config.cognitive.inlineSuggestions) return;

        const position = editor.selection.active;
        const line = editor.document.lineAt(position.line);

        // Skip empty lines or very short lines
        if (line.text.trim().length < 5) return;

        // Get surrounding context
        const startLine = Math.max(0, position.line - 5);
        const endLine = Math.min(editor.document.lineCount - 1, position.line + 5);
        const contextRange = new vscode.Range(startLine, 0, endLine, editor.document.lineAt(endLine).text.length);
        const context = editor.document.getText(contextRange);

        // Quick pattern check (local, no API call)
        const insights = this.detectLocalPatterns(context, position.line - startLine);

        if (insights.length > 0) {
            this.showInlineInsights(editor, insights, position.line);
        }
    }

    private detectLocalPatterns(code: string, focusLine: number): string[] {
        const insights: string[] = [];
        const lines = code.split('\n');
        const currentLine = lines[focusLine] || '';

        // Detect common patterns
        if (currentLine.includes('TODO') || currentLine.includes('FIXME')) {
            insights.push('Task marker detected');
        }

        if (currentLine.includes('console.log') || currentLine.includes('print(')) {
            insights.push('Debug statement - consider removing');
        }

        if (currentLine.match(/catch\s*\(\s*\w*\s*\)\s*\{\s*\}/)) {
            insights.push('Empty catch block - consider handling error');
        }

        if (currentLine.match(/\bvar\b/) && code.includes('const') || code.includes('let')) {
            insights.push('Consider using const/let instead of var');
        }

        if (currentLine.length > 120) {
            insights.push('Line exceeds 120 characters');
        }

        // Detect nested callbacks
        const nestingLevel = (currentLine.match(/\{/g) || []).length;
        if (nestingLevel >= 3) {
            insights.push('Deep nesting detected - consider refactoring');
        }

        // Detect magic numbers
        if (currentLine.match(/[^0-9a-zA-Z_](0|[1-9][0-9]{2,})[^0-9a-zA-Z_]/)) {
            insights.push('Magic number detected - consider using named constant');
        }

        return insights;
    }

    private showInlineInsights(
        editor: vscode.TextEditor,
        insights: string[],
        line: number
    ): void {
        const decorations: vscode.DecorationOptions[] = insights.map((insight, index) => ({
            range: new vscode.Range(line + index, 0, line + index, 0),
            renderOptions: {
                after: {
                    contentText: ` $(lightbulb) ${insight}`,
                },
            },
        }));

        editor.setDecorations(this.insightDecoration, decorations);

        // Clear after 5 seconds
        setTimeout(() => {
            editor.setDecorations(this.insightDecoration, []);
        }, 5000);
    }

    private async handleDocumentSave(document: vscode.TextDocument): Promise<void> {
        const config = this.core.getConfig();
        if (!config.cognitive.autoAnalyze) return;

        // Only analyze code files
        const codeLanguages = ['javascript', 'typescript', 'python', 'java', 'c', 'cpp', 'go', 'rust'];
        if (!codeLanguages.includes(document.languageId)) return;

        // Trigger background analysis
        this.core.emit('documentAnalysisRequested', {
            filePath: document.uri.fsPath,
            language: document.languageId,
        });
    }

    private handleDocumentChange(event: vscode.TextDocumentChangeEvent): void {
        // Clear decorations on significant changes
        if (event.contentChanges.length > 0) {
            const editor = vscode.window.activeTextEditor;
            if (editor && editor.document === event.document) {
                editor.setDecorations(this.insightDecoration, []);
            }
        }
    }

    // Public API for showing insights programmatically

    showInsight(editor: vscode.TextEditor, insight: CodeInsight): void {
        const decoration: vscode.DecorationOptions = {
            range: insight.range,
            hoverMessage: new vscode.MarkdownString(`**${insight.type}:** ${insight.message}`),
        };

        if (insight.type === 'warning') {
            editor.setDecorations(this.warningDecoration, [decoration]);
        } else {
            const inlineDecoration: vscode.DecorationOptions = {
                range: insight.range,
                renderOptions: {
                    after: {
                        contentText: ` // ${insight.message}`,
                    },
                },
            };
            editor.setDecorations(this.insightDecoration, [inlineDecoration]);
        }

        // Also add to VS Code diagnostics
        const diagnosticCollection = this.core.getDiagnosticCollection();
        const diagnostics = diagnosticCollection.get(editor.document.uri) || [];

        diagnostics.push(new vscode.Diagnostic(
            insight.range,
            `Grace: ${insight.message}`,
            insight.severity
        ));

        diagnosticCollection.set(editor.document.uri, diagnostics);
    }

    clearInsights(editor: vscode.TextEditor): void {
        editor.setDecorations(this.insightDecoration, []);
        editor.setDecorations(this.warningDecoration, []);

        const diagnosticCollection = this.core.getDiagnosticCollection();
        diagnosticCollection.delete(editor.document.uri);
    }

    dispose(): void {
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }

        this.insightDecoration.dispose();
        this.warningDecoration.dispose();

        this.disposables.forEach(d => d.dispose());
    }
}
