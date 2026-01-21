/**
 * Command Registration
 *
 * Registers all Grace OS commands with VSCode.
 */

import * as vscode from 'vscode';
import { GraceOSCore } from '../core/GraceOSCore';
import { IDEBridge } from '../bridges/IDEBridge';
import { GhostLedger } from '../core/GhostLedger';
import { CognitiveIDEProvider } from '../providers/CognitiveIDEProvider';
import { MemoryMeshProvider } from '../providers/MemoryMeshProvider';
import { GenesisKeyProvider } from '../providers/GenesisKeyProvider';
import { DiagnosticProvider } from '../providers/DiagnosticProvider';
import { LearningProvider } from '../providers/LearningProvider';
import { AutonomousScheduler } from '../core/AutonomousScheduler';

export function registerCommands(
    context: vscode.ExtensionContext,
    core: GraceOSCore,
    bridge: IDEBridge,
    ghostLedger: GhostLedger,
    cognitiveProvider: CognitiveIDEProvider,
    memoryProvider: MemoryMeshProvider,
    genesisProvider: GenesisKeyProvider,
    diagnosticProvider: DiagnosticProvider,
    learningProvider: LearningProvider,
    autonomousScheduler: AutonomousScheduler
): vscode.Disposable[] {
    const disposables: vscode.Disposable[] = [];

    // Core commands
    disposables.push(
        vscode.commands.registerCommand('graceOS.activate', async () => {
            if (!bridge.isBackendConnected()) {
                const connected = await bridge.connect();
                if (connected) {
                    vscode.window.showInformationMessage('Grace OS: Connected to backend');
                } else {
                    vscode.window.showWarningMessage('Grace OS: Could not connect to backend');
                }
            } else {
                vscode.window.showInformationMessage('Grace OS: Already connected');
            }
        })
    );

    disposables.push(
        vscode.commands.registerCommand('graceOS.settings', () => {
            vscode.commands.executeCommand('workbench.action.openSettings', 'graceOS');
        })
    );

    // Chat commands
    disposables.push(
        vscode.commands.registerCommand('graceOS.chat', () => {
            vscode.commands.executeCommand('graceOS.chat.focus');
        })
    );

    // Memory commands
    disposables.push(
        vscode.commands.registerCommand('graceOS.memory.query', async () => {
            const query = await vscode.window.showInputBox({
                prompt: 'Enter memory query',
                placeHolder: 'Search memories...',
            });
            if (query) {
                await memoryProvider.queryMemory(query);
            }
        })
    );

    disposables.push(
        vscode.commands.registerCommand('graceOS.memory.store', async () => {
            await memoryProvider.storeMemory();
        })
    );

    disposables.push(
        vscode.commands.registerCommand('graceOS.memory.view', (node: any) => {
            memoryProvider.viewMemory(node);
        })
    );

    disposables.push(
        vscode.commands.registerCommand('graceOS.magma.ingest', async () => {
            await memoryProvider.ingestToMagma();
        })
    );

    disposables.push(
        vscode.commands.registerCommand('graceOS.magma.consolidate', async () => {
            await memoryProvider.triggerConsolidation();
        })
    );

    // Genesis Key commands
    disposables.push(
        vscode.commands.registerCommand('graceOS.genesis.createKey', async () => {
            await genesisProvider.createGenesisKey();
        })
    );

    disposables.push(
        vscode.commands.registerCommand('graceOS.genesis.viewLineage', async () => {
            await genesisProvider.viewLineage();
        })
    );

    disposables.push(
        vscode.commands.registerCommand('graceOS.genesis.viewKey', async (key: any) => {
            await genesisProvider.viewGenesisKey(key);
        })
    );

    // Diagnostic commands
    disposables.push(
        vscode.commands.registerCommand('graceOS.diagnostic.runCheck', async () => {
            await diagnosticProvider.runDiagnostics();
        })
    );

    disposables.push(
        vscode.commands.registerCommand('graceOS.diagnostic.viewHealth', async () => {
            await diagnosticProvider.viewHealth();
        })
    );

    disposables.push(
        vscode.commands.registerCommand('graceOS.diagnostic.viewDetail', (diagnostic: any) => {
            diagnosticProvider.viewDiagnosticDetail(diagnostic);
        })
    );

    // Cognitive commands
    disposables.push(
        vscode.commands.registerCommand('graceOS.cognitive.analyze', async () => {
            await cognitiveProvider.analyzeSelection();
        })
    );

    disposables.push(
        vscode.commands.registerCommand('graceOS.cognitive.explain', async () => {
            await cognitiveProvider.explainCode();
        })
    );

    disposables.push(
        vscode.commands.registerCommand('graceOS.cognitive.refactor', async () => {
            await cognitiveProvider.suggestRefactoring();
        })
    );

    // Learning commands
    disposables.push(
        vscode.commands.registerCommand('graceOS.learning.recordInsight', async () => {
            await learningProvider.recordInsight();
        })
    );

    disposables.push(
        vscode.commands.registerCommand('graceOS.learning.viewHistory', async () => {
            await learningProvider.viewHistory();
        })
    );

    disposables.push(
        vscode.commands.registerCommand('graceOS.learning.viewInsight', async (insight: any) => {
            await learningProvider.viewInsight(insight);
        })
    );

    // Ghost Ledger commands
    disposables.push(
        vscode.commands.registerCommand('graceOS.ghostLedger.toggle', () => {
            ghostLedger.toggle();
        })
    );

    disposables.push(
        vscode.commands.registerCommand('graceOS.ghostLedger.viewChanges', async (args?: any) => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                vscode.window.showWarningMessage('No active editor');
                return;
            }

            const filePath = args?.filePath || editor.document.uri.fsPath;
            const lineNumber = args?.lineNumber || editor.selection.active.line + 1;

            await ghostLedger.viewLineChanges(filePath, lineNumber);
        })
    );

    // Autonomous Task commands
    disposables.push(
        vscode.commands.registerCommand('graceOS.autonomous.scheduleTask', async () => {
            const taskName = await vscode.window.showInputBox({
                prompt: 'Enter task name',
                placeHolder: 'Task name...',
            });
            if (!taskName) return;

            const taskType = await vscode.window.showQuickPick(
                ['diagnostic', 'memory_consolidation', 'learning', 'cicd', 'custom'],
                { placeHolder: 'Select task type' }
            );
            if (!taskType) return;

            const schedule = await vscode.window.showQuickPick(
                [
                    { label: 'Run once', value: 'once' },
                    { label: 'Every minute', value: 'interval', interval: 60000 },
                    { label: 'Every 5 minutes', value: 'interval', interval: 300000 },
                    { label: 'Every hour', value: 'interval', interval: 3600000 },
                ],
                { placeHolder: 'Select schedule' }
            );
            if (!schedule) return;

            const taskId = autonomousScheduler.scheduleTask({
                name: taskName,
                type: taskType as any,
                schedule: schedule.value as any,
                intervalMs: (schedule as any).interval,
            });

            vscode.window.showInformationMessage(`Task scheduled: ${taskId.substring(0, 8)}...`);
        })
    );

    disposables.push(
        vscode.commands.registerCommand('graceOS.autonomous.viewTasks', () => {
            vscode.commands.executeCommand('graceOS.tasks.focus');
        })
    );

    disposables.push(
        vscode.commands.registerCommand('graceOS.autonomous.cancelTask', async (node: any) => {
            if (node?.id) {
                autonomousScheduler.cancelTask(node.id);
            }
        })
    );

    // Librarian commands
    disposables.push(
        vscode.commands.registerCommand('graceOS.librarian.search', async () => {
            const query = await vscode.window.showInputBox({
                prompt: 'Search knowledge base',
                placeHolder: 'Enter search query...',
            });
            if (query) {
                const response = await bridge.searchKnowledgeBase(query);
                if (response.success && response.data) {
                    const items = response.data.map((item: any) => ({
                        label: item.title || item.content?.substring(0, 50) || 'Untitled',
                        description: item.source || item.type,
                        detail: item.content,
                    }));

                    await vscode.window.showQuickPick(items, {
                        placeHolder: 'Search results',
                        matchOnDetail: true,
                    });
                } else {
                    vscode.window.showInformationMessage('No results found');
                }
            }
        })
    );

    disposables.push(
        vscode.commands.registerCommand('graceOS.librarian.tag', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                vscode.window.showWarningMessage('No active editor');
                return;
            }

            const tagsInput = await vscode.window.showInputBox({
                prompt: 'Enter tags (comma-separated)',
                placeHolder: 'tag1, tag2, tag3',
            });
            if (!tagsInput) return;

            const tags = tagsInput.split(',').map(t => t.trim()).filter(Boolean);
            const response = await bridge.tagFile(editor.document.uri.fsPath, tags);

            if (response.success) {
                vscode.window.showInformationMessage('File tagged successfully');
            } else {
                vscode.window.showErrorMessage(`Failed to tag file: ${response.error}`);
            }
        })
    );

    // Whitelist commands
    disposables.push(
        vscode.commands.registerCommand('graceOS.whitelist.propose', async () => {
            const editor = vscode.window.activeTextEditor;

            let content: string;
            if (editor && !editor.selection.isEmpty) {
                content = editor.document.getText(editor.selection);
            } else {
                const input = await vscode.window.showInputBox({
                    prompt: 'Enter content to propose for whitelist',
                    placeHolder: 'Content...',
                });
                if (!input) return;
                content = input;
            }

            const category = await vscode.window.showQuickPick(
                ['pattern', 'rule', 'template', 'snippet', 'other'],
                { placeHolder: 'Select category' }
            );
            if (!category) return;

            const response = await bridge.proposeWhitelistEntry(content, category, {
                source: 'vscode',
                filePath: editor?.document.uri.fsPath,
            });

            if (response.success) {
                vscode.window.showInformationMessage('Whitelist proposal submitted');
            } else {
                vscode.window.showErrorMessage(`Proposal failed: ${response.error}`);
            }
        })
    );

    // CI/CD commands
    disposables.push(
        vscode.commands.registerCommand('graceOS.cicd.trigger', async () => {
            const confirm = await vscode.window.showWarningMessage(
                'Trigger CI/CD pipeline?',
                { modal: true },
                'Yes'
            );
            if (confirm !== 'Yes') return;

            await vscode.window.withProgress(
                {
                    location: vscode.ProgressLocation.Notification,
                    title: 'Triggering CI/CD pipeline...',
                },
                async () => {
                    const response = await bridge.triggerCICDPipeline();
                    if (response.success) {
                        vscode.window.showInformationMessage('CI/CD pipeline triggered');
                    } else {
                        vscode.window.showErrorMessage(`Pipeline trigger failed: ${response.error}`);
                    }
                }
            );
        })
    );

    // Refresh commands for tree views
    disposables.push(
        vscode.commands.registerCommand('graceOS.memory.refresh', () => {
            memoryProvider.refresh();
        })
    );

    disposables.push(
        vscode.commands.registerCommand('graceOS.genesis.refresh', () => {
            genesisProvider.refresh();
        })
    );

    disposables.push(
        vscode.commands.registerCommand('graceOS.diagnostics.refresh', () => {
            diagnosticProvider.refresh();
        })
    );

    disposables.push(
        vscode.commands.registerCommand('graceOS.learning.refresh', () => {
            learningProvider.refresh();
        })
    );

    disposables.push(
        vscode.commands.registerCommand('graceOS.tasks.refresh', () => {
            autonomousScheduler.refresh();
        })
    );

    return disposables;
}
