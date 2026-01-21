/**
 * Oracle & ML Intelligence System
 *
 * Predictive analysis and machine learning integration:
 * - Prediction engine
 * - Pattern learning
 * - Anomaly detection
 * - Neural trust scoring
 * - Bandit optimization
 */

import * as vscode from 'vscode';
import { GraceOSCore } from '../core/GraceOSCore';
import { IDEBridge } from '../bridges/IDEBridge';

// ============================================================================
// Types
// ============================================================================

export interface Prediction {
    id: string;
    timestamp: Date;
    type: PredictionType;
    target: string;
    prediction: any;
    confidence: number;
    reasoning: string;
    actualOutcome?: any;
    accuracy?: number;
}

export type PredictionType =
    | 'code_completion'
    | 'error_occurrence'
    | 'user_action'
    | 'performance'
    | 'complexity'
    | 'bug_likelihood';

export interface Pattern {
    id: string;
    name: string;
    description: string;
    frequency: number;
    confidence: number;
    triggers: string[];
    outcomes: string[];
    lastSeen: Date;
}

export interface Anomaly {
    id: string;
    timestamp: Date;
    type: string;
    severity: 'low' | 'medium' | 'high' | 'critical';
    description: string;
    context: Record<string, any>;
    recommended_action: string;
}

export interface TrustScore {
    entity: string;
    score: number;
    history: TrustEvent[];
    factors: Record<string, number>;
}

export interface TrustEvent {
    timestamp: Date;
    action: string;
    outcome: 'positive' | 'negative' | 'neutral';
    impact: number;
}

export interface BanditArm {
    id: string;
    name: string;
    pulls: number;
    rewards: number;
    avgReward: number;
    ucbScore: number;
}

// ============================================================================
// Oracle Prediction Engine
// ============================================================================

export class OraclePredictionEngine {
    private core: GraceOSCore;
    private bridge: IDEBridge;
    private predictions: Map<string, Prediction> = new Map();
    private patterns: Map<string, Pattern> = new Map();

    constructor(core: GraceOSCore, bridge: IDEBridge) {
        this.core = core;
        this.bridge = bridge;
    }

    async predict(
        type: PredictionType,
        target: string,
        context: Record<string, any>
    ): Promise<Prediction> {
        const prediction: Prediction = {
            id: `pred_${Date.now()}`,
            timestamp: new Date(),
            type,
            target,
            prediction: null,
            confidence: 0,
            reasoning: '',
        };

        try {
            // Try backend prediction
            const response = await this.bridge.invokeAgent('predict', {
                type,
                target,
                context,
            });

            if (response.success && response.data) {
                prediction.prediction = response.data.prediction;
                prediction.confidence = response.data.confidence;
                prediction.reasoning = response.data.reasoning;
            } else {
                // Local prediction
                const localPrediction = await this.localPredict(type, target, context);
                prediction.prediction = localPrediction.prediction;
                prediction.confidence = localPrediction.confidence;
                prediction.reasoning = localPrediction.reasoning;
            }
        } catch {
            const localPrediction = await this.localPredict(type, target, context);
            prediction.prediction = localPrediction.prediction;
            prediction.confidence = localPrediction.confidence;
            prediction.reasoning = localPrediction.reasoning;
        }

        this.predictions.set(prediction.id, prediction);
        return prediction;
    }

    private async localPredict(
        type: PredictionType,
        target: string,
        context: Record<string, any>
    ): Promise<{ prediction: any; confidence: number; reasoning: string }> {
        switch (type) {
            case 'error_occurrence':
                return this.predictErrorOccurrence(context);
            case 'complexity':
                return this.predictComplexity(context);
            case 'bug_likelihood':
                return this.predictBugLikelihood(context);
            case 'user_action':
                return this.predictUserAction(context);
            default:
                return {
                    prediction: null,
                    confidence: 0.5,
                    reasoning: 'Default prediction',
                };
        }
    }

