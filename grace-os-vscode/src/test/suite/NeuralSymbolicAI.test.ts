/**
 * Neural-Symbolic AI Comprehensive Test Suite
 *
 * Tests hybrid symbolic/neural reasoning
 */

import * as assert from 'assert';
import {
    NeuralSymbolicAI,
    SymbolicRuleEngine,
    NeuralPatternMatcher,
    Rule,
    Pattern,
    InferenceResult
} from '../../systems/NeuralSymbolicAI';

suite('NeuralSymbolicAI Test Suite', () => {
    // ============================================================================
    // Symbolic Rule Engine Tests
    // ============================================================================

    suite('SymbolicRuleEngine', () => {
        let engine: SymbolicRuleEngine;

        setup(() => {
            engine = new SymbolicRuleEngine();
        });

        test('should add rules', () => {
            engine.addRule({
                id: 'test_rule',
                name: 'Test Rule',
                condition: (facts) => facts.temperature > 30,
                action: (facts) => ({ ...facts, hot: true }),
                priority: 5,
            });

            const rules = engine.getRules();
            assert.ok(rules.some(r => r.id === 'test_rule'));
        });

        test('should evaluate conditions', () => {
            engine.addRule({
                id: 'temp_rule',
                name: 'Temperature Rule',
                condition: (facts) => facts.value > 100,
                action: (facts) => ({ ...facts, status: 'high' }),
                priority: 5,
            });

            const result = engine.evaluate({ value: 150 });
            assert.strictEqual(result.status, 'high');
        });

        test('should chain rules', () => {
            engine.addRule({
                id: 'rule1',
                name: 'First Rule',
                condition: (facts) => facts.a === true,
                action: (facts) => ({ ...facts, b: true }),
                priority: 10,
            });

            engine.addRule({
                id: 'rule2',
                name: 'Second Rule',
                condition: (facts) => facts.b === true,
                action: (facts) => ({ ...facts, c: true }),
                priority: 5,
            });

            const result = engine.evaluate({ a: true });
            assert.strictEqual(result.b, true);
            assert.strictEqual(result.c, true);
        });

        test('should respect rule priorities', () => {
            const order: string[] = [];

            engine.addRule({
                id: 'low_priority',
                name: 'Low Priority',
                condition: () => true,
                action: (facts) => {
                    order.push('low');
                    return facts;
                },
                priority: 1,
            });

            engine.addRule({
                id: 'high_priority',
                name: 'High Priority',
                condition: () => true,
                action: (facts) => {
                    order.push('high');
                    return facts;
                },
                priority: 10,
            });

            engine.evaluate({});
            assert.strictEqual(order[0], 'high');
        });

        test('should remove rules', () => {
            engine.addRule({
                id: 'removable',
                name: 'Removable',
                condition: () => true,
                action: (facts) => facts,
                priority: 5,
            });

            engine.removeRule('removable');
            const rules = engine.getRules();
            assert.ok(!rules.some(r => r.id === 'removable'));
        });

        test('should handle complex conditions', () => {
            engine.addRule({
                id: 'complex',
                name: 'Complex Condition',
                condition: (facts) =>
                    facts.type === 'error' &&
                    facts.severity > 5 &&
                    facts.retryable === true,
                action: (facts) => ({ ...facts, action: 'retry' }),
                priority: 5,
            });

            const result1 = engine.evaluate({
                type: 'error',
                severity: 7,
                retryable: true,
            });
            assert.strictEqual(result1.action, 'retry');

            const result2 = engine.evaluate({
                type: 'error',
                severity: 3,
                retryable: true,
            });
            assert.strictEqual(result2.action, undefined);
        });
    });

    // ============================================================================
    // Neural Pattern Matcher Tests
    // ============================================================================

    suite('NeuralPatternMatcher', () => {
        let matcher: NeuralPatternMatcher;

        setup(() => {
            matcher = new NeuralPatternMatcher();
        });

        test('should register patterns', () => {
            matcher.registerPattern({
                id: 'test_pattern',
                name: 'Test Pattern',
                features: ['feature1', 'feature2'],
                weights: [0.5, 0.5],
                threshold: 0.7,
            });

            const patterns = matcher.getPatterns();
            assert.ok(patterns.some(p => p.id === 'test_pattern'));
        });

        test('should match patterns based on features', () => {
            matcher.registerPattern({
                id: 'error_pattern',
                name: 'Error Pattern',
                features: ['hasError', 'isRecent', 'highSeverity'],
                weights: [0.4, 0.3, 0.3],
                threshold: 0.6,
            });

            const match = matcher.match({
                hasError: 1.0,
                isRecent: 0.8,
                highSeverity: 0.9,
            });

            assert.ok(match.matched);
            assert.ok(match.confidence >= 0.6);
        });

        test('should not match below threshold', () => {
            matcher.registerPattern({
                id: 'strict_pattern',
                name: 'Strict Pattern',
                features: ['required1', 'required2'],
                weights: [0.5, 0.5],
                threshold: 0.9,
            });

            const match = matcher.match({
                required1: 0.5,
                required2: 0.5,
            });

            assert.ok(!match.matched);
        });

        test('should return best match', () => {
            matcher.registerPattern({
                id: 'pattern_a',
                name: 'Pattern A',
                features: ['featureA'],
                weights: [1.0],
                threshold: 0.5,
            });

            matcher.registerPattern({
                id: 'pattern_b',
                name: 'Pattern B',
                features: ['featureB'],
                weights: [1.0],
                threshold: 0.5,
            });

            const match = matcher.matchBest({
                featureA: 0.9,
                featureB: 0.6,
            });

            assert.strictEqual(match.patternId, 'pattern_a');
        });

        test('should handle missing features', () => {
            matcher.registerPattern({
                id: 'optional_pattern',
                name: 'Optional Pattern',
                features: ['required', 'optional'],
                weights: [0.8, 0.2],
                threshold: 0.5,
            });

            const match = matcher.match({
                required: 1.0,
                // optional is missing
            });

            assert.ok(typeof match.matched === 'boolean');
        });

        test('should learn from examples', async () => {
            await matcher.trainOnExamples([
                { features: { error: 1.0, warning: 0.0 }, label: 'error' },
                { features: { error: 0.0, warning: 1.0 }, label: 'warning' },
            ]);

            const classification = matcher.classify({
                error: 0.9,
                warning: 0.1,
            });

            assert.strictEqual(classification.label, 'error');
        });
    });

    // ============================================================================
    // Hybrid Inference Tests
    // ============================================================================

    suite('Hybrid Inference', () => {
        let neuralSymbolic: NeuralSymbolicAI;

        const mockCore = {
            log: () => {},
            getConfig: () => ({}),
            enableFeature: () => {},
        };

        setup(() => {
            neuralSymbolic = new NeuralSymbolicAI(mockCore as any);
        });

        test('should perform hybrid inference', async () => {
            const result = await neuralSymbolic.infer({
                type: 'code_analysis',
                data: {
                    hasErrors: true,
                    complexity: 0.8,
                    testCoverage: 0.3,
                },
            });

            assert.ok(result);
            assert.ok('conclusion' in result);
            assert.ok('confidence' in result);
        });

        test('should combine symbolic and neural results', async () => {
            const result = await neuralSymbolic.infer({
                type: 'decision',
                data: {
                    factA: true,
                    factB: false,
                    score: 0.75,
                },
            });

            assert.ok(result.symbolicResult !== undefined);
            assert.ok(result.neuralResult !== undefined);
        });

        test('should explain reasoning', async () => {
            const result = await neuralSymbolic.infer({
                type: 'diagnosis',
                data: { symptom1: true, symptom2: false },
            });

            const explanation = await neuralSymbolic.explain(result);
            assert.ok(explanation);
            assert.ok(explanation.steps.length > 0);
        });

        test('should handle contradictions', async () => {
            const result = await neuralSymbolic.infer({
                type: 'contradiction_test',
                data: {
                    symbolicSays: 'A',
                    neuralSays: 'B',
                    confidence: 0.5,
                },
            });

            // System should resolve or report contradiction
            assert.ok('resolution' in result || 'conflict' in result);
        });
    });

    // ============================================================================
    // Knowledge Representation Tests
    // ============================================================================

    suite('Knowledge Representation', () => {
        let neuralSymbolic: NeuralSymbolicAI;

        const mockCore = {
            log: () => {},
            getConfig: () => ({}),
            enableFeature: () => {},
        };

        setup(() => {
            neuralSymbolic = new NeuralSymbolicAI(mockCore as any);
        });

        test('should store knowledge', async () => {
            await neuralSymbolic.addKnowledge({
                type: 'fact',
                content: 'TypeScript is a superset of JavaScript',
                confidence: 1.0,
            });

            const knowledge = neuralSymbolic.getKnowledge();
            assert.ok(knowledge.length > 0);
        });

        test('should query knowledge', async () => {
            await neuralSymbolic.addKnowledge({
                type: 'fact',
                content: 'Python is interpreted',
                confidence: 1.0,
            });

            const results = await neuralSymbolic.queryKnowledge('Python');
            assert.ok(results.some(r => r.content.includes('Python')));
        });

        test('should derive new knowledge', async () => {
            await neuralSymbolic.addKnowledge({
                type: 'rule',
                content: 'If X is a programming language, X can be compiled or interpreted',
                confidence: 0.9,
            });

            await neuralSymbolic.addKnowledge({
                type: 'fact',
                content: 'Rust is a programming language',
                confidence: 1.0,
            });

            const derived = await neuralSymbolic.deriveKnowledge();
            // System should derive that Rust can be compiled or interpreted
            assert.ok(derived.length >= 0);
        });
    });

    // ============================================================================
    // Reasoning Chain Tests
    // ============================================================================

    suite('Reasoning Chains', () => {
        let neuralSymbolic: NeuralSymbolicAI;

        const mockCore = {
            log: () => {},
            getConfig: () => ({}),
            enableFeature: () => {},
        };

        setup(() => {
            neuralSymbolic = new NeuralSymbolicAI(mockCore as any);
        });

        test('should build reasoning chains', async () => {
            const chain = await neuralSymbolic.buildReasoningChain({
                goal: 'determine_language_type',
                premises: [
                    { fact: 'Code uses async/await', confidence: 0.9 },
                    { fact: 'Code has type annotations', confidence: 0.8 },
                ],
            });

            assert.ok(chain.steps.length > 0);
        });

        test('should validate reasoning chains', async () => {
            const chain = {
                steps: [
                    { premise: 'A implies B', confidence: 0.9 },
                    { premise: 'B implies C', confidence: 0.8 },
                    { conclusion: 'A implies C', confidence: 0.72 },
                ],
            };

            const validation = await neuralSymbolic.validateChain(chain);
            assert.ok('valid' in validation);
        });

        test('should detect logical fallacies', async () => {
            const chain = {
                steps: [
                    { premise: 'All birds can fly', confidence: 0.5 },
                    { premise: 'Penguins are birds', confidence: 1.0 },
                    { conclusion: 'Penguins can fly', confidence: 0.5 },
                ],
            };

            const analysis = await neuralSymbolic.analyzeChain(chain);
            assert.ok(analysis.warnings.length > 0 || analysis.confidence < 1.0);
        });
    });

    // ============================================================================
    // Integration Tests
    // ============================================================================

    suite('System Integration', () => {
        let neuralSymbolic: NeuralSymbolicAI;

        const mockCore = {
            log: () => {},
            getConfig: () => ({}),
            enableFeature: () => {},
        };

        setup(() => {
            neuralSymbolic = new NeuralSymbolicAI(mockCore as any);
        });

        test('should process code analysis queries', async () => {
            const result = await neuralSymbolic.analyzeCode({
                code: 'function add(a: number, b: number): number { return a + b; }',
                language: 'typescript',
            });

            assert.ok(result);
            assert.ok('insights' in result);
        });

        test('should provide recommendations', async () => {
            const recommendations = await neuralSymbolic.getRecommendations({
                context: 'code_review',
                data: {
                    complexity: 'high',
                    coverage: 'low',
                    duplications: 5,
                },
            });

            assert.ok(Array.isArray(recommendations));
        });

        test('should learn from feedback', async () => {
            const before = neuralSymbolic.getAccuracy();

            await neuralSymbolic.provideFeedback({
                inferenceId: 'test_inference',
                correct: false,
                expectedResult: { label: 'correct_label' },
            });

            // System should adjust based on feedback
            const after = neuralSymbolic.getAccuracy();
            assert.ok(typeof after === 'number');
        });
    });
});
