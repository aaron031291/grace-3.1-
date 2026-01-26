/**
 * Cognitive IDE Provider
 *
 * Brings Grace's cognitive layer into the editor.
 * Provides code analysis, explanations, and intelligent suggestions.
 */

import * as vscode from 'vscode';
import { GraceOSCore } from '../core/GraceOSCore';
import { IDEBridge, CognitiveAnalysis } from '../bridges/IDEBridge';

export interface AnalysisResult {
    code: string;
    language: string;
    analysis: CognitiveAnalysis;
    timestamp: Date;
}

export class CognitiveIDEProvider {
    private core: GraceOSCore;
    private bridge: IDEBridge;
    private analysisCache: Map<string, AnalysisResult> = new Map();
    private analysisOutputChannel: vscode.OutputChannel;
    private codeActionProvider: vscode.Disposable | undefined;
    private completionProvider: vscode.Disposable | undefined;

    constructor(core: GraceOSCore, bridge: IDEBridge) {
        this.core = core;
        this.bridge = bridge;
        this.analysisOutputChannel = vscode.window.createOutputChannel('Grace Cognitive');
    }

    async initialize(): Promise<void> {
        this.core.log('Initializing Cognitive IDE Provider...');

        // Register code action provider for suggestions
        this.codeActionProvider = vscode.languages.registerCodeActionsProvider(
            { scheme: 'file' },
            {
                provideCodeActions: (document, range) => this.provideCodeActions(document, range),
            },
            {
                providedCodeActionKinds: [
                    vscode.CodeActionKind.QuickFix,
                    vscode.CodeActionKind.Refactor,
                ],
            }
        );

        // Register completion provider for cognitive completions
        this.completionProvider = vscode.languages.registerCompletionItemProvider(
            { scheme: 'file' },
            {
                provideCompletionItems: (document, position) =>
                    this.provideCognitiveCompletions(document, position),
            },
            '.' // Trigger on dot
        );

        this.core.enableFeature('cognitiveIDE');
        this.core.log('Cognitive IDE Provider initialized');
    }

    private async provideCodeActions(
        document: vscode.TextDocument,
        range: vscode.Range
    ): Promise<vscode.CodeAction[]> {
        const actions: vscode.CodeAction[] = [];

        // Only provide actions for selections
        if (range.isEmpty) {
            return actions;
        }

        const selectedText = document.getText(range);
        if (selectedText.trim().length < 10) {
            return actions;
        }

        // Add analyze action
        const analyzeAction = new vscode.CodeAction(
            'Grace: Analyze Selection',
            vscode.CodeActionKind.QuickFix
        );
        analyzeAction.command = {
            command: 'graceOS.cognitive.analyze',
            title: 'Analyze Selection',
        };
        actions.push(analyzeAction);

        // Add explain action
        const explainAction = new vscode.CodeAction(
            'Grace: Explain Code',
            vscode.CodeActionKind.QuickFix
        );
        explainAction.command = {
            command: 'graceOS.cognitive.explain',
            title: 'Explain Code',
        };
        actions.push(explainAction);

        // Add refactor action
        const refactorAction = new vscode.CodeAction(
            'Grace: Suggest Refactoring',
            vscode.CodeActionKind.Refactor
        );
        refactorAction.command = {
            command: 'graceOS.cognitive.refactor',
            title: 'Suggest Refactoring',
        };
        actions.push(refactorAction);

        return actions;
    }

    private async provideCognitiveCompletions(
        document: vscode.TextDocument,
        position: vscode.Position
    ): Promise<vscode.CompletionItem[]> {
        const config = this.core.getConfig();
        if (!config.cognitive.inlineSuggestions) {
            return [];
        }

        // Get context around cursor
        const linePrefix = document.lineAt(position).text.substring(0, position.character);
        const contextRange = new vscode.Range(
            Math.max(0, position.line - 10),
            0,
            position.line,
            position.character
        );
        const context = document.getText(contextRange);

        // Check cache for recent analysis
        const cacheKey = `${document.uri.fsPath}:${context.length}`;
        const cached = this.analysisCache.get(cacheKey);

        if (cached && Date.now() - cached.timestamp.getTime() < 30000) {
            return this.createCompletionItems(cached.analysis.suggestions);
        }

        return [];
    }

    private createCompletionItems(suggestions: string[]): vscode.CompletionItem[] {
        return suggestions.map((suggestion, index) => {
            const item = new vscode.CompletionItem(
                suggestion,
                vscode.CompletionItemKind.Snippet
            );
            item.detail = 'Grace Cognitive Suggestion';
            item.sortText = `0${index}`; // Prioritize Grace suggestions
            item.insertText = new vscode.SnippetString(suggestion);
            return item;
        });
    }

    // Public API for commands

    async analyzeSelection(): Promise<void> {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('No active editor');
            return;
        }

        const selection = editor.selection;
        if (selection.isEmpty) {
            vscode.window.showWarningMessage('Please select some code to analyze');
            return;
        }

        const code = editor.document.getText(selection);
        const language = editor.document.languageId;

