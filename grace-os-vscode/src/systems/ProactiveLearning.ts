/**
 * Proactive Learning System
 *
 * Autonomous learning and improvement:
 * - Pattern recognition from user behavior
 * - Automatic knowledge acquisition
 * - Continuous improvement
 * - Feedback integration
 */

import * as vscode from 'vscode';
import { GraceOSCore } from '../core/GraceOSCore';
import { IDEBridge } from '../bridges/IDEBridge';
import { DeepMagmaMemory } from './DeepMagmaMemory';

// ============================================================================
// Types
// ============================================================================

export interface LearningTask {
    id: string;
    type: LearningTaskType;
    priority: number;
    status: 'queued' | 'learning' | 'completed' | 'failed';
    data: any;
    result?: LearningResult;
    createdAt: Date;
    completedAt?: Date;
}

export type LearningTaskType =
    | 'pattern_extraction'
    | 'feedback_integration'
    | 'knowledge_acquisition'
    | 'skill_improvement'
    | 'error_learning'
    | 'preference_learning';

export interface LearningResult {
    success: boolean;
    insights: string[];
    patternsLearned: LearnedPattern[];
    knowledgeGained: KnowledgeItem[];
    confidence: number;
}

export interface LearnedPattern {
    id: string;
    name: string;
    type: string;
    frequency: number;
    confidence: number;
    triggers: string[];
    outcomes: string[];
}

export interface KnowledgeItem {
    id: string;
    content: string;
    category: string;
    source: string;
    trustScore: number;
    usageCount: number;
}

export interface UserBehavior {
    timestamp: Date;
    action: string;
    context: Record<string, any>;
    outcome?: 'positive' | 'negative' | 'neutral';
}

export interface FeedbackEvent {
    id: string;
    timestamp: Date;
    type: 'explicit' | 'implicit';
    target: string;
    rating: number; // -1 to 1
    comment?: string;
}

// ============================================================================
// Proactive Learning System
// ============================================================================

export class ProactiveLearning {
    private core: GraceOSCore;
    private bridge: IDEBridge;
    private memory?: DeepMagmaMemory;
    private taskQueue: LearningTask[] = [];
    private behaviorLog: UserBehavior[] = [];
    private feedbackLog: FeedbackEvent[] = [];
    private learnedPatterns: Map<string, LearnedPattern> = new Map();
    private knowledge: Map<string, KnowledgeItem> = new Map();
    private learningInterval?: NodeJS.Timeout;
    private isLearning: boolean = false;

    constructor(core: GraceOSCore, bridge: IDEBridge) {
        this.core = core;
        this.bridge = bridge;
    }

    setMemory(memory: DeepMagmaMemory): void {
        this.memory = memory;
    }

    async initialize(): Promise<void> {
        this.core.log('Initializing Proactive Learning...');

        // Set up behavior tracking
        this.setupBehaviorTracking();

        // Start continuous learning loop
        this.startLearningLoop();

        this.core.enableFeature('proactiveLearning');
        this.core.log('Proactive Learning initialized');
    }

    // ============================================================================
    // Behavior Tracking
    // ============================================================================

    private setupBehaviorTracking(): void {
        // Track editor changes
        vscode.workspace.onDidChangeTextDocument(event => {
            this.recordBehavior('edit', {
                filePath: event.document.uri.fsPath,
                language: event.document.languageId,
                changeCount: event.contentChanges.length,
            });
        });

        // Track file saves
        vscode.workspace.onDidSaveTextDocument(doc => {
            this.recordBehavior('save', {
                filePath: doc.uri.fsPath,
                language: doc.languageId,
            });
        });

        // Track command executions
        vscode.commands.getCommands().then(commands => {
            // Note: This doesn't actually intercept commands, just logs their availability
        });

        // Track file opens
        vscode.window.onDidChangeActiveTextEditor(editor => {
            if (editor) {
                this.recordBehavior('open_file', {
                    filePath: editor.document.uri.fsPath,
                    language: editor.document.languageId,
                });
            }
        });

        // Track selections
        vscode.window.onDidChangeTextEditorSelection(event => {
            if (!event.selections[0].isEmpty) {
                this.recordBehavior('select', {
                    filePath: event.textEditor.document.uri.fsPath,
                    selectionLength: event.selections[0].end.character - event.selections[0].start.character,
                });
            }
        });
    }

