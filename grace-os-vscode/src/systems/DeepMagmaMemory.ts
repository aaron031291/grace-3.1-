/**
 * Deep Magma Memory Integration
 *
 * Full integration with Grace's Magma Memory system:
 * - 4 Relation Types: Semantic, Temporal, Causal, Entity
 * - Memory consolidation
 * - Context-aware retrieval
 * - Learning integration
 */

import * as vscode from 'vscode';
import { GraceOSCore } from '../core/GraceOSCore';
import { IDEBridge } from '../bridges/IDEBridge';
import { GraceWebSocketBridge } from '../bridges/WebSocketBridge';

// ============================================================================
// Types
// ============================================================================

export interface MemoryNode {
    id: string;
    content: string;
    type: MemoryType;
    embedding?: number[];
    metadata: MemoryMetadata;
    relations: MemoryRelation[];
    trustScore: number;
    accessCount: number;
    lastAccessed: Date;
    createdAt: Date;
}

export type MemoryType =
    | 'episodic'    // Events and experiences
    | 'semantic'    // Facts and concepts
    | 'procedural'  // How-to knowledge
    | 'working'     // Short-term active memory
    | 'context';    // Current context

export interface MemoryMetadata {
    source: string;
    filePath?: string;
    language?: string;
    genesisKey?: string;
    tags: string[];
    importance: number;
}

export interface MemoryRelation {
    id: string;
    type: RelationType;
    targetId: string;
    strength: number;
    metadata?: Record<string, any>;
}

export type RelationType =
    | 'semantic'    // Conceptual similarity
    | 'temporal'    // Time-based sequence
    | 'causal'      // Cause-effect
    | 'entity';     // Shared entities

export interface RetrievalQuery {
    query: string;
    context?: string;
    memoryTypes?: MemoryType[];
    relationTypes?: RelationType[];
    minTrustScore?: number;
    limit?: number;
    useRelations?: boolean;
}

export interface RetrievalResult {
    node: MemoryNode;
    score: number;
    matchType: 'direct' | 'relational' | 'inferred';
    path?: MemoryRelation[];
}

export interface ConsolidationResult {
    merged: number;
    strengthened: number;
    decayed: number;
    newRelations: number;
}

// ============================================================================
// Deep Magma Memory
// ============================================================================

export class DeepMagmaMemory {
    private core: GraceOSCore;
    private bridge: IDEBridge;
    private wsBridge: GraceWebSocketBridge;
    private localCache: Map<string, MemoryNode> = new Map();
    private workingMemory: Map<string, MemoryNode> = new Map();
    private consolidationInterval?: NodeJS.Timeout;

    constructor(core: GraceOSCore, bridge: IDEBridge, wsBridge: GraceWebSocketBridge) {
        this.core = core;
        this.bridge = bridge;
        this.wsBridge = wsBridge;
    }

    async initialize(): Promise<void> {
        this.core.log('Initializing Deep Magma Memory...');

        // Load recent memories into local cache
        await this.loadRecentMemories();

        // Start consolidation cycle
        const config = this.core.getConfig();
        this.startConsolidationCycle(config.memory.consolidationInterval);

        // Listen for memory updates
        this.wsBridge.on('memoryUpdate', (data: any) => {
            this.handleMemoryUpdate(data);
        });

        this.core.enableFeature('deepMagmaMemory');
        this.core.log('Deep Magma Memory initialized');
    }

    private async loadRecentMemories(): Promise<void> {
        try {
            const response = await this.bridge.queryMemory({
                query: '*',
                limit: 100,
            });

            if (response.success && response.data) {
                for (const memory of response.data) {
                    this.localCache.set(memory.id, this.convertToNode(memory));
                }
            }
        } catch (error) {
            this.core.log('Failed to load recent memories', 'error');
        }
    }

    private convertToNode(data: any): MemoryNode {
        return {
            id: data.id,
            content: data.content,
            type: data.memoryType || 'semantic',
            metadata: {
                source: data.source || 'unknown',
                filePath: data.metadata?.filePath,
                language: data.metadata?.language,
                genesisKey: data.metadata?.genesisKey,
                tags: data.metadata?.tags || [],
                importance: data.metadata?.importance || 0.5,
            },
            relations: data.relations || [],
            trustScore: data.trustScore || 0.5,
            accessCount: data.accessCount || 0,
            lastAccessed: new Date(data.lastAccessed || Date.now()),
            createdAt: new Date(data.createdAt || Date.now()),
        };
    }

    private startConsolidationCycle(interval: number): void {
        this.consolidationInterval = setInterval(async () => {
            await this.consolidate();
        }, interval);
    }

    private handleMemoryUpdate(data: any): void {
        if (data.node) {
            this.localCache.set(data.node.id, this.convertToNode(data.node));
        }
    }