        await vscode.window.withProgress(
            {
                location: vscode.ProgressLocation.Notification,
                title: 'Grace: Analyzing code...',
                cancellable: false,
            },
            async () => {
                const response = await this.bridge.analyzeCode(code, language, {
                    filePath: editor.document.uri.fsPath,
                    lineStart: selection.start.line,
                    lineEnd: selection.end.line,
                });

                if (response.success && response.data) {
                    this.showAnalysisResult(response.data, code, language);

                    // Cache the result
                    const cacheKey = `${editor.document.uri.fsPath}:${code.length}`;
                    this.analysisCache.set(cacheKey, {
                        code,
                        language,
                        analysis: response.data,
                        timestamp: new Date(),
                    });
                } else {
                    vscode.window.showErrorMessage(`Analysis failed: ${response.error}`);
                }
            }
        );
    }

    async explainCode(): Promise<void> {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('No active editor');
            return;
        }

        const selection = editor.selection;
        const code = selection.isEmpty
            ? editor.document.getText()
            : editor.document.getText(selection);
        const language = editor.document.languageId;

        await vscode.window.withProgress(
            {
                location: vscode.ProgressLocation.Notification,
                title: 'Grace: Generating explanation...',
                cancellable: false,
            },
            async () => {
                const response = await this.bridge.explainCode(code, language);

                if (response.success && response.data) {
                    this.showExplanation(response.data);
                } else {
                    vscode.window.showErrorMessage(`Explanation failed: ${response.error}`);
                }
            }
        );
    }

    async suggestRefactoring(): Promise<void> {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('No active editor');
            return;
        }

        const selection = editor.selection;
        if (selection.isEmpty) {
            vscode.window.showWarningMessage('Please select code to refactor');
            return;
        }

        const code = editor.document.getText(selection);
        const language = editor.document.languageId;

        await vscode.window.withProgress(
            {
                location: vscode.ProgressLocation.Notification,
                title: 'Grace: Analyzing for refactoring...',
                cancellable: false,
            },
            async () => {
                const response = await this.bridge.suggestRefactoring(code, language);

                if (response.success && response.data) {
                    this.showRefactoringSuggestions(response.data, editor, selection);
                } else {
                    vscode.window.showErrorMessage(`Refactoring analysis failed: ${response.error}`);
                }
            }
        );
    }

    private showAnalysisResult(analysis: CognitiveAnalysis, code: string, language: string): void {
        this.analysisOutputChannel.clear();
        this.analysisOutputChannel.appendLine('=== Grace Cognitive Analysis ===\n');
        this.analysisOutputChannel.appendLine(`Language: ${language}`);
        this.analysisOutputChannel.appendLine(`Confidence: ${(analysis.confidence * 100).toFixed(1)}%\n`);

        this.analysisOutputChannel.appendLine('--- Analysis ---');
        this.analysisOutputChannel.appendLine(analysis.analysis);
        this.analysisOutputChannel.appendLine('');

        if (analysis.patterns.length > 0) {
            this.analysisOutputChannel.appendLine('--- Detected Patterns ---');
            analysis.patterns.forEach(pattern => {
                this.analysisOutputChannel.appendLine(`  - ${pattern}`);
            });
            this.analysisOutputChannel.appendLine('');
        }

        if (analysis.suggestions.length > 0) {
            this.analysisOutputChannel.appendLine('--- Suggestions ---');
            analysis.suggestions.forEach(suggestion => {
                this.analysisOutputChannel.appendLine(`  - ${suggestion}`);
            });
        }

        this.analysisOutputChannel.show();
    }

    private showExplanation(explanation: string): void {
        this.analysisOutputChannel.clear();
        this.analysisOutputChannel.appendLine('=== Grace Code Explanation ===\n');
        this.analysisOutputChannel.appendLine(explanation);
        this.analysisOutputChannel.show();
    }

    private async showRefactoringSuggestions(
        suggestions: any,
        editor: vscode.TextEditor,
        selection: vscode.Selection
    ): Promise<void> {
        if (!suggestions.refactored_code && !suggestions.suggestions) {
            vscode.window.showInformationMessage('No refactoring suggestions available');
            return;
        }

        const items: vscode.QuickPickItem[] = [];

        if (suggestions.refactored_code) {
            items.push({
                label: '$(edit) Apply Refactored Code',
                description: 'Replace selection with refactored version',
                detail: suggestions.refactored_code.substring(0, 100) + '...',
            });
        }

        if (suggestions.suggestions) {
            suggestions.suggestions.forEach((s: string, i: number) => {
                items.push({
                    label: `$(lightbulb) Suggestion ${i + 1}`,
                    description: s.substring(0, 50),
                    detail: s,
                });
            });
        }

        items.push({
            label: '$(book) View Full Analysis',
            description: 'Show detailed refactoring analysis',
        });

        const selected = await vscode.window.showQuickPick(items, {
            placeHolder: 'Select a refactoring option',
        });

        if (selected) {
            if (selected.label.includes('Apply Refactored Code') && suggestions.refactored_code) {
                await editor.edit(editBuilder => {
                    editBuilder.replace(selection, suggestions.refactored_code);
                });
                vscode.window.showInformationMessage('Refactoring applied');
            } else if (selected.label.includes('View Full Analysis')) {
                this.analysisOutputChannel.clear();
                this.analysisOutputChannel.appendLine('=== Grace Refactoring Analysis ===\n');
                this.analysisOutputChannel.appendLine(JSON.stringify(suggestions, null, 2));
                this.analysisOutputChannel.show();
            }
        }
    }

    getAnalysisForFile(filePath: string): AnalysisResult | undefined {
        for (const [key, result] of this.analysisCache) {
            if (key.startsWith(filePath)) {
                return result;
            }
        }
        return undefined;
    }

    clearCache(): void {
        this.analysisCache.clear();
    }

    dispose(): void {
        this.codeActionProvider?.dispose();
        this.completionProvider?.dispose();
        this.analysisOutputChannel.dispose();
    }
}
