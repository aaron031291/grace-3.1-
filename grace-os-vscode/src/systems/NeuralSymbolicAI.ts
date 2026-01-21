/**
 * Neural-Symbolic AI Reasoning Layer
 *
 * Combines neural network pattern recognition with symbolic reasoning:
 * - Symbolic rule engine
 * - Neural pattern matching
 * - Hybrid inference
 * - Explainable reasoning
 */

import * as vscode from 'vscode';
import { GraceOSCore } from '../core/GraceOSCore';
import { IDEBridge } from '../bridges/IDEBridge';

// ============================================================================
// Types
// ============================================================================

export interface SymbolicRule {
    id: string;
    name: string;
    description: string;
    condition: RuleCondition;
    action: RuleAction;
    priority: number;
    confidence: number;
    metadata?: Record<string, any>;
}

export interface RuleCondition {
    type: 'and' | 'or' | 'not' | 'predicate';
    predicates?: Predicate[];
    children?: RuleCondition[];
    predicate?: Predicate;
}

export interface Predicate {
    name: string;
    args: string[];
    operator?: '=' | '!=' | '>' | '<' | '>=' | '<=' | 'contains' | 'matches';
    value?: any;
}

export interface RuleAction {
    type: string;
    params: Record<string, any>;
}

export interface NeuralPattern {
    id: string;
    name: string;
    embedding?: number[];
    examples: string[];
    confidence: number;
    activationThreshold: number;
}

export interface InferenceResult {
    id: string;
    timestamp: Date;
    query: string;
    symbolicInferences: SymbolicInference[];
    neuralInferences: NeuralInference[];
    hybridConclusion: Conclusion;
    confidence: number;
    explanation: string[];
}

export interface SymbolicInference {
    ruleId: string;
    ruleName: string;
    conclusion: string;
    confidence: number;
    bindings: Record<string, any>;
}

export interface NeuralInference {
    patternId: string;
    patternName: string;
    similarity: number;
    matchedExample: string;
}

export interface Conclusion {
    statement: string;
    confidence: number;
    sources: Array<{ type: 'symbolic' | 'neural'; id: string; contribution: number }>;
}

// ============================================================================
// Symbolic Rule Engine
// ============================================================================

export class SymbolicRuleEngine {
    private rules: Map<string, SymbolicRule> = new Map();
    private facts: Map<string, any> = new Map();

    constructor() {
        this.loadDefaultRules();
    }

    private loadDefaultRules(): void {
        // Code quality rules
        this.addRule({
            id: 'rule_complexity',
            name: 'High Complexity Warning',
            description: 'Warns when code complexity exceeds threshold',
            condition: {
                type: 'predicate',
                predicate: { name: 'complexity', args: ['code'], operator: '>', value: 50 },
            },
            action: { type: 'warn', params: { message: 'High complexity detected' } },
            priority: 8,
            confidence: 0.9,
        });

        this.addRule({
            id: 'rule_long_function',
            name: 'Long Function Warning',
            description: 'Warns when function exceeds 50 lines',
            condition: {
                type: 'predicate',
                predicate: { name: 'lineCount', args: ['function'], operator: '>', value: 50 },
            },
            action: { type: 'suggest', params: { action: 'split_function' } },
            priority: 6,
            confidence: 0.85,
        });

        this.addRule({
            id: 'rule_missing_docs',
            name: 'Missing Documentation',
            description: 'Suggests adding documentation',
            condition: {
                type: 'and',
                children: [
                    { type: 'predicate', predicate: { name: 'isPublic', args: ['function'], operator: '=', value: true } },
                    { type: 'predicate', predicate: { name: 'hasDocstring', args: ['function'], operator: '=', value: false } },
                ],
            },
            action: { type: 'suggest', params: { action: 'add_documentation' } },
            priority: 5,
            confidence: 0.95,
        });

        this.addRule({
            id: 'rule_error_handling',
            name: 'Missing Error Handling',
            description: 'Detects async code without error handling',
            condition: {
                type: 'and',
                children: [
                    { type: 'predicate', predicate: { name: 'isAsync', args: ['code'], operator: '=', value: true } },
                    { type: 'predicate', predicate: { name: 'hasTryCatch', args: ['code'], operator: '=', value: false } },
                ],
            },
            action: { type: 'warn', params: { message: 'Consider adding error handling' } },
            priority: 7,
            confidence: 0.8,
        });

        this.addRule({
            id: 'rule_unused_import',
            name: 'Unused Import',
            description: 'Detects imports that are not used',
            condition: {
                type: 'predicate',
                predicate: { name: 'importUsed', args: ['import'], operator: '=', value: false },
            },
            action: { type: 'suggest', params: { action: 'remove_import' } },
            priority: 4,
            confidence: 0.99,
        });
    }

