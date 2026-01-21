/**
 * DiagnosticMachine Comprehensive Test Suite
 *
 * Tests all 4 layers: Sensors, Interpreters, Judgement, Actions
 */

import * as assert from 'assert';
import {
    SensorLayer,
    InterpreterLayer,
    JudgementLayer,
    ActionLayer,
    DiagnosticMachine,
    SensorReading,
    DiagnosticPattern,
    DiagnosticJudgement
} from '../../systems/DiagnosticMachine';

suite('DiagnosticMachine Test Suite', () => {
    // ============================================================================
    // Layer 1: Sensor Tests
    // ============================================================================

    suite('Layer 1 - Sensors', () => {
        let sensorLayer: SensorLayer;

        setup(() => {
            sensorLayer = new SensorLayer();
        });

        test('should register sensors', () => {
            sensorLayer.registerSensor({
                id: 'test_sensor',
                name: 'Test Sensor',
                type: 'performance',
                interval: 1000,
                collect: async () => ({ value: 42 }),
            });

            const sensors = sensorLayer.getSensors();
            assert.ok(sensors.some(s => s.id === 'test_sensor'));
        });

        test('should collect readings from all sensors', async () => {
            sensorLayer.registerSensor({
                id: 'sensor1',
                name: 'Sensor 1',
                type: 'performance',
                interval: 1000,
                collect: async () => ({ cpu: 50 }),
            });

            sensorLayer.registerSensor({
                id: 'sensor2',
                name: 'Sensor 2',
                type: 'memory',
                interval: 1000,
                collect: async () => ({ heap: 100 }),
            });

            const readings = await sensorLayer.collectAll();
            assert.strictEqual(readings.length, 2);
        });

        test('should handle sensor errors gracefully', async () => {
            sensorLayer.registerSensor({
                id: 'error_sensor',
                name: 'Error Sensor',
                type: 'performance',
                interval: 1000,
                collect: async () => { throw new Error('Test error'); },
            });

            const readings = await sensorLayer.collectAll();
            const errorReading = readings.find(r => r.sensorId === 'error_sensor');
            assert.ok(errorReading?.error);
        });

        test('should generate unique reading IDs', async () => {
            sensorLayer.registerSensor({
                id: 'unique_sensor',
                name: 'Unique Sensor',
                type: 'performance',
                interval: 1000,
                collect: async () => ({ value: 1 }),
            });

            const readings1 = await sensorLayer.collectAll();
            const readings2 = await sensorLayer.collectAll();

            assert.notStrictEqual(readings1[0].id, readings2[0].id);
        });

        test('should track reading timestamps', async () => {
            sensorLayer.registerSensor({
                id: 'time_sensor',
                name: 'Time Sensor',
                type: 'performance',
                interval: 1000,
                collect: async () => ({ time: Date.now() }),
            });

            const before = new Date();
            const readings = await sensorLayer.collectAll();
            const after = new Date();

            assert.ok(readings[0].timestamp >= before);
            assert.ok(readings[0].timestamp <= after);
        });

        test('should unregister sensors', () => {
            sensorLayer.registerSensor({
                id: 'removable',
                name: 'Removable',
                type: 'performance',
                interval: 1000,
                collect: async () => ({}),
            });

            sensorLayer.unregisterSensor('removable');
            const sensors = sensorLayer.getSensors();
            assert.ok(!sensors.some(s => s.id === 'removable'));
        });
    });

    // ============================================================================
    // Layer 2: Interpreter Tests
    // ============================================================================

    suite('Layer 2 - Interpreters', () => {
        let interpreterLayer: InterpreterLayer;

        setup(() => {
            interpreterLayer = new InterpreterLayer();
        });

        test('should register interpreters', () => {
            interpreterLayer.registerInterpreter({
                id: 'test_interpreter',
                name: 'Test Interpreter',
                sensorTypes: ['performance'],
                interpret: async (readings) => [],
            });

            const interpreters = interpreterLayer.getInterpreters();
            assert.ok(interpreters.some(i => i.id === 'test_interpreter'));
        });

        test('should interpret readings into patterns', async () => {
            interpreterLayer.registerInterpreter({
                id: 'pattern_interpreter',
                name: 'Pattern Interpreter',
                sensorTypes: ['performance'],
                interpret: async (readings) => [{
                    id: 'pattern1',
                    patternType: 'high_cpu',
                    confidence: 0.9,
                    severity: 'warning',
                    description: 'High CPU detected',
                    readings: readings.map(r => r.id),
                    timestamp: new Date(),
                }],
            });

            const readings: SensorReading[] = [{
                id: 'r1',
                sensorId: 's1',
                sensorType: 'performance',
                timestamp: new Date(),
                data: { cpu: 95 },
            }];

            const patterns = await interpreterLayer.interpretAll(readings);
            assert.strictEqual(patterns.length, 1);
            assert.strictEqual(patterns[0].patternType, 'high_cpu');
        });

        test('should filter readings by sensor type', async () => {
            let receivedReadings: SensorReading[] = [];

            interpreterLayer.registerInterpreter({
                id: 'memory_only',
                name: 'Memory Only',
                sensorTypes: ['memory'],
                interpret: async (readings) => {
                    receivedReadings = readings;
                    return [];
                },
            });

            const readings: SensorReading[] = [
                { id: 'r1', sensorId: 's1', sensorType: 'performance', timestamp: new Date(), data: {} },
                { id: 'r2', sensorId: 's2', sensorType: 'memory', timestamp: new Date(), data: {} },
            ];

            await interpreterLayer.interpretAll(readings);
            assert.strictEqual(receivedReadings.length, 1);
            assert.strictEqual(receivedReadings[0].sensorType, 'memory');
        });

        test('should assign confidence scores', async () => {
            interpreterLayer.registerInterpreter({
                id: 'confidence_test',
                name: 'Confidence Test',
                sensorTypes: ['performance'],
                interpret: async (readings) => [{
                    id: 'p1',
                    patternType: 'test',
                    confidence: 0.75,
                    severity: 'info',
                    description: 'Test',
                    readings: [],
                    timestamp: new Date(),
                }],
            });

            const readings: SensorReading[] = [{
                id: 'r1',
                sensorId: 's1',
                sensorType: 'performance',
                timestamp: new Date(),
                data: {},
            }];

            const patterns = await interpreterLayer.interpretAll(readings);
            assert.strictEqual(patterns[0].confidence, 0.75);
        });

        test('should handle interpreter errors', async () => {
            interpreterLayer.registerInterpreter({
                id: 'error_interpreter',
                name: 'Error Interpreter',
                sensorTypes: ['performance'],
                interpret: async () => { throw new Error('Interpreter error'); },
            });

            const readings: SensorReading[] = [{
                id: 'r1',
                sensorId: 's1',
                sensorType: 'performance',
                timestamp: new Date(),
                data: {},
            }];

            // Should not throw
            const patterns = await interpreterLayer.interpretAll(readings);
            assert.ok(Array.isArray(patterns));
        });
    });

    // ============================================================================
    // Layer 3: Judgement Tests
    // ============================================================================

    suite('Layer 3 - Judgement', () => {
        let judgementLayer: JudgementLayer;

        setup(() => {
            judgementLayer = new JudgementLayer();
        });

        test('should evaluate patterns and produce judgements', async () => {
            const patterns: DiagnosticPattern[] = [{
                id: 'p1',
                patternType: 'high_cpu',
                confidence: 0.9,
                severity: 'critical',
                description: 'CPU critical',
                readings: [],
                timestamp: new Date(),
            }];

            const judgements = await judgementLayer.evaluate(patterns);
            assert.ok(judgements.length > 0);
        });

        test('should prioritize by severity', async () => {
            const patterns: DiagnosticPattern[] = [
                {
                    id: 'p1',
                    patternType: 'low_issue',
                    confidence: 0.9,
                    severity: 'info',
                    description: 'Info',
                    readings: [],
                    timestamp: new Date(),
                },
                {
                    id: 'p2',
                    patternType: 'high_issue',
                    confidence: 0.9,
                    severity: 'critical',
                    description: 'Critical',
                    readings: [],
                    timestamp: new Date(),
                },
            ];

            const judgements = await judgementLayer.evaluate(patterns);
            assert.strictEqual(judgements[0].severity, 'critical');
        });

        test('should factor in confidence', async () => {
            const patterns: DiagnosticPattern[] = [{
                id: 'p1',
                patternType: 'low_confidence',
                confidence: 0.3,
                severity: 'warning',
                description: 'Low confidence warning',
                readings: [],
                timestamp: new Date(),
            }];

            const judgements = await judgementLayer.evaluate(patterns);
            // Low confidence should affect priority
            if (judgements.length > 0) {
                assert.ok(judgements[0].priority <= 5);
            }
        });

        test('should recommend actions', async () => {
            const patterns: DiagnosticPattern[] = [{
                id: 'p1',
                patternType: 'memory_leak',
                confidence: 0.95,
                severity: 'error',
                description: 'Memory leak detected',
                readings: [],
                timestamp: new Date(),
            }];

            const judgements = await judgementLayer.evaluate(patterns);
            assert.ok(judgements[0].recommendedActions.length > 0);
        });

        test('should aggregate related patterns', async () => {
            const patterns: DiagnosticPattern[] = [
                {
                    id: 'p1',
                    patternType: 'network_slow',
                    confidence: 0.8,
                    severity: 'warning',
                    description: 'Network slow',
                    readings: [],
                    timestamp: new Date(),
                },
                {
                    id: 'p2',
                    patternType: 'network_timeout',
                    confidence: 0.7,
                    severity: 'warning',
                    description: 'Network timeout',
                    readings: [],
                    timestamp: new Date(),
                },
            ];

            const judgements = await judgementLayer.evaluate(patterns);
            // Should recognize related network issues
            assert.ok(judgements.some(j => j.affectedPatterns.length >= 1));
        });
    });

    // ============================================================================
    // Layer 4: Action Tests
    // ============================================================================

    suite('Layer 4 - Actions', () => {
        let actionLayer: ActionLayer;

        setup(() => {
            actionLayer = new ActionLayer();
        });

        test('should register actions', () => {
            actionLayer.registerAction({
                id: 'test_action',
                name: 'Test Action',
                type: 'remediation',
                execute: async () => ({ success: true }),
            });

            const actions = actionLayer.getActions();
            assert.ok(actions.some(a => a.id === 'test_action'));
        });

        test('should execute actions for judgements', async () => {
            let executed = false;

            actionLayer.registerAction({
                id: 'exec_action',
                name: 'Execute Action',
                type: 'remediation',
                execute: async () => {
                    executed = true;
                    return { success: true };
                },
            });

            const judgements: DiagnosticJudgement[] = [{
                id: 'j1',
                summary: 'Test issue',
                severity: 'error',
                priority: 8,
                affectedPatterns: [],
                recommendedActions: ['exec_action'],
                timestamp: new Date(),
            }];

            await actionLayer.executeForJudgements(judgements);
            assert.strictEqual(executed, true);
        });

        test('should report action results', async () => {
            actionLayer.registerAction({
                id: 'result_action',
                name: 'Result Action',
                type: 'remediation',
                execute: async () => ({ success: true, data: { fixed: true } }),
            });

            const judgements: DiagnosticJudgement[] = [{
                id: 'j1',
                summary: 'Test',
                severity: 'warning',
                priority: 5,
                affectedPatterns: [],
                recommendedActions: ['result_action'],
                timestamp: new Date(),
            }];

            const results = await actionLayer.executeForJudgements(judgements);
            assert.ok(results.some(r => r.success === true));
        });

        test('should handle action failures', async () => {
            actionLayer.registerAction({
                id: 'fail_action',
                name: 'Fail Action',
                type: 'remediation',
                execute: async () => { throw new Error('Action failed'); },
            });

            const judgements: DiagnosticJudgement[] = [{
                id: 'j1',
                summary: 'Test',
                severity: 'error',
                priority: 9,
                affectedPatterns: [],
                recommendedActions: ['fail_action'],
                timestamp: new Date(),
            }];

            const results = await actionLayer.executeForJudgements(judgements);
            assert.ok(results.some(r => r.success === false));
        });

        test('should respect action priorities', async () => {
            const executionOrder: string[] = [];

            actionLayer.registerAction({
                id: 'low_priority',
                name: 'Low Priority',
                type: 'notification',
                execute: async () => {
                    executionOrder.push('low');
                    return { success: true };
                },
            });

            actionLayer.registerAction({
                id: 'high_priority',
                name: 'High Priority',
                type: 'remediation',
                execute: async () => {
                    executionOrder.push('high');
                    return { success: true };
                },
            });

            const judgements: DiagnosticJudgement[] = [
                {
                    id: 'j1',
                    summary: 'Low',
                    severity: 'info',
                    priority: 2,
                    affectedPatterns: [],
                    recommendedActions: ['low_priority'],
                    timestamp: new Date(),
                },
                {
                    id: 'j2',
                    summary: 'High',
                    severity: 'critical',
                    priority: 9,
                    affectedPatterns: [],
                    recommendedActions: ['high_priority'],
                    timestamp: new Date(),
                },
            ];

            await actionLayer.executeForJudgements(judgements);
            assert.strictEqual(executionOrder[0], 'high');
        });
    });

    // ============================================================================
    // Full Pipeline Tests
    // ============================================================================

    suite('Full Diagnostic Pipeline', () => {
        test('should run complete diagnostic cycle', async () => {
            const sensorLayer = new SensorLayer();
            const interpreterLayer = new InterpreterLayer();
            const judgementLayer = new JudgementLayer();
            const actionLayer = new ActionLayer();

            // Register components
            sensorLayer.registerSensor({
                id: 'cpu_sensor',
                name: 'CPU Sensor',
                type: 'performance',
                interval: 1000,
                collect: async () => ({ cpu: 85 }),
            });

            interpreterLayer.registerInterpreter({
                id: 'cpu_interpreter',
                name: 'CPU Interpreter',
                sensorTypes: ['performance'],
                interpret: async (readings) => {
                    const cpuReadings = readings.filter(r => r.data.cpu !== undefined);
                    return cpuReadings.map(r => ({
                        id: `pattern_${r.id}`,
                        patternType: r.data.cpu > 80 ? 'high_cpu' : 'normal_cpu',
                        confidence: 0.9,
                        severity: r.data.cpu > 80 ? 'warning' as const : 'info' as const,
                        description: `CPU at ${r.data.cpu}%`,
                        readings: [r.id],
                        timestamp: new Date(),
                    }));
                },
            });

            let actionExecuted = false;
            actionLayer.registerAction({
                id: 'cpu_alert',
                name: 'CPU Alert',
                type: 'notification',
                execute: async () => {
                    actionExecuted = true;
                    return { success: true };
                },
            });

            // Run pipeline
            const readings = await sensorLayer.collectAll();
            const patterns = await interpreterLayer.interpretAll(readings);
            const judgements = await judgementLayer.evaluate(patterns);

            // Manually add action to judgement for test
            if (judgements.length > 0) {
                judgements[0].recommendedActions.push('cpu_alert');
                await actionLayer.executeForJudgements(judgements);
            }

            assert.ok(readings.length > 0);
            assert.ok(patterns.length > 0);
        });
    });
});
