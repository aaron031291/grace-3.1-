/**
 * Enterprise Agent Comprehensive Test Suite
 *
 * Tests full agent execution capabilities
 */

import * as assert from 'assert';
import { EnterpriseAgent, AgentTool, AgentTask, ExecutionResult } from '../../systems/EnterpriseAgent';

suite('EnterpriseAgent Test Suite', () => {
    let agent: EnterpriseAgent;

    const mockCore = {
        log: () => {},
        getConfig: () => ({ agent: { maxSteps: 10, timeout: 30000 } }),
        enableFeature: () => {},
        on: () => {},
    };

    const mockBridge = {
        invokeAgent: async (method: string, params: any) => {
            if (method === 'execute_tool') {
                return { success: true, data: { result: 'executed' } };
            }
            return { success: true, data: {} };
        },
    };

    setup(() => {
        agent = new EnterpriseAgent(mockCore as any, mockBridge as any);
    });

    teardown(() => {
        agent.dispose();
    });

    // ============================================================================
    // Tool Registration Tests
    // ============================================================================

    suite('Tool Registration', () => {
        test('should register tools', () => {
            agent.registerTool({
                id: 'test_tool',
                name: 'Test Tool',
                description: 'A test tool',
                parameters: {},
                execute: async () => ({ success: true, data: 'test' }),
            });

            const tools = agent.getTools();
            assert.ok(tools.some(t => t.id === 'test_tool'));
        });

        test('should execute registered tools', async () => {
            let executed = false;

            agent.registerTool({
                id: 'exec_tool',
                name: 'Exec Tool',
                description: 'Execution test',
                parameters: {},
                execute: async () => {
                    executed = true;
                    return { success: true, data: 'done' };
                },
            });

            await agent.executeTool('exec_tool', {});
            assert.strictEqual(executed, true);
        });

        test('should pass parameters to tools', async () => {
            let receivedParams: any = null;

            agent.registerTool({
                id: 'param_tool',
                name: 'Param Tool',
                description: 'Parameter test',
                parameters: { input: { type: 'string' } },
                execute: async (params) => {
                    receivedParams = params;
                    return { success: true, data: params };
                },
            });

            await agent.executeTool('param_tool', { input: 'test_value' });
            assert.strictEqual(receivedParams.input, 'test_value');
        });

        test('should handle tool errors', async () => {
            agent.registerTool({
                id: 'error_tool',
                name: 'Error Tool',
                description: 'Error test',
                parameters: {},
                execute: async () => {
                    throw new Error('Tool error');
                },
            });

            const result = await agent.executeTool('error_tool', {});
            assert.strictEqual(result.success, false);
        });

        test('should unregister tools', () => {
            agent.registerTool({
                id: 'removable_tool',
                name: 'Removable',
                description: 'Test',
                parameters: {},
                execute: async () => ({ success: true }),
            });

            agent.unregisterTool('removable_tool');
            const tools = agent.getTools();
            assert.ok(!tools.some(t => t.id === 'removable_tool'));
        });
    });

    // ============================================================================
    // Built-in Tools Tests
    // ============================================================================

    suite('Built-in Tools', () => {
        test('should have read_file tool', () => {
            const tools = agent.getTools();
            assert.ok(tools.some(t => t.id === 'read_file'));
        });

        test('should have write_file tool', () => {
            const tools = agent.getTools();
            assert.ok(tools.some(t => t.id === 'write_file'));
        });

        test('should have edit_file tool', () => {
            const tools = agent.getTools();
            assert.ok(tools.some(t => t.id === 'edit_file'));
        });

        test('should have search_files tool', () => {
            const tools = agent.getTools();
            assert.ok(tools.some(t => t.id === 'search_files'));
        });

        test('should have run_command tool', () => {
            const tools = agent.getTools();
            assert.ok(tools.some(t => t.id === 'run_command'));
        });

        test('should have analyze_code tool', () => {
            const tools = agent.getTools();
            assert.ok(tools.some(t => t.id === 'analyze_code'));
        });

        test('should have git tools', () => {
            const tools = agent.getTools();
            assert.ok(tools.some(t => t.id === 'git_status' || t.id === 'git_commit'));
        });
    });

    // ============================================================================
    // Task Execution Tests
    // ============================================================================

    suite('Task Execution', () => {
        test('should create tasks', () => {
            const task = agent.createTask({
                name: 'Test Task',
                description: 'A test task',
                steps: [{ action: 'test', params: {} }],
            });

            assert.ok(task.id);
            assert.strictEqual(task.status, 'pending');
        });

        test('should execute tasks', async () => {
            agent.registerTool({
                id: 'task_tool',
                name: 'Task Tool',
                description: 'For task test',
                parameters: {},
                execute: async () => ({ success: true, data: 'completed' }),
            });

            const task = agent.createTask({
                name: 'Exec Task',
                description: 'Execution test',
                steps: [{ action: 'task_tool', params: {} }],
            });

            const result = await agent.executeTask(task.id);
            assert.strictEqual(result.success, true);
        });

        test('should track task progress', async () => {
            agent.registerTool({
                id: 'progress_tool',
                name: 'Progress Tool',
                description: 'Progress test',
                parameters: {},
                execute: async () => ({ success: true }),
            });

            const task = agent.createTask({
                name: 'Progress Task',
                description: 'Track progress',
                steps: [
                    { action: 'progress_tool', params: {} },
                    { action: 'progress_tool', params: {} },
                ],
            });

            await agent.executeTask(task.id);
            const taskState = agent.getTask(task.id);
            assert.strictEqual(taskState?.status, 'completed');
        });

        test('should handle task failures', async () => {
            agent.registerTool({
                id: 'fail_tool',
                name: 'Fail Tool',
                description: 'Failure test',
                parameters: {},
                execute: async () => {
                    throw new Error('Task failed');
                },
            });

            const task = agent.createTask({
                name: 'Fail Task',
                description: 'Should fail',
                steps: [{ action: 'fail_tool', params: {} }],
            });

            const result = await agent.executeTask(task.id);
            assert.strictEqual(result.success, false);
        });

        test('should cancel tasks', async () => {
            const task = agent.createTask({
                name: 'Cancel Task',
                description: 'Should be cancelled',
                steps: [{ action: 'unknown', params: {} }],
            });

            agent.cancelTask(task.id);
            const taskState = agent.getTask(task.id);
            assert.strictEqual(taskState?.status, 'cancelled');
        });

        test('should list all tasks', () => {
            agent.createTask({ name: 'Task 1', description: 'First', steps: [] });
            agent.createTask({ name: 'Task 2', description: 'Second', steps: [] });

            const tasks = agent.getTasks();
            assert.ok(tasks.length >= 2);
        });
    });

    // ============================================================================
    // Plan Execution Tests
    // ============================================================================

    suite('Plan Execution', () => {
        test('should generate execution plans', async () => {
            const plan = await agent.generatePlan('Fix the bug in file.ts');
            assert.ok(plan);
            assert.ok(plan.steps.length > 0);
        });

        test('should execute plans', async () => {
            agent.registerTool({
                id: 'plan_step',
                name: 'Plan Step',
                description: 'Plan step execution',
                parameters: {},
                execute: async () => ({ success: true }),
            });

            const plan = {
                goal: 'Test plan',
                steps: [{ action: 'plan_step', params: {} }],
            };

            const result = await agent.executePlan(plan);
            assert.strictEqual(result.success, true);
        });

        test('should handle plan failures gracefully', async () => {
            agent.registerTool({
                id: 'plan_fail',
                name: 'Plan Fail',
                description: 'Will fail',
                parameters: {},
                execute: async () => { throw new Error('Plan step failed'); },
            });

            const plan = {
                goal: 'Failing plan',
                steps: [{ action: 'plan_fail', params: {} }],
            };

            const result = await agent.executePlan(plan);
            assert.strictEqual(result.success, false);
        });
    });

    // ============================================================================
    // Autonomous Mode Tests
    // ============================================================================

    suite('Autonomous Mode', () => {
        test('should enable autonomous mode', () => {
            agent.enableAutonomousMode();
            assert.strictEqual(agent.isAutonomous(), true);
        });

        test('should disable autonomous mode', () => {
            agent.enableAutonomousMode();
            agent.disableAutonomousMode();
            assert.strictEqual(agent.isAutonomous(), false);
        });

        test('should respect step limits', async () => {
            let stepCount = 0;

            agent.registerTool({
                id: 'step_counter',
                name: 'Step Counter',
                description: 'Counts steps',
                parameters: {},
                execute: async () => {
                    stepCount++;
                    return { success: true };
                },
            });

            const task = agent.createTask({
                name: 'Many Steps',
                description: 'Should be limited',
                steps: Array(20).fill({ action: 'step_counter', params: {} }),
                maxSteps: 5,
            });

            await agent.executeTask(task.id);
            assert.ok(stepCount <= 5);
        });
    });

    // ============================================================================
    // Execution History Tests
    // ============================================================================

    suite('Execution History', () => {
        test('should track execution history', async () => {
            agent.registerTool({
                id: 'history_tool',
                name: 'History Tool',
                description: 'For history',
                parameters: {},
                execute: async () => ({ success: true }),
            });

            await agent.executeTool('history_tool', {});
            const history = agent.getExecutionHistory();
            assert.ok(history.length > 0);
        });

        test('should include execution details in history', async () => {
            agent.registerTool({
                id: 'detail_tool',
                name: 'Detail Tool',
                description: 'For details',
                parameters: { input: { type: 'string' } },
                execute: async (params) => ({ success: true, data: params.input }),
            });

            await agent.executeTool('detail_tool', { input: 'test' });
            const history = agent.getExecutionHistory();
            const lastExecution = history[history.length - 1];

            assert.strictEqual(lastExecution.toolId, 'detail_tool');
            assert.deepStrictEqual(lastExecution.params, { input: 'test' });
        });

        test('should clear execution history', async () => {
            agent.registerTool({
                id: 'clear_tool',
                name: 'Clear Tool',
                description: 'Test',
                parameters: {},
                execute: async () => ({ success: true }),
            });

            await agent.executeTool('clear_tool', {});
            agent.clearExecutionHistory();
            const history = agent.getExecutionHistory();
            assert.strictEqual(history.length, 0);
        });
    });

    // ============================================================================
    // Statistics Tests
    // ============================================================================

    suite('Agent Statistics', () => {
        test('should track tool execution counts', async () => {
            agent.registerTool({
                id: 'count_tool',
                name: 'Count Tool',
                description: 'For counting',
                parameters: {},
                execute: async () => ({ success: true }),
            });

            await agent.executeTool('count_tool', {});
            await agent.executeTool('count_tool', {});
            await agent.executeTool('count_tool', {});

            const stats = agent.getStats();
            assert.ok(stats.totalExecutions >= 3);
        });

        test('should track success rate', async () => {
            agent.registerTool({
                id: 'success_tool',
                name: 'Success Tool',
                description: 'Always succeeds',
                parameters: {},
                execute: async () => ({ success: true }),
            });

            agent.registerTool({
                id: 'fail_sometimes',
                name: 'Fail Sometimes',
                description: 'Fails',
                parameters: {},
                execute: async () => { throw new Error('Failed'); },
            });

            await agent.executeTool('success_tool', {});
            await agent.executeTool('fail_sometimes', {});

            const stats = agent.getStats();
            assert.ok(typeof stats.successRate === 'number');
        });
    });
});