    addRule(rule: SymbolicRule): void {
        this.rules.set(rule.id, rule);
    }

    setFact(name: string, value: any): void {
        this.facts.set(name, value);
    }

    clearFacts(): void {
        this.facts.clear();
    }

    infer(context: Record<string, any>): SymbolicInference[] {
        const inferences: SymbolicInference[] = [];

        // Set context as facts
        for (const [key, value] of Object.entries(context)) {
            this.setFact(key, value);
        }

        // Evaluate all rules
        const sortedRules = Array.from(this.rules.values())
            .sort((a, b) => b.priority - a.priority);

        for (const rule of sortedRules) {
            const bindings: Record<string, any> = {};
            const result = this.evaluateCondition(rule.condition, bindings);

            if (result) {
                inferences.push({
                    ruleId: rule.id,
                    ruleName: rule.name,
                    conclusion: this.formatConclusion(rule, bindings),
                    confidence: rule.confidence,
                    bindings,
                });
            }
        }

        return inferences;
    }

    private evaluateCondition(condition: RuleCondition, bindings: Record<string, any>): boolean {
        switch (condition.type) {
            case 'and':
                return condition.children?.every(c => this.evaluateCondition(c, bindings)) ?? false;

            case 'or':
                return condition.children?.some(c => this.evaluateCondition(c, bindings)) ?? false;

            case 'not':
                return !this.evaluateCondition(condition.children![0], bindings);

            case 'predicate':
                return this.evaluatePredicate(condition.predicate!, bindings);

            default:
                return false;
        }
    }

    private evaluatePredicate(predicate: Predicate, bindings: Record<string, any>): boolean {
        const factValue = this.facts.get(predicate.name);
        if (factValue === undefined) return false;

        bindings[predicate.name] = factValue;

        const targetValue = predicate.value;
        const operator = predicate.operator || '=';

        switch (operator) {
            case '=':
                return factValue === targetValue;
            case '!=':
                return factValue !== targetValue;
            case '>':
                return factValue > targetValue;
            case '<':
                return factValue < targetValue;
            case '>=':
                return factValue >= targetValue;
            case '<=':
                return factValue <= targetValue;
            case 'contains':
                return String(factValue).includes(String(targetValue));
            case 'matches':
                return new RegExp(String(targetValue)).test(String(factValue));
            default:
                return false;
        }
    }

    private formatConclusion(rule: SymbolicRule, bindings: Record<string, any>): string {
        let message = rule.action.params.message || rule.action.params.action || rule.name;

        // Replace bindings in message
        for (const [key, value] of Object.entries(bindings)) {
            message = message.replace(`{${key}}`, String(value));
        }

        return message;
    }
}

// ============================================================================
// Neural Pattern Matcher
// ============================================================================

export class NeuralPatternMatcher {
    private patterns: Map<string, NeuralPattern> = new Map();

    constructor() {
        this.loadDefaultPatterns();
    }