    private recordBehavior(action: string, context: Record<string, any>): void {
        const behavior: UserBehavior = {
            timestamp: new Date(),
            action,
            context,
        };

        this.behaviorLog.push(behavior);

        // Keep last 1000 behaviors
        if (this.behaviorLog.length > 1000) {
            this.behaviorLog = this.behaviorLog.slice(-1000);
        }

        // Queue pattern extraction if enough data
        if (this.behaviorLog.length % 50 === 0) {
            this.queueTask('pattern_extraction', { behaviors: this.behaviorLog.slice(-100) });
        }
    }

    // ============================================================================
    // Feedback Collection
    // ============================================================================

    recordFeedback(
        target: string,
        rating: number,
        type: 'explicit' | 'implicit' = 'explicit',
        comment?: string
    ): void {
        const feedback: FeedbackEvent = {
            id: `feedback_${Date.now()}`,
            timestamp: new Date(),
            type,
            target,
            rating: Math.max(-1, Math.min(1, rating)),
            comment,
        };

        this.feedbackLog.push(feedback);

        // Queue feedback integration
        this.queueTask('feedback_integration', { feedback });

        // Store feedback to memory
        if (this.memory) {
            this.memory.store(
                `Feedback for ${target}: ${rating > 0 ? 'positive' : rating < 0 ? 'negative' : 'neutral'}${comment ? ` - ${comment}` : ''}`,
                'learning',
                { source: 'user_feedback', target, rating }
            );
        }
    }

    recordImplicitFeedback(target: string, outcome: 'positive' | 'negative' | 'neutral'): void {
        const rating = outcome === 'positive' ? 0.5 : outcome === 'negative' ? -0.5 : 0;
        this.recordFeedback(target, rating, 'implicit');
    }

    // ============================================================================
    // Learning Task Queue
    // ============================================================================

    private queueTask(type: LearningTaskType, data: any, priority: number = 5): LearningTask {
        const task: LearningTask = {
            id: `task_${Date.now()}`,
            type,
            priority,
            status: 'queued',
            data,
            createdAt: new Date(),
        };

        this.taskQueue.push(task);
        this.taskQueue.sort((a, b) => b.priority - a.priority);

        return task;
    }

    private startLearningLoop(): void {
        this.learningInterval = setInterval(async () => {
            await this.processLearningQueue();
        }, 30000); // Every 30 seconds
    }

    private async processLearningQueue(): Promise<void> {
        if (this.isLearning || this.taskQueue.length === 0) return;

        this.isLearning = true;

        try {
            const task = this.taskQueue.find(t => t.status === 'queued');
            if (!task) return;

            task.status = 'learning';

            const result = await this.executeTask(task);
            task.result = result;
            task.status = result.success ? 'completed' : 'failed';
            task.completedAt = new Date();

            // Remove completed tasks (keep last 50)
            const completedTasks = this.taskQueue.filter(
                t => t.status === 'completed' || t.status === 'failed'
            );
            if (completedTasks.length > 50) {
                this.taskQueue = this.taskQueue.filter(
                    t => t.status === 'queued' || t.status === 'learning'
                ).concat(completedTasks.slice(-50));
            }

        } finally {
            this.isLearning = false;
        }
    }

