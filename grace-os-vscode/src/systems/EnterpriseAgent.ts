/**
 * Enterprise Coding Agent - Full IDE Integration
 *
 * Comprehensive software engineering agent with:
 * - Code generation and modification
 * - File operations (create, edit, delete)
 * - Git operations
 * - Test execution
 * - Build and deployment
 * - Multi-step task execution
 * - Context-aware assistance
 */

import * as vscode from 'vscode';
import * as path from 'path';
import { GraceOSCore } from '../core/GraceOSCore';
import { IDEBridge } from '../bridges/IDEBridge';
import { GraceWebSocketBridge } from '../bridges/WebSocketBridge';
import { SecurityLayer } from './SecurityLayer';

// ============================================================================
// Types
// ============================================================================

export interface AgentTask {
    id: string;
    type: AgentTaskType;
    description: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    steps: AgentStep[];
    result?: any;
    error?: string;
    createdAt: Date;
    completedAt?: Date;
}

export type AgentTaskType =
    | 'code_generation'
    | 'code_modification'
    | 'file_operation'
    | 'git_operation'
    | 'test_execution'
    | 'build'
    | 'deploy'
    | 'refactor'
    | 'debug'
    | 'explain'
    | 'multi_step';

export interface AgentStep {
    id: string;
    type: string;
    description: string;
    status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
    input?: any;
    output?: any;
    error?: string;
}

export interface CodeGenerationRequest {
    prompt: string;
    language: string;
    context?: {
        filePath?: string;
        surroundingCode?: string;
        imports?: string[];
        projectStructure?: string[];
    };
    constraints?: {
        maxLines?: number;
        style?: string;
        frameworks?: string[];
    };
}

export interface CodeModificationRequest {
    filePath: string;
    instruction: string;
    targetRange?: vscode.Range;
    preserveStyle?: boolean;
}

export interface ExecutionContext {
    workspaceRoot: string;
    currentFile?: string;
    selection?: string;
    diagnostics?: vscode.Diagnostic[];
    gitStatus?: any;
    openFiles?: string[];
}

// ============================================================================
// Tool Definitions
// ============================================================================

interface AgentTool {
    name: string;
    description: string;
    execute: (params: any) => Promise<any>;
}

// ============================================================================
// Enterprise Agent
// ============================================================================

export class EnterpriseAgent {
    private core: GraceOSCore;
    private bridge: IDEBridge;
    private wsBridge: GraceWebSocketBridge;
    private security: SecurityLayer;
    private activeTasks: Map<string, AgentTask> = new Map();
    private tools: Map<string, AgentTool> = new Map();
    private outputChannel: vscode.OutputChannel;

    constructor(
        core: GraceOSCore,
        bridge: IDEBridge,
        wsBridge: GraceWebSocketBridge,
        security: SecurityLayer
    ) {
        this.core = core;
        this.bridge = bridge;
        this.wsBridge = wsBridge;
        this.security = security;
        this.outputChannel = vscode.window.createOutputChannel('Grace Agent');

        this.registerTools();
    }

    async initialize(): Promise<void> {
        this.core.log('Initializing Enterprise Agent...');
        this.core.enableFeature('enterpriseAgent');
        this.core.log('Enterprise Agent initialized');
    }