    private predictErrorOccurrence(context: Record<string, any>): {
        prediction: any;
        confidence: number;
        reasoning: string;
    } {
        const code = context.code || '';
        const complexity = this.estimateComplexity(code);

        // Heuristic: more complex code = higher error likelihood
        const errorLikelihood = Math.min(0.9, complexity / 100);

        return {
            prediction: { likelihood: errorLikelihood },
            confidence: 0.7,
            reasoning: `Based on code complexity (${complexity.toFixed(0)}/100)`,
        };
    }

    private predictComplexity(context: Record<string, any>): {
        prediction: any;
        confidence: number;
        reasoning: string;
    } {
        const code = context.code || '';
        const complexity = this.estimateComplexity(code);

        return {
            prediction: {
                score: complexity,
                level: complexity < 30 ? 'low' : complexity < 60 ? 'medium' : 'high',
            },
            confidence: 0.85,
            reasoning: 'Based on cyclomatic complexity indicators',
        };
    }

    private predictBugLikelihood(context: Record<string, any>): {
        prediction: any;
        confidence: number;
        reasoning: string;
    } {
        const code = context.code || '';
        const factors: Record<string, number> = {};

        // Check for common bug patterns
        factors.todoComments = (code.match(/TODO|FIXME|HACK/g) || []).length * 0.1;
        factors.magicNumbers = (code.match(/[^0-9][0-9]{3,}[^0-9]/g) || []).length * 0.05;
        factors.longFunctions = code.length > 500 ? 0.15 : 0;
        factors.deepNesting = (code.match(/\{/g) || []).length > 10 ? 0.1 : 0;
        factors.noErrorHandling = !code.includes('catch') && !code.includes('error') ? 0.1 : 0;

        const totalLikelihood = Math.min(0.9, Object.values(factors).reduce((a, b) => a + b, 0));

        return {
            prediction: {
                likelihood: totalLikelihood,
                factors,
            },
            confidence: 0.65,
            reasoning: `Based on ${Object.keys(factors).filter(k => factors[k] > 0).length} risk factors`,
        };
    }

    private predictUserAction(context: Record<string, any>): {
        prediction: any;
        confidence: number;
        reasoning: string;
    } {
        const recentActions = context.recentActions || [];
        const currentState = context.currentState || {};

        // Simple markov-like prediction based on recent actions
        const actionPatterns: Record<string, string> = {
            'edit': 'save',
            'save': 'run',
            'run': 'debug',
            'debug': 'edit',
            'open': 'edit',
        };

        const lastAction = recentActions[recentActions.length - 1];
        const predictedAction = actionPatterns[lastAction] || 'edit';

        return {
            prediction: { action: predictedAction },
            confidence: 0.6,
            reasoning: `Based on common action sequence after "${lastAction}"`,
        };
    }

    private estimateComplexity(code: string): number {
        let complexity = 0;

        // Line count
        complexity += Math.min(30, code.split('\n').length * 0.3);

        // Control structures
        complexity += (code.match(/if|else|for|while|switch|case/g) || []).length * 2;

        // Nesting depth
        let maxDepth = 0;
        let currentDepth = 0;
        for (const char of code) {
            if (char === '{') {
                currentDepth++;
                maxDepth = Math.max(maxDepth, currentDepth);
            } else if (char === '}') {
                currentDepth--;
            }
        }
        complexity += maxDepth * 5;

        // Function calls
        complexity += (code.match(/\w+\s*\(/g) || []).length * 0.5;

        return Math.min(100, complexity);
    }

    recordOutcome(predictionId: string, actualOutcome: any): void {
        const prediction = this.predictions.get(predictionId);
        if (prediction) {
            prediction.actualOutcome = actualOutcome;
            prediction.accuracy = this.calculateAccuracy(prediction.prediction, actualOutcome);
        }
    }

    private calculateAccuracy(predicted: any, actual: any): number {
        if (typeof predicted === 'object' && typeof actual === 'object') {
            // Compare object properties
            let matches = 0;
            let total = 0;
            for (const key of Object.keys(predicted)) {
                total++;
                if (predicted[key] === actual[key]) matches++;
            }
            return total > 0 ? matches / total : 0;
        }
        return predicted === actual ? 1 : 0;
    }
}

// ============================================================================
// Neural Trust Scoring
// ============================================================================

export class NeuralTrustScorer {
    private core: GraceOSCore;
    private trustScores: Map<string, TrustScore> = new Map();

    constructor(core: GraceOSCore) {
        this.core = core;
    }

    getScore(entity: string): number {
        const score = this.trustScores.get(entity);
        return score?.score || 0.5; // Default neutral trust
    }

    updateScore(entity: string, event: Omit<TrustEvent, 'timestamp'>): number {
        let trustScore = this.trustScores.get(entity);

        if (!trustScore) {
            trustScore = {
                entity,
                score: 0.5,
                history: [],
                factors: {},
            };
            this.trustScores.set(entity, trustScore);
        }

        const fullEvent: TrustEvent = {
            ...event,
            timestamp: new Date(),
        };

        trustScore.history.push(fullEvent);

        // Keep only last 100 events
        if (trustScore.history.length > 100) {
            trustScore.history = trustScore.history.slice(-100);
        }

        // Update score using exponential moving average
        const alpha = 0.1;
        const eventScore = event.outcome === 'positive' ? 1 :
                          event.outcome === 'negative' ? 0 : 0.5;

        trustScore.score = trustScore.score * (1 - alpha) + eventScore * alpha;

        // Update factors
        trustScore.factors[event.action] = eventScore;

        return trustScore.score;
    }

    getHistory(entity: string): TrustEvent[] {
        return this.trustScores.get(entity)?.history || [];
    }

    getAllScores(): Array<{ entity: string; score: number }> {
        return Array.from(this.trustScores.entries()).map(([entity, ts]) => ({
            entity,
            score: ts.score,
        }));
    }
}

// ============================================================================
// Multi-Armed Bandit Optimizer
// ============================================================================

export class BanditOptimizer {
    private core: GraceOSCore;
    private arms: Map<string, BanditArm> = new Map();
    private totalPulls: number = 0;

    constructor(core: GraceOSCore) {
        this.core = core;
    }

    registerArm(id: string, name: string): void {
        this.arms.set(id, {
            id,
            name,
            pulls: 0,
            rewards: 0,
            avgReward: 0,
            ucbScore: Infinity, // Start with infinite to ensure exploration
        });
    }

    selectArm(): BanditArm | null {
        if (this.arms.size === 0) return null;

        this.updateUCBScores();

        // Select arm with highest UCB score
        let bestArm: BanditArm | null = null;
        let bestScore = -Infinity;

        for (const arm of this.arms.values()) {
            if (arm.ucbScore > bestScore) {
                bestScore = arm.ucbScore;
                bestArm = arm;
            }
        }

        return bestArm;
    }

    recordReward(armId: string, reward: number): void {
        const arm = this.arms.get(armId);
        if (!arm) return;

        arm.pulls++;
        arm.rewards += reward;
        arm.avgReward = arm.rewards / arm.pulls;
        this.totalPulls++;
    }

    private updateUCBScores(): void {
        for (const arm of this.arms.values()) {
            if (arm.pulls === 0) {
                arm.ucbScore = Infinity;
            } else {
                // UCB1 formula
                const exploration = Math.sqrt(2 * Math.log(this.totalPulls) / arm.pulls);
                arm.ucbScore = arm.avgReward + exploration;
            }
        }
    }

    getStats(): BanditArm[] {
        return Array.from(this.arms.values());
    }
}

// ============================================================================
// Anomaly Detector
// ============================================================================

export class AnomalyDetector {
    private core: GraceOSCore;
    private baseline: Map<string, number[]> = new Map();
    private anomalies: Anomaly[] = [];

    constructor(core: GraceOSCore) {
        this.core = core;
    }

    recordMetric(name: string, value: number): Anomaly | null {
        let history = this.baseline.get(name);
        if (!history) {
            history = [];
            this.baseline.set(name, history);
        }

        history.push(value);

        // Keep last 100 values
        if (history.length > 100) {
            history.shift();
        }

        // Check for anomaly if we have enough data
        if (history.length >= 10) {
            const anomaly = this.detectAnomaly(name, value, history);
            if (anomaly) {
                this.anomalies.push(anomaly);
                return anomaly;
            }
        }

        return null;
    }

    private detectAnomaly(name: string, value: number, history: number[]): Anomaly | null {
        const mean = history.reduce((a, b) => a + b, 0) / history.length;
        const stdDev = Math.sqrt(
            history.reduce((sq, n) => sq + Math.pow(n - mean, 2), 0) / history.length
        );

        // Z-score based anomaly detection
        const zScore = (value - mean) / (stdDev || 1);

        if (Math.abs(zScore) > 3) {
            const severity = Math.abs(zScore) > 5 ? 'critical' :
                            Math.abs(zScore) > 4 ? 'high' : 'medium';

            return {
                id: `anomaly_${Date.now()}`,
                timestamp: new Date(),
                type: name,
                severity,
                description: `Unusual ${name}: ${value.toFixed(2)} (z-score: ${zScore.toFixed(2)})`,
                context: { value, mean, stdDev, zScore },
                recommended_action: `Investigate ${name} spike`,
            };
        }

        return null;
    }

    getAnomalies(limit: number = 10): Anomaly[] {
        return this.anomalies.slice(-limit);
    }
}

// ============================================================================
// Main Oracle ML Intelligence System
// ============================================================================

export class OracleMLIntelligence {
    private core: GraceOSCore;
    private bridge: IDEBridge;
    public predictionEngine: OraclePredictionEngine;
    public trustScorer: NeuralTrustScorer;
    public banditOptimizer: BanditOptimizer;
    public anomalyDetector: AnomalyDetector;

    constructor(core: GraceOSCore, bridge: IDEBridge) {
        this.core = core;
        this.bridge = bridge;

        this.predictionEngine = new OraclePredictionEngine(core, bridge);
        this.trustScorer = new NeuralTrustScorer(core);
        this.banditOptimizer = new BanditOptimizer(core);
        this.anomalyDetector = new AnomalyDetector(core);
    }

    async initialize(): Promise<void> {
        this.core.log('Initializing Oracle ML Intelligence...');

        // Register default bandit arms for strategy selection
        this.banditOptimizer.registerArm('aggressive', 'Aggressive suggestions');
        this.banditOptimizer.registerArm('conservative', 'Conservative suggestions');
        this.banditOptimizer.registerArm('balanced', 'Balanced approach');

        this.core.enableFeature('oracleMLIntelligence');
        this.core.log('Oracle ML Intelligence initialized');
    }

    async predictAndAct(context: Record<string, any>): Promise<void> {
        // Get prediction for likely user needs
        const prediction = await this.predictionEngine.predict(
            'user_action',
            'next_action',
            context
        );

        // Select strategy using bandit
        const strategy = this.banditOptimizer.selectArm();

        if (prediction.confidence > 0.7 && strategy) {
            this.core.log(`High confidence prediction: ${JSON.stringify(prediction.prediction)}`);
            // Could trigger proactive assistance here
        }
    }

    recordInteractionOutcome(
        entity: string,
        action: string,
        outcome: 'positive' | 'negative' | 'neutral'
    ): void {
        this.trustScorer.updateScore(entity, {
            action,
            outcome,
            impact: outcome === 'positive' ? 1 : outcome === 'negative' ? -1 : 0,
        });
    }

    dispose(): void {
        // Cleanup
    }
}