    private loadDefaultPatterns(): void {
        // Code smell patterns
        this.addPattern({
            id: 'pattern_god_class',
            name: 'God Class',
            examples: [
                'class with more than 20 methods',
                'class handling multiple responsibilities',
                'class with many dependencies',
            ],
            confidence: 0.8,
            activationThreshold: 0.7,
        });

        this.addPattern({
            id: 'pattern_long_method',
            name: 'Long Method',
            examples: [
                'method with more than 50 lines',
                'method with many parameters',
                'method doing multiple things',
            ],
            confidence: 0.85,
            activationThreshold: 0.65,
        });

        this.addPattern({
            id: 'pattern_duplicate_code',
            name: 'Duplicate Code',
            examples: [
                'similar code blocks',
                'copy-pasted logic',
                'repeated patterns',
            ],
            confidence: 0.75,
            activationThreshold: 0.6,
        });

        this.addPattern({
            id: 'pattern_feature_envy',
            name: 'Feature Envy',
            examples: [
                'method using other class data more than own',
                'excessive calls to other object methods',
                'tight coupling between classes',
            ],
            confidence: 0.7,
            activationThreshold: 0.7,
        });
    }

    addPattern(pattern: NeuralPattern): void {
        this.patterns.set(pattern.id, pattern);
    }

    match(text: string): NeuralInference[] {
        const inferences: NeuralInference[] = [];
        const textLower = text.toLowerCase();

        for (const pattern of this.patterns.values()) {
            let maxSimilarity = 0;
            let matchedExample = '';

            for (const example of pattern.examples) {
                const similarity = this.calculateSimilarity(textLower, example.toLowerCase());
                if (similarity > maxSimilarity) {
                    maxSimilarity = similarity;
                    matchedExample = example;
                }
            }

            if (maxSimilarity >= pattern.activationThreshold) {
                inferences.push({
                    patternId: pattern.id,
                    patternName: pattern.name,
                    similarity: maxSimilarity,
                    matchedExample,
                });
            }
        }

        return inferences.sort((a, b) => b.similarity - a.similarity);
    }

    private calculateSimilarity(text1: string, text2: string): number {
        // Simple word overlap similarity
        const words1 = new Set(text1.split(/\s+/));
        const words2 = new Set(text2.split(/\s+/));

        const intersection = new Set([...words1].filter(x => words2.has(x)));
        const union = new Set([...words1, ...words2]);

        return intersection.size / union.size;
    }
}

// ============================================================================
// Neural-Symbolic AI System
// ============================================================================

export class NeuralSymbolicAI {
    private core: GraceOSCore;
    private bridge: IDEBridge;
    private symbolicEngine: SymbolicRuleEngine;
    private neuralMatcher: NeuralPatternMatcher;
    private inferenceHistory: InferenceResult[] = [];

    constructor(core: GraceOSCore, bridge: IDEBridge) {
        this.core = core;
        this.bridge = bridge;

        this.symbolicEngine = new SymbolicRuleEngine();
        this.neuralMatcher = new NeuralPatternMatcher();
    }

    async initialize(): Promise<void> {
        this.core.log('Initializing Neural-Symbolic AI...');
        this.core.enableFeature('neuralSymbolicAI');
        this.core.log('Neural-Symbolic AI initialized');
    }

    async reason(query: string, context: Record<string, any>): Promise<InferenceResult> {
        const result: InferenceResult = {
            id: `inference_${Date.now()}`,
            timestamp: new Date(),
            query,
            symbolicInferences: [],
            neuralInferences: [],
            hybridConclusion: {
                statement: '',
                confidence: 0,
                sources: [],
            },
            confidence: 0,
            explanation: [],
        };

        // Extract features for symbolic reasoning
        const symbolicContext = this.extractSymbolicFeatures(context);
        result.symbolicInferences = this.symbolicEngine.infer(symbolicContext);

        // Neural pattern matching
        const textForMatching = query + ' ' + JSON.stringify(context);
        result.neuralInferences = this.neuralMatcher.match(textForMatching);

        // Hybrid conclusion
        result.hybridConclusion = this.combineInferences(
            result.symbolicInferences,
            result.neuralInferences
        );

        result.confidence = result.hybridConclusion.confidence;
        result.explanation = this.generateExplanation(result);

        this.inferenceHistory.push(result);
        if (this.inferenceHistory.length > 100) {
            this.inferenceHistory = this.inferenceHistory.slice(-100);
        }

        return result;
    }