    private registerTools(): void {
        // File Operations
        this.tools.set('read_file', {
            name: 'read_file',
            description: 'Read contents of a file',
            execute: async (params: { filePath: string }) => {
                const uri = vscode.Uri.file(params.filePath);
                const doc = await vscode.workspace.openTextDocument(uri);
                return doc.getText();
            },
        });

        this.tools.set('write_file', {
            name: 'write_file',
            description: 'Write content to a file',
            execute: async (params: { filePath: string; content: string }) => {
                const uri = vscode.Uri.file(params.filePath);
                const edit = new vscode.WorkspaceEdit();
                edit.createFile(uri, { overwrite: true });
                await vscode.workspace.applyEdit(edit);

                const doc = await vscode.workspace.openTextDocument(uri);
                const fullRange = new vscode.Range(0, 0, doc.lineCount, 0);
                const editBuilder = new vscode.WorkspaceEdit();
                editBuilder.replace(uri, fullRange, params.content);
                await vscode.workspace.applyEdit(editBuilder);
                await doc.save();

                return { success: true, path: params.filePath };
            },
        });

        this.tools.set('edit_file', {
            name: 'edit_file',
            description: 'Edit a specific range in a file',
            execute: async (params: {
                filePath: string;
                startLine: number;
                endLine: number;
                newContent: string;
            }) => {
                const uri = vscode.Uri.file(params.filePath);
                const doc = await vscode.workspace.openTextDocument(uri);
                const range = new vscode.Range(
                    params.startLine - 1,
                    0,
                    params.endLine - 1,
                    doc.lineAt(params.endLine - 1).text.length
                );

                const edit = new vscode.WorkspaceEdit();
                edit.replace(uri, range, params.newContent);
                await vscode.workspace.applyEdit(edit);
                await doc.save();

                return { success: true, path: params.filePath };
            },
        });

        this.tools.set('create_file', {
            name: 'create_file',
            description: 'Create a new file',
            execute: async (params: { filePath: string; content: string }) => {
                const uri = vscode.Uri.file(params.filePath);
                const edit = new vscode.WorkspaceEdit();
                edit.createFile(uri, { overwrite: false, ignoreIfExists: false });
                await vscode.workspace.applyEdit(edit);

                const doc = await vscode.workspace.openTextDocument(uri);
                const editBuilder = new vscode.WorkspaceEdit();
                editBuilder.insert(uri, new vscode.Position(0, 0), params.content);
                await vscode.workspace.applyEdit(editBuilder);
                await doc.save();

                return { success: true, path: params.filePath };
            },
        });

        this.tools.set('delete_file', {
            name: 'delete_file',
            description: 'Delete a file',
            execute: async (params: { filePath: string }) => {
                const uri = vscode.Uri.file(params.filePath);
                const edit = new vscode.WorkspaceEdit();
                edit.deleteFile(uri);
                await vscode.workspace.applyEdit(edit);
                return { success: true, deleted: params.filePath };
            },
        });

        // Search Operations
        this.tools.set('search_files', {
            name: 'search_files',
            description: 'Search for files matching a pattern',
            execute: async (params: { pattern: string; maxResults?: number }) => {
                const files = await vscode.workspace.findFiles(
                    params.pattern,
                    '**/node_modules/**',
                    params.maxResults || 50
                );
                return files.map(f => f.fsPath);
            },
        });

        this.tools.set('search_text', {
            name: 'search_text',
            description: 'Search for text in workspace',
            execute: async (params: { query: string; include?: string }) => {
                // Use workspace search
                const results: Array<{ file: string; line: number; text: string }> = [];

                const files = await vscode.workspace.findFiles(
                    params.include || '**/*',
                    '**/node_modules/**',
                    100
                );

                for (const file of files.slice(0, 20)) {
                    try {
                        const doc = await vscode.workspace.openTextDocument(file);
                        const text = doc.getText();
                        const lines = text.split('\n');

                        for (let i = 0; i < lines.length; i++) {
                            if (lines[i].includes(params.query)) {
                                results.push({
                                    file: file.fsPath,
                                    line: i + 1,
                                    text: lines[i].trim(),
                                });
                            }
                        }
                    } catch {
                        // Skip files that can't be opened
                    }
                }

                return results;
            },
        });

        // Terminal Operations
        this.tools.set('run_command', {
            name: 'run_command',
            description: 'Run a terminal command',
            execute: async (params: { command: string; cwd?: string }) => {
                return new Promise((resolve, reject) => {
                    const terminal = vscode.window.createTerminal({
                        name: 'Grace Agent',
                        cwd: params.cwd || vscode.workspace.workspaceFolders?.[0]?.uri.fsPath,
                    });

                    terminal.show();
                    terminal.sendText(params.command);

                    // Note: In real implementation, would capture output
                    resolve({ executed: true, command: params.command });
                });
            },
        });

        this.tools.set('run_tests', {
            name: 'run_tests',
            description: 'Run test suite',
            execute: async (params: { testPattern?: string; coverage?: boolean }) => {
                const terminal = vscode.window.createTerminal('Grace Tests');
                terminal.show();

                let command = 'npm test';
                if (params.testPattern) {
                    command += ` -- --testPathPattern="${params.testPattern}"`;
                }
                if (params.coverage) {
                    command += ' -- --coverage';
                }

                terminal.sendText(command);
                return { executed: true, command };
            },
        });

        // Git Operations
        this.tools.set('git_status', {
            name: 'git_status',
            description: 'Get git status',
            execute: async () => {
                const gitExtension = vscode.extensions.getExtension('vscode.git');
                if (gitExtension) {
                    const git = gitExtension.exports.getAPI(1);
                    const repo = git.repositories[0];
                    if (repo) {
                        return {
                            branch: repo.state.HEAD?.name,
                            changes: repo.state.workingTreeChanges.length,
                            staged: repo.state.indexChanges.length,
                        };
                    }
                }
                return { error: 'Git not available' };
            },
        });

        this.tools.set('git_commit', {
            name: 'git_commit',
            description: 'Commit staged changes',
            execute: async (params: { message: string }) => {
                const gitExtension = vscode.extensions.getExtension('vscode.git');
                if (gitExtension) {
                    const git = gitExtension.exports.getAPI(1);
                    const repo = git.repositories[0];
                    if (repo) {
                        await repo.commit(params.message);
                        return { success: true, message: params.message };
                    }
                }
                return { error: 'Git not available' };
            },
        });

        // Code Analysis
        this.tools.set('analyze_code', {
            name: 'analyze_code',
            description: 'Analyze code for issues and suggestions',
            execute: async (params: { code: string; language: string }) => {
                const response = await this.bridge.analyzeCode(params.code, params.language);
                return response.data;
            },
        });

        this.tools.set('get_diagnostics', {
            name: 'get_diagnostics',
            description: 'Get all diagnostics for a file',
            execute: async (params: { filePath: string }) => {
                const uri = vscode.Uri.file(params.filePath);
                const diagnostics = vscode.languages.getDiagnostics(uri);
                return diagnostics.map(d => ({
                    message: d.message,
                    severity: vscode.DiagnosticSeverity[d.severity],
                    range: {
                        start: { line: d.range.start.line + 1, character: d.range.start.character },
                        end: { line: d.range.end.line + 1, character: d.range.end.character },
                    },
                }));
            },
        });
    }