    private async executeTask(task: LearningTask): Promise<LearningResult> {
        switch (task.type) {
            case 'pattern_extraction':
                return this.extractPatterns(task.data);
            case 'feedback_integration':
                return this.integrateFeedback(task.data);
            case 'knowledge_acquisition':
                return this.acquireKnowledge(task.data);
            case 'error_learning':
                return this.learnFromError(task.data);
            case 'preference_learning':
                return this.learnPreferences(task.data);
            default:
                return { success: false, insights: [], patternsLearned: [], knowledgeGained: [], confidence: 0 };
        }
    }

    // ============================================================================
    // Learning Algorithms
    // ============================================================================

    private async extractPatterns(data: { behaviors: UserBehavior[] }): Promise<LearningResult> {
        const patterns: LearnedPattern[] = [];
        const insights: string[] = [];

        // Group behaviors by action
        const actionGroups: Record<string, UserBehavior[]> = {};
        for (const behavior of data.behaviors) {
            if (!actionGroups[behavior.action]) {
                actionGroups[behavior.action] = [];
            }
            actionGroups[behavior.action].push(behavior);
        }

        // Analyze each action group
        for (const [action, behaviors] of Object.entries(actionGroups)) {
            if (behaviors.length >= 5) {
                // Look for common context patterns
                const contextPatterns = this.findContextPatterns(behaviors);

                for (const pattern of contextPatterns) {
                    const existingPattern = this.learnedPatterns.get(pattern.name);

                    if (existingPattern) {
                        existingPattern.frequency += pattern.frequency;
                        existingPattern.confidence = (existingPattern.confidence + pattern.confidence) / 2;
                    } else {
                        this.learnedPatterns.set(pattern.name, pattern);
                        patterns.push(pattern);
                        insights.push(`New pattern discovered: ${pattern.name}`);
                    }
                }
            }
        }

        return {
            success: true,
            insights,
            patternsLearned: patterns,
            knowledgeGained: [],
            confidence: patterns.length > 0 ? 0.7 : 0.5,
        };
    }

    private findContextPatterns(behaviors: UserBehavior[]): LearnedPattern[] {
        const patterns: LearnedPattern[] = [];

        // Extract common file types
        const languages = behaviors
            .filter(b => b.context.language)
            .map(b => b.context.language);

        const languageCounts: Record<string, number> = {};
        for (const lang of languages) {
            languageCounts[lang] = (languageCounts[lang] || 0) + 1;
        }

        for (const [lang, count] of Object.entries(languageCounts)) {
            if (count >= 3) {
                patterns.push({
                    id: `pattern_${Date.now()}_${lang}`,
                    name: `${behaviors[0].action}_${lang}_preference`,
                    type: 'language_preference',
                    frequency: count,
                    confidence: count / behaviors.length,
                    triggers: [behaviors[0].action],
                    outcomes: [lang],
                });
            }
        }

        return patterns;
    }

    private async integrateFeedback(data: { feedback: FeedbackEvent }): Promise<LearningResult> {
        const { feedback } = data;
        const insights: string[] = [];
        const knowledge: KnowledgeItem[] = [];

        // Update relevant patterns based on feedback
        for (const pattern of this.learnedPatterns.values()) {
            if (pattern.outcomes.includes(feedback.target)) {
                // Adjust confidence based on feedback
                const adjustment = feedback.rating * 0.1;
                pattern.confidence = Math.max(0, Math.min(1, pattern.confidence + adjustment));

                insights.push(`Adjusted pattern "${pattern.name}" confidence by ${(adjustment * 100).toFixed(0)}%`);
            }
        }

        // Create knowledge from feedback
        if (feedback.comment) {
            const item: KnowledgeItem = {
                id: `knowledge_${Date.now()}`,
                content: feedback.comment,
                category: 'user_feedback',
                source: 'user',
                trustScore: 0.9,
                usageCount: 0,
            };
            this.knowledge.set(item.id, item);
            knowledge.push(item);
        }

        return {
            success: true,
            insights,
            patternsLearned: [],
            knowledgeGained: knowledge,
            confidence: 0.8,
        };
    }