    private extractSymbolicFeatures(context: Record<string, any>): Record<string, any> {
        const features: Record<string, any> = {};
        const code = context.code || '';

        // Code metrics
        features.lineCount = code.split('\n').length;
        features.complexity = this.estimateComplexity(code);
        features.isAsync = code.includes('async') || code.includes('await');
        features.hasTryCatch = code.includes('try') && code.includes('catch');
        features.hasDocstring = code.includes('/**') || code.includes('"""') || code.includes("'''");
        features.isPublic = !code.includes('private') && !code.includes('_');

        // Import analysis
        const imports = code.match(/import\s+.+/g) || [];
        features.importCount = imports.length;

        // Copy context features
        for (const [key, value] of Object.entries(context)) {
            if (typeof value === 'number' || typeof value === 'boolean' || typeof value === 'string') {
                features[key] = value;
            }
        }

        return features;
    }

    private estimateComplexity(code: string): number {
        let complexity = 1;

        // Control structures
        complexity += (code.match(/if|else|for|while|switch|case/g) || []).length;

        // Logical operators
        complexity += (code.match(/&&|\|\|/g) || []).length;

        // Ternary operators
        complexity += (code.match(/\?.*:/g) || []).length;

        return complexity;
    }

    private combineInferences(
        symbolic: SymbolicInference[],
        neural: NeuralInference[]
    ): Conclusion {
        const sources: Conclusion['sources'] = [];
        const conclusions: Array<{ text: string; weight: number }> = [];

        // Add symbolic conclusions
        for (const inf of symbolic) {
            conclusions.push({
                text: inf.conclusion,
                weight: inf.confidence,
            });
            sources.push({
                type: 'symbolic',
                id: inf.ruleId,
                contribution: inf.confidence,
            });
        }

        // Add neural conclusions
        for (const inf of neural) {
            conclusions.push({
                text: `Pattern detected: ${inf.patternName}`,
                weight: inf.similarity,
            });
            sources.push({
                type: 'neural',
                id: inf.patternId,
                contribution: inf.similarity,
            });
        }

        if (conclusions.length === 0) {
            return {
                statement: 'No significant issues detected',
                confidence: 0.9,
                sources: [],
            };
        }

        // Combine conclusions by weight
        conclusions.sort((a, b) => b.weight - a.weight);
        const topConclusions = conclusions.slice(0, 3);

        const avgConfidence = topConclusions.reduce((sum, c) => sum + c.weight, 0) / topConclusions.length;

        return {
            statement: topConclusions.map(c => c.text).join('; '),
            confidence: avgConfidence,
            sources,
        };
    }

    private generateExplanation(result: InferenceResult): string[] {
        const explanation: string[] = [];

        explanation.push(`Query: "${result.query}"`);

        if (result.symbolicInferences.length > 0) {
            explanation.push(`Symbolic reasoning identified ${result.symbolicInferences.length} rule matches:`);
            for (const inf of result.symbolicInferences) {
                explanation.push(`  - ${inf.ruleName}: ${inf.conclusion} (confidence: ${(inf.confidence * 100).toFixed(0)}%)`);
            }
        }

        if (result.neuralInferences.length > 0) {
            explanation.push(`Neural pattern matching found ${result.neuralInferences.length} patterns:`);
            for (const inf of result.neuralInferences) {
                explanation.push(`  - ${inf.patternName}: similarity ${(inf.similarity * 100).toFixed(0)}%`);
            }
        }

        explanation.push(`Hybrid conclusion (${(result.confidence * 100).toFixed(0)}% confidence): ${result.hybridConclusion.statement}`);

        return explanation;
    }

    getInferenceHistory(): InferenceResult[] {
        return [...this.inferenceHistory];
    }

    addSymbolicRule(rule: SymbolicRule): void {
        this.symbolicEngine.addRule(rule);
    }

    addNeuralPattern(pattern: NeuralPattern): void {
        this.neuralMatcher.addPattern(pattern);
    }

    dispose(): void {
        // Cleanup
    }
}