    // ============================================================================
    // Task Execution
    // ============================================================================

    async executeTask(request: string, context?: ExecutionContext): Promise<AgentTask> {
        const task: AgentTask = {
            id: `task_${Date.now()}`,
            type: this.determineTaskType(request),
            description: request,
            status: 'pending',
            steps: [],
            createdAt: new Date(),
        };

        this.activeTasks.set(task.id, task);
        this.logOutput(`Starting task: ${task.description}`);

        try {
            task.status = 'running';

            // Get execution plan from backend
            const plan = await this.planTask(request, context);

            // Execute each step
            for (const step of plan.steps) {
                task.steps.push(step);
                step.status = 'running';
                this.logOutput(`  Step: ${step.description}`);

                try {
                    const tool = this.tools.get(step.type);
                    if (tool) {
                        step.output = await tool.execute(step.input);
                        step.status = 'completed';
                        this.logOutput(`    ✓ Completed`);
                    } else {
                        // Handle through backend
                        const response = await this.bridge.invokeAgent(step.type, step.input);
                        step.output = response.data;
                        step.status = 'completed';
                    }
                } catch (error: any) {
                    step.status = 'failed';
                    step.error = error.message;
                    this.logOutput(`    ✗ Failed: ${error.message}`);

                    // Try recovery
                    const recovered = await this.attemptRecovery(step, error);
                    if (!recovered) {
                        throw error;
                    }
                }
            }

            task.status = 'completed';
            task.completedAt = new Date();
            task.result = this.aggregateResults(task.steps);

            this.logOutput(`Task completed successfully`);

        } catch (error: any) {
            task.status = 'failed';
            task.error = error.message;
            task.completedAt = new Date();
            this.logOutput(`Task failed: ${error.message}`);
        }

        return task;
    }

    private determineTaskType(request: string): AgentTaskType {
        const lower = request.toLowerCase();

        if (lower.includes('generate') || lower.includes('create') || lower.includes('write')) {
            return 'code_generation';
        }
        if (lower.includes('modify') || lower.includes('change') || lower.includes('update')) {
            return 'code_modification';
        }
        if (lower.includes('refactor')) {
            return 'refactor';
        }
        if (lower.includes('test')) {
            return 'test_execution';
        }
        if (lower.includes('build')) {
            return 'build';
        }
        if (lower.includes('deploy')) {
            return 'deploy';
        }
        if (lower.includes('debug') || lower.includes('fix')) {
            return 'debug';
        }
        if (lower.includes('explain')) {
            return 'explain';
        }
        if (lower.includes('git') || lower.includes('commit')) {
            return 'git_operation';
        }

        return 'multi_step';
    }

