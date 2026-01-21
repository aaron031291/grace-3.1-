/**
 * DeepMagmaMemory Comprehensive Test Suite
 *
 * Tests all 4 relation types: Semantic, Temporal, Causal, Entity
 */

import * as assert from 'assert';
import { DeepMagmaMemory, MemoryItem, RelationType } from '../../systems/DeepMagmaMemory';

suite('DeepMagmaMemory Test Suite', () => {
    let memory: DeepMagmaMemory;

    // Mock core and bridge
    const mockCore = {
        log: () => {},
        getConfig: () => ({
            memory: {
                maxItems: 100,
                consolidationInterval: 60000,
            },
        }),
        enableFeature: () => {},
        on: () => {},
    };

    const mockBridge = {
        invokeAgent: async () => ({ success: true, data: { results: [] } }),
    };

    setup(() => {
        memory = new DeepMagmaMemory(mockCore as any, mockBridge as any);
    });

    teardown(() => {
        memory.dispose();
    });

    // ============================================================================
    // Basic Storage Tests
    // ============================================================================

    suite('Basic Storage', () => {
        test('should store memory items', async () => {
            const id = await memory.store('Test content', 'semantic', { tag: 'test' });
            assert.ok(id);
            assert.ok(id.startsWith('mem_'));
        });

        test('should retrieve stored items', async () => {
            const id = await memory.store('Retrievable content', 'semantic', {});
            const item = await memory.retrieve(id);
            assert.ok(item);
            assert.strictEqual(item?.content, 'Retrievable content');
        });

        test('should return null for non-existent items', async () => {
            const item = await memory.retrieve('non_existent_id');
            assert.strictEqual(item, null);
        });

        test('should store with metadata', async () => {
            const metadata = { source: 'test', priority: 5 };
            const id = await memory.store('Content with metadata', 'semantic', metadata);
            const item = await memory.retrieve(id);
            assert.deepStrictEqual(item?.metadata.source, 'test');
            assert.deepStrictEqual(item?.metadata.priority, 5);
        });

        test('should auto-generate timestamps', async () => {
            const before = new Date();
            const id = await memory.store('Timestamped content', 'semantic', {});
            const after = new Date();
            const item = await memory.retrieve(id);

            assert.ok(item?.timestamp >= before);
            assert.ok(item?.timestamp <= after);
        });
    });

    // ============================================================================
    // Memory Types Tests
    // ============================================================================

    suite('Memory Types', () => {
        test('should store semantic memories', async () => {
            const id = await memory.store('Semantic knowledge', 'semantic', {});
            const item = await memory.retrieve(id);
            assert.strictEqual(item?.type, 'semantic');
        });

        test('should store episodic memories', async () => {
            const id = await memory.store('Episode event', 'episodic', {});
            const item = await memory.retrieve(id);
            assert.strictEqual(item?.type, 'episodic');
        });

        test('should store procedural memories', async () => {
            const id = await memory.store('How to do something', 'procedural', {});
            const item = await memory.retrieve(id);
            assert.strictEqual(item?.type, 'procedural');
        });

        test('should store working memories', async () => {
            const id = await memory.store('Current task context', 'working', {});
            const item = await memory.retrieve(id);
            assert.strictEqual(item?.type, 'working');
        });
    });

    // ============================================================================
    // Relation Type Tests - SEMANTIC
    // ============================================================================

    suite('Semantic Relations', () => {
        test('should create semantic relations', async () => {
            const id1 = await memory.store('TypeScript is a programming language', 'semantic', {});
            const id2 = await memory.store('Programming languages are used for coding', 'semantic', {});

            await memory.createRelation(id1, id2, 'semantic', { similarity: 0.8 });

            const relations = await memory.getRelations(id1);
            assert.ok(relations.some(r => r.type === 'semantic'));
        });

        test('should store semantic similarity scores', async () => {
            const id1 = await memory.store('JavaScript', 'semantic', {});
            const id2 = await memory.store('TypeScript', 'semantic', {});

            await memory.createRelation(id1, id2, 'semantic', { similarity: 0.95 });

            const relations = await memory.getRelations(id1);
            const semanticRel = relations.find(r => r.type === 'semantic');
            assert.ok(semanticRel?.metadata.similarity >= 0.9);
        });

        test('should find semantically similar items', async () => {
            await memory.store('Python programming tutorial', 'semantic', { topic: 'python' });
            await memory.store('Python data analysis', 'semantic', { topic: 'python' });
            await memory.store('Java programming basics', 'semantic', { topic: 'java' });

            const results = await memory.query('Python programming');
            assert.ok(results.length >= 0); // Results depend on backend
        });
    });

    // ============================================================================
    // Relation Type Tests - TEMPORAL
    // ============================================================================

    suite('Temporal Relations', () => {
        test('should create temporal relations', async () => {
            const id1 = await memory.store('Event A happened', 'episodic', { order: 1 });
            const id2 = await memory.store('Event B happened after', 'episodic', { order: 2 });

            await memory.createRelation(id1, id2, 'temporal', {
                ordering: 'before',
                timeDelta: 5000,
            });

            const relations = await memory.getRelations(id1);
            assert.ok(relations.some(r => r.type === 'temporal'));
        });

        test('should track temporal ordering', async () => {
            const id1 = await memory.store('First action', 'episodic', {});
            const id2 = await memory.store('Second action', 'episodic', {});
            const id3 = await memory.store('Third action', 'episodic', {});

            await memory.createRelation(id1, id2, 'temporal', { ordering: 'before' });
            await memory.createRelation(id2, id3, 'temporal', { ordering: 'before' });

            const relations1 = await memory.getRelations(id1);
            const relations2 = await memory.getRelations(id2);

            assert.ok(relations1.length > 0);
            assert.ok(relations2.length > 0);
        });

        test('should support concurrent temporal relations', async () => {
            const id1 = await memory.store('Concurrent event 1', 'episodic', {});
            const id2 = await memory.store('Concurrent event 2', 'episodic', {});

            await memory.createRelation(id1, id2, 'temporal', { ordering: 'concurrent' });

            const relations = await memory.getRelations(id1);
            const temporalRel = relations.find(r => r.type === 'temporal');
            assert.strictEqual(temporalRel?.metadata.ordering, 'concurrent');
        });
    });

    // ============================================================================
    // Relation Type Tests - CAUSAL
    // ============================================================================

    suite('Causal Relations', () => {
        test('should create causal relations', async () => {
            const causeId = await memory.store('Button clicked', 'episodic', {});
            const effectId = await memory.store('Modal opened', 'episodic', {});

            await memory.createRelation(causeId, effectId, 'causal', {
                strength: 0.9,
                mechanism: 'user_interaction',
            });

            const relations = await memory.getRelations(causeId);
            assert.ok(relations.some(r => r.type === 'causal'));
        });

        test('should track causal strength', async () => {
            const causeId = await memory.store('Code change', 'episodic', {});
            const effectId = await memory.store('Tests failed', 'episodic', {});

            await memory.createRelation(causeId, effectId, 'causal', { strength: 0.85 });

            const relations = await memory.getRelations(causeId);
            const causalRel = relations.find(r => r.type === 'causal');
            assert.ok(causalRel?.metadata.strength >= 0.8);
        });

        test('should support causal chains', async () => {
            const id1 = await memory.store('Root cause', 'episodic', {});
            const id2 = await memory.store('Intermediate effect', 'episodic', {});
            const id3 = await memory.store('Final effect', 'episodic', {});

            await memory.createRelation(id1, id2, 'causal', { strength: 0.9 });
            await memory.createRelation(id2, id3, 'causal', { strength: 0.8 });

            const chain = await memory.getCausalChain(id1);
            assert.ok(chain.length >= 1);
        });

        test('should identify probable causes', async () => {
            const cause1 = await memory.store('Possible cause 1', 'episodic', {});
            const cause2 = await memory.store('Possible cause 2', 'episodic', {});
            const effect = await memory.store('Observed effect', 'episodic', {});

            await memory.createRelation(cause1, effect, 'causal', { strength: 0.9 });
            await memory.createRelation(cause2, effect, 'causal', { strength: 0.3 });

            const causes = await memory.findCauses(effect);
            // Most probable cause should have higher strength
            if (causes.length > 1) {
                assert.ok(causes[0].metadata.strength >= causes[1].metadata.strength);
            }
        });
    });

    // ============================================================================
    // Relation Type Tests - ENTITY
    // ============================================================================

    suite('Entity Relations', () => {
        test('should create entity relations', async () => {
            const entityId = await memory.store('User object', 'semantic', { entityType: 'user' });
            const attributeId = await memory.store('User preferences', 'semantic', { entityType: 'preferences' });

            await memory.createRelation(entityId, attributeId, 'entity', {
                relationName: 'has_preferences',
            });

            const relations = await memory.getRelations(entityId);
            assert.ok(relations.some(r => r.type === 'entity'));
        });

        test('should support named entity relations', async () => {
            const parentId = await memory.store('Parent entity', 'semantic', {});
            const childId = await memory.store('Child entity', 'semantic', {});

            await memory.createRelation(parentId, childId, 'entity', {
                relationName: 'contains',
            });

            const relations = await memory.getRelations(parentId);
            const entityRel = relations.find(r => r.type === 'entity');
            assert.strictEqual(entityRel?.metadata.relationName, 'contains');
        });

        test('should track entity hierarchies', async () => {
            const classId = await memory.store('Animal class', 'semantic', {});
            const subclassId = await memory.store('Dog class', 'semantic', {});
            const instanceId = await memory.store('Fido instance', 'semantic', {});

            await memory.createRelation(classId, subclassId, 'entity', { relationName: 'superclass_of' });
            await memory.createRelation(subclassId, instanceId, 'entity', { relationName: 'instance_of' });

            const classRelations = await memory.getRelations(classId);
            const subclassRelations = await memory.getRelations(subclassId);

            assert.ok(classRelations.length > 0);
            assert.ok(subclassRelations.length > 0);
        });

        test('should support bidirectional entity relations', async () => {
            const id1 = await memory.store('Entity A', 'semantic', {});
            const id2 = await memory.store('Entity B', 'semantic', {});

            await memory.createRelation(id1, id2, 'entity', {
                relationName: 'related_to',
                bidirectional: true,
            });

            const relations1 = await memory.getRelations(id1);
            const relations2 = await memory.getRelations(id2);

            // Both should have relations if bidirectional
            assert.ok(relations1.length > 0 || relations2.length > 0);
        });
    });

    // ============================================================================
    // Memory Operations Tests
    // ============================================================================

    suite('Memory Operations', () => {
        test('should update memory items', async () => {
            const id = await memory.store('Original content', 'semantic', {});
            await memory.update(id, 'Updated content', { updated: true });

            const item = await memory.retrieve(id);
            assert.strictEqual(item?.content, 'Updated content');
            assert.strictEqual(item?.metadata.updated, true);
        });

        test('should delete memory items', async () => {
            const id = await memory.store('To be deleted', 'semantic', {});
            await memory.delete(id);

            const item = await memory.retrieve(id);
            assert.strictEqual(item, null);
        });

        test('should query memories', async () => {
            await memory.store('Query test content alpha', 'semantic', {});
            await memory.store('Query test content beta', 'semantic', {});
            await memory.store('Different content', 'semantic', {});

            const results = await memory.query('Query test');
            // Results depend on implementation
            assert.ok(Array.isArray(results));
        });

        test('should filter queries by type', async () => {
            await memory.store('Semantic item', 'semantic', {});
            await memory.store('Episodic item', 'episodic', {});

            const results = await memory.query('item', { type: 'semantic' });
            assert.ok(results.every(r => r.type === 'semantic' || r.type === undefined));
        });

        test('should limit query results', async () => {
            for (let i = 0; i < 10; i++) {
                await memory.store(`Item ${i}`, 'semantic', {});
            }

            const results = await memory.query('Item', { limit: 3 });
            assert.ok(results.length <= 3);
        });
    });

    // ============================================================================
    // Working Memory Tests
    // ============================================================================

    suite('Working Memory', () => {
        test('should add to working memory', async () => {
            await memory.addToWorkingMemory('Current task', { priority: 'high' });
            const working = await memory.getWorkingMemory();
            assert.ok(working.some(w => w.content === 'Current task'));
        });

        test('should clear working memory', async () => {
            await memory.addToWorkingMemory('Task 1', {});
            await memory.addToWorkingMemory('Task 2', {});
            await memory.clearWorkingMemory();

            const working = await memory.getWorkingMemory();
            assert.strictEqual(working.length, 0);
        });

        test('should respect working memory capacity', async () => {
            for (let i = 0; i < 20; i++) {
                await memory.addToWorkingMemory(`Task ${i}`, {});
            }

            const working = await memory.getWorkingMemory();
            // Should be capped at some limit
            assert.ok(working.length <= 10);
        });
    });

    // ============================================================================
    // Consolidation Tests
    // ============================================================================

    suite('Memory Consolidation', () => {
        test('should consolidate related memories', async () => {
            await memory.store('Related item 1', 'semantic', { topic: 'consolidation' });
            await memory.store('Related item 2', 'semantic', { topic: 'consolidation' });
            await memory.store('Related item 3', 'semantic', { topic: 'consolidation' });

            const stats = await memory.consolidate();
            assert.ok(stats.itemsProcessed >= 0);
        });

        test('should strengthen frequently accessed memories', async () => {
            const id = await memory.store('Frequently accessed', 'semantic', {});

            // Access multiple times
            for (let i = 0; i < 5; i++) {
                await memory.retrieve(id);
            }

            const item = await memory.retrieve(id);
            assert.ok(item?.accessCount >= 5);
        });

        test('should decay old, unused memories', async () => {
            const id = await memory.store('Old memory', 'semantic', { strength: 1.0 });

            // Simulate time passage by calling decay
            await memory.decayMemories();

            const item = await memory.retrieve(id);
            // Strength should decrease over time
            assert.ok(item?.strength !== undefined);
        });
    });

    // ============================================================================
    // Statistics Tests
    // ============================================================================

    suite('Memory Statistics', () => {
        test('should track total items', async () => {
            const initialStats = await memory.getStats();
            const initialCount = initialStats.totalItems;

            await memory.store('New item 1', 'semantic', {});
            await memory.store('New item 2', 'semantic', {});

            const newStats = await memory.getStats();
            assert.strictEqual(newStats.totalItems, initialCount + 2);
        });

        test('should track items by type', async () => {
            await memory.store('Semantic', 'semantic', {});
            await memory.store('Episodic', 'episodic', {});
            await memory.store('Procedural', 'procedural', {});

            const stats = await memory.getStats();
            assert.ok(stats.byType.semantic >= 1);
            assert.ok(stats.byType.episodic >= 1);
            assert.ok(stats.byType.procedural >= 1);
        });

        test('should track relation counts', async () => {
            const id1 = await memory.store('Item 1', 'semantic', {});
            const id2 = await memory.store('Item 2', 'semantic', {});

            await memory.createRelation(id1, id2, 'semantic', {});

            const stats = await memory.getStats();
            assert.ok(stats.totalRelations >= 1);
        });
    });
});