    // ============================================================================
    // Memory Operations
    // ============================================================================

    async store(
        content: string,
        type: MemoryType,
        metadata: Partial<MemoryMetadata> = {}
    ): Promise<MemoryNode> {
        const node: MemoryNode = {
            id: `mem_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            content,
            type,
            metadata: {
                source: metadata.source || 'vscode',
                filePath: metadata.filePath,
                language: metadata.language,
                genesisKey: metadata.genesisKey,
                tags: metadata.tags || [],
                importance: metadata.importance || 0.5,
            },
            relations: [],
            trustScore: 0.5,
            accessCount: 0,
            lastAccessed: new Date(),
            createdAt: new Date(),
        };

        // Store locally
        this.localCache.set(node.id, node);

        // If working memory, also track there
        if (type === 'working' || type === 'context') {
            this.workingMemory.set(node.id, node);
        }

        // Store to backend
        try {
            await this.bridge.storeMemory(content, type, {
                ...metadata,
                localId: node.id,
            });
        } catch (error) {
            this.core.log('Failed to store memory to backend', 'warn');
        }

        // Auto-create relations to similar memories
        await this.createAutoRelations(node);

        return node;
    }

    async retrieve(query: RetrievalQuery): Promise<RetrievalResult[]> {
        const results: RetrievalResult[] = [];

        // Query backend
        try {
            const response = await this.bridge.queryMemory({
                query: query.query,
                limit: query.limit || 10,
                memoryTypes: query.memoryTypes,
            });

            if (response.success && response.data) {
                for (const memory of response.data) {
                    const node = this.convertToNode(memory);
                    this.localCache.set(node.id, node);

                    results.push({
                        node,
                        score: memory.score || 0.5,
                        matchType: 'direct',
                    });
                }
            }
        } catch (error) {
            this.core.log('Backend query failed, using local cache', 'warn');
        }

        // Augment with local search
        const localResults = this.searchLocalCache(query);
        for (const result of localResults) {
            if (!results.find(r => r.node.id === result.node.id)) {
                results.push(result);
            }
        }

        // Apply relational retrieval if requested
        if (query.useRelations) {
            const relationalResults = await this.retrieveViaRelations(results, query);
            results.push(...relationalResults);
        }

        // Sort by score and limit
        results.sort((a, b) => b.score - a.score);
        return results.slice(0, query.limit || 10);
    }

    private searchLocalCache(query: RetrievalQuery): RetrievalResult[] {
        const results: RetrievalResult[] = [];
        const queryLower = query.query.toLowerCase();

        for (const node of this.localCache.values()) {
            // Filter by memory type
            if (query.memoryTypes && !query.memoryTypes.includes(node.type)) {
                continue;
            }

            // Filter by trust score
            if (query.minTrustScore && node.trustScore < query.minTrustScore) {
                continue;
            }

            // Simple text matching score
            const contentLower = node.content.toLowerCase();
            if (contentLower.includes(queryLower)) {
                const score = this.calculateMatchScore(queryLower, contentLower, node);
                results.push({
                    node,
                    score,
                    matchType: 'direct',
                });
            }
        }

        return results;
    }

    private calculateMatchScore(query: string, content: string, node: MemoryNode): number {
        let score = 0;

        // Exact match bonus
        if (content === query) {
            score += 1.0;
        } else if (content.startsWith(query)) {
            score += 0.8;
        } else if (content.includes(query)) {
            score += 0.5;
        }

        // Recency bonus
        const ageMs = Date.now() - node.lastAccessed.getTime();
        const ageHours = ageMs / (1000 * 60 * 60);
        score += Math.max(0, 0.2 - ageHours * 0.01);

        // Trust score factor
        score *= node.trustScore;

        // Importance factor
        score *= (0.5 + node.metadata.importance * 0.5);

        return Math.min(1.0, score);
    }

    private async retrieveViaRelations(
        directResults: RetrievalResult[],
        query: RetrievalQuery
    ): Promise<RetrievalResult[]> {
        const relationalResults: RetrievalResult[] = [];
        const seenIds = new Set(directResults.map(r => r.node.id));

        for (const result of directResults.slice(0, 5)) {
            for (const relation of result.node.relations) {
                if (seenIds.has(relation.targetId)) continue;

                // Filter by relation type
                if (query.relationTypes && !query.relationTypes.includes(relation.type)) {
                    continue;
                }

                const targetNode = this.localCache.get(relation.targetId);
                if (targetNode) {
                    relationalResults.push({
                        node: targetNode,
                        score: result.score * relation.strength * 0.8,
                        matchType: 'relational',
                        path: [relation],
                    });
                    seenIds.add(relation.targetId);
                }
            }
        }

        return relationalResults;
    }

    // ============================================================================
    // Relation Management
    // ============================================================================

    async createRelation(
        sourceId: string,
        targetId: string,
        type: RelationType,
        strength: number = 0.5
    ): Promise<MemoryRelation | null> {
        const source = this.localCache.get(sourceId);
        const target = this.localCache.get(targetId);

        if (!source || !target) {
            return null;
        }

        const relation: MemoryRelation = {
            id: `rel_${Date.now()}`,
            type,
            targetId,
            strength,
        };

        source.relations.push(relation);

        // Also create reverse relation with lower strength
        target.relations.push({
            id: `rel_${Date.now()}_rev`,
            type,
            targetId: sourceId,
            strength: strength * 0.8,
        });

        return relation;
    }

    private async createAutoRelations(node: MemoryNode): Promise<void> {
        // Find similar memories
        const similar = await this.retrieve({
            query: node.content.substring(0, 100),
            limit: 5,
            memoryTypes: [node.type],
        });

        for (const result of similar) {
            if (result.node.id === node.id) continue;
            if (result.score < 0.5) continue;

            await this.createRelation(node.id, result.node.id, 'semantic', result.score);
        }

        // Create temporal relations to recent working memory
        const recentWorking = Array.from(this.workingMemory.values())
            .filter(m => m.id !== node.id)
            .slice(-3);

        for (let i = 0; i < recentWorking.length; i++) {
            const strength = 1 - (i * 0.2);
            await this.createRelation(node.id, recentWorking[i].id, 'temporal', strength);
        }
    }

    // ============================================================================
    // Memory Consolidation
    // ============================================================================

    async consolidate(): Promise<ConsolidationResult> {
        this.core.log('Running memory consolidation...');

        const result: ConsolidationResult = {
            merged: 0,
            strengthened: 0,
            decayed: 0,
            newRelations: 0,
        };

        // Trigger backend consolidation
        try {
            await this.bridge.triggerMemoryConsolidation();
        } catch {
            this.core.log('Backend consolidation failed', 'warn');
        }

        // Local consolidation
        const now = Date.now();

        for (const node of this.localCache.values()) {
            // Decay old, unused memories
            const ageMs = now - node.lastAccessed.getTime();
            const ageHours = ageMs / (1000 * 60 * 60);

            if (ageHours > 24 && node.accessCount < 3) {
                node.trustScore *= 0.95;
                result.decayed++;
            }

            // Strengthen frequently accessed memories
            if (node.accessCount > 10) {
                node.trustScore = Math.min(1.0, node.trustScore * 1.05);
                result.strengthened++;
            }

            // Strengthen relations that were traversed
            for (const relation of node.relations) {
                if (relation.strength > 0.1) {
                    relation.strength *= 0.99; // Slight decay
                }
            }
        }

        // Clear old working memory
        const workingMemoryAge = 30 * 60 * 1000; // 30 minutes
        for (const [id, node] of this.workingMemory.entries()) {
            if (now - node.createdAt.getTime() > workingMemoryAge) {
                this.workingMemory.delete(id);
            }
        }

        this.core.log(`Consolidation complete: ${JSON.stringify(result)}`);
        return result;
    }

    // ============================================================================
    // Context Management
    // ============================================================================

    async updateContext(context: Record<string, any>): Promise<void> {
        // Store current context
        const contextNode = await this.store(
            JSON.stringify(context),
            'context',
            {
                source: 'ide_context',
                filePath: context.filePath,
                language: context.language,
                importance: 0.8,
            }
        );

        // Link to working memory
        for (const node of this.workingMemory.values()) {
            await this.createRelation(contextNode.id, node.id, 'temporal', 0.6);
        }
    }

    getWorkingMemory(): MemoryNode[] {
        return Array.from(this.workingMemory.values());
    }

    clearWorkingMemory(): void {
        this.workingMemory.clear();
    }

    // ============================================================================
    // Statistics
    // ============================================================================

    getStats(): Record<string, any> {
        const stats = {
            totalMemories: this.localCache.size,
            workingMemorySize: this.workingMemory.size,
            byType: {} as Record<string, number>,
            avgTrustScore: 0,
            totalRelations: 0,
        };

        let totalTrust = 0;

        for (const node of this.localCache.values()) {
            stats.byType[node.type] = (stats.byType[node.type] || 0) + 1;
            totalTrust += node.trustScore;
            stats.totalRelations += node.relations.length;
        }

        stats.avgTrustScore = stats.totalMemories > 0
            ? totalTrust / stats.totalMemories
            : 0;

        return stats;
    }

    dispose(): void {
        if (this.consolidationInterval) {
            clearInterval(this.consolidationInterval);
        }
    }
}