    private async planTask(request: string, context?: ExecutionContext): Promise<{ steps: AgentStep[] }> {
        // Get execution plan from backend or generate locally
        try {
            const response = await this.bridge.invokeAgent('plan_task', {
                request,
                context,
                availableTools: Array.from(this.tools.keys()),
            });

            if (response.success && response.data?.steps) {
                return response.data;
            }
        } catch {
            // Fallback to local planning
        }

        // Simple local planning
        const steps: AgentStep[] = [];
        const taskType = this.determineTaskType(request);

        switch (taskType) {
            case 'code_generation':
                steps.push({
                    id: `step_1`,
                    type: 'analyze_code',
                    description: 'Analyze context',
                    status: 'pending',
                    input: { code: context?.selection || '', language: 'typescript' },
                });
                steps.push({
                    id: `step_2`,
                    type: 'generate_code',
                    description: 'Generate code',
                    status: 'pending',
                    input: { prompt: request, context },
                });
                break;

            case 'test_execution':
                steps.push({
                    id: `step_1`,
                    type: 'run_tests',
                    description: 'Run tests',
                    status: 'pending',
                    input: { coverage: true },
                });
                break;

            case 'debug':
                steps.push({
                    id: `step_1`,
                    type: 'get_diagnostics',
                    description: 'Get diagnostics',
                    status: 'pending',
                    input: { filePath: context?.currentFile },
                });
                steps.push({
                    id: `step_2`,
                    type: 'analyze_code',
                    description: 'Analyze issues',
                    status: 'pending',
                    input: { code: context?.selection || '', language: 'typescript' },
                });
                break;

            default:
                steps.push({
                    id: `step_1`,
                    type: 'analyze_code',
                    description: 'Analyze request',
                    status: 'pending',
                    input: { code: context?.selection || '', language: 'typescript' },
                });
        }

        return { steps };
    }

    private async attemptRecovery(step: AgentStep, error: Error): Promise<boolean> {
        this.logOutput(`    Attempting recovery...`);

        // Simple retry with backoff
        await new Promise(resolve => setTimeout(resolve, 1000));

        try {
            const tool = this.tools.get(step.type);
            if (tool) {
                step.output = await tool.execute(step.input);
                step.status = 'completed';
                this.logOutput(`    ✓ Recovery successful`);
                return true;
            }
        } catch {
            // Recovery failed
        }

        return false;
    }

    private aggregateResults(steps: AgentStep[]): any {
        const results: Record<string, any> = {};

        for (const step of steps) {
            if (step.output) {
                results[step.id] = step.output;
            }
        }

        return results;
    }

    // ============================================================================
    // High-Level Operations
    // ============================================================================

    async generateCode(request: CodeGenerationRequest): Promise<string> {
        const response = await this.bridge.invokeAgent('generate_code', request);
        return response.data?.code || '';
    }

    async modifyCode(request: CodeModificationRequest): Promise<boolean> {
        const editor = vscode.window.activeTextEditor;
        if (!editor) return false;

        const response = await this.bridge.invokeAgent('modify_code', {
            ...request,
            currentCode: editor.document.getText(),
        });

        if (response.success && response.data?.modifiedCode) {
            const edit = new vscode.WorkspaceEdit();
            const fullRange = new vscode.Range(
                0,
                0,
                editor.document.lineCount,
                0
            );
            edit.replace(editor.document.uri, fullRange, response.data.modifiedCode);
            return vscode.workspace.applyEdit(edit);
        }

        return false;
    }

    async runTests(pattern?: string): Promise<void> {
        await this.tools.get('run_tests')?.execute({ testPattern: pattern, coverage: true });
    }

    async fixErrors(): Promise<void> {
        const editor = vscode.window.activeTextEditor;
        if (!editor) return;

        const diagnostics = vscode.languages.getDiagnostics(editor.document.uri);
        const errors = diagnostics.filter(d => d.severity === vscode.DiagnosticSeverity.Error);

        if (errors.length === 0) {
            vscode.window.showInformationMessage('No errors to fix');
            return;
        }

        await this.executeTask(`Fix ${errors.length} errors in current file`, {
            workspaceRoot: vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || '',
            currentFile: editor.document.uri.fsPath,
            diagnostics: errors,
        });
    }

    // ============================================================================
    // Utilities
    // ============================================================================

    private logOutput(message: string): void {
        const timestamp = new Date().toISOString().split('T')[1].split('.')[0];
        this.outputChannel.appendLine(`[${timestamp}] ${message}`);
    }

    showOutput(): void {
        this.outputChannel.show();
    }

    getActiveTasks(): AgentTask[] {
        return Array.from(this.activeTasks.values());
    }

    getTask(taskId: string): AgentTask | undefined {
        return this.activeTasks.get(taskId);
    }

    dispose(): void {
        this.outputChannel.dispose();
    }
}