    private async acquireKnowledge(data: { content: string; source: string }): Promise<LearningResult> {
        const item: KnowledgeItem = {
            id: `knowledge_${Date.now()}`,
            content: data.content,
            category: 'acquired',
            source: data.source,
            trustScore: 0.6,
            usageCount: 0,
        };

        this.knowledge.set(item.id, item);

        // Store to memory
        if (this.memory) {
            await this.memory.store(data.content, 'semantic', {
                source: data.source,
                category: 'acquired_knowledge',
            });
        }

        return {
            success: true,
            insights: [`Acquired knowledge from ${data.source}`],
            patternsLearned: [],
            knowledgeGained: [item],
            confidence: 0.6,
        };
    }

    private async learnFromError(data: { error: string; context: Record<string, any> }): Promise<LearningResult> {
        const insights: string[] = [];

        // Analyze error
        const errorType = this.classifyError(data.error);
        insights.push(`Error type: ${errorType}`);

        // Create pattern to avoid this error
        const pattern: LearnedPattern = {
            id: `pattern_${Date.now()}_error`,
            name: `avoid_${errorType}`,
            type: 'error_avoidance',
            frequency: 1,
            confidence: 0.6,
            triggers: [data.error],
            outcomes: ['error'],
        };

        this.learnedPatterns.set(pattern.id, pattern);

        // Store to memory
        if (this.memory) {
            await this.memory.store(
                `Error learned: ${data.error}`,
                'episodic',
                { errorType, context: data.context }
            );
        }

        return {
            success: true,
            insights,
            patternsLearned: [pattern],
            knowledgeGained: [],
            confidence: 0.6,
        };
    }

    private classifyError(error: string): string {
        const lowerError = error.toLowerCase();

        if (lowerError.includes('syntax')) return 'syntax_error';
        if (lowerError.includes('type')) return 'type_error';
        if (lowerError.includes('reference')) return 'reference_error';
        if (lowerError.includes('network') || lowerError.includes('connection')) return 'network_error';
        if (lowerError.includes('timeout')) return 'timeout_error';
        if (lowerError.includes('permission') || lowerError.includes('access')) return 'permission_error';

        return 'unknown_error';
    }

    private async learnPreferences(data: { preferences: Record<string, any> }): Promise<LearningResult> {
        const insights: string[] = [];
        const knowledge: KnowledgeItem[] = [];

        for (const [key, value] of Object.entries(data.preferences)) {
            const item: KnowledgeItem = {
                id: `pref_${Date.now()}_${key}`,
                content: `User prefers ${key}: ${JSON.stringify(value)}`,
                category: 'preference',
                source: 'user_behavior',
                trustScore: 0.8,
                usageCount: 0,
            };

            this.knowledge.set(item.id, item);
            knowledge.push(item);
            insights.push(`Learned preference: ${key}`);
        }

        return {
            success: true,
            insights,
            patternsLearned: [],
            knowledgeGained: knowledge,
            confidence: 0.8,
        };
    }

    // ============================================================================
    // Query Interface
    // ============================================================================

    getLearnedPatterns(): LearnedPattern[] {
        return Array.from(this.learnedPatterns.values());
    }

    getKnowledge(category?: string): KnowledgeItem[] {
        const items = Array.from(this.knowledge.values());
        if (category) {
            return items.filter(i => i.category === category);
        }
        return items;
    }

    getTaskQueue(): LearningTask[] {
        return [...this.taskQueue];
    }

    getStats(): Record<string, any> {
        return {
            patternsLearned: this.learnedPatterns.size,
            knowledgeItems: this.knowledge.size,
            pendingTasks: this.taskQueue.filter(t => t.status === 'queued').length,
            behaviorsLogged: this.behaviorLog.length,
            feedbackReceived: this.feedbackLog.length,
        };
    }

    dispose(): void {
        if (this.learningInterval) {
            clearInterval(this.learningInterval);
        }
    }
}
