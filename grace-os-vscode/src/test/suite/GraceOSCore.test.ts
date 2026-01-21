/**
 * GraceOSCore Comprehensive Test Suite
 */

import * as assert from 'assert';
import * as vscode from 'vscode';
import { GraceOSCore, GraceConfig, GraceState } from '../../core/GraceOSCore';

suite('GraceOSCore Test Suite', () => {
    let core: GraceOSCore;
    let context: vscode.ExtensionContext;

    suiteSetup(async () => {
        // Wait for extension to activate
        const ext = vscode.extensions.getExtension('grace.grace-os-vscode');
        if (ext) {
            await ext.activate();
        }
    });

    setup(() => {
        // Create mock context
        context = {
            subscriptions: [],
            workspaceState: {
                get: () => undefined,
                update: async () => {},
                keys: () => [],
            },
            globalState: {
                get: () => undefined,
                update: async () => {},
                keys: () => [],
                setKeysForSync: () => {},
            },
            extensionPath: '/test/path',
            extensionUri: vscode.Uri.file('/test/path'),
            storagePath: '/test/storage',
            globalStoragePath: '/test/global',
            logPath: '/test/log',
        } as any;

        core = new GraceOSCore(context);
    });

    teardown(() => {
        core.dispose();
    });

    // ============================================================================
    // Initialization Tests
    // ============================================================================

    suite('Initialization', () => {
        test('should create instance with default config', () => {
            assert.ok(core);
            const config = core.getConfig();
            assert.ok(config);
            assert.ok(config.backend);
            assert.ok(config.features);
        });

        test('should initialize with inactive state', () => {
            const state = core.getState();
            assert.strictEqual(state.isActive, false);
            assert.strictEqual(state.pendingTasks, 0);
            assert.ok(state.activeFeatures instanceof Set);
        });

        test('should generate session ID on creation', () => {
            const state = core.getState();
            assert.ok(state.sessionId);
            assert.ok(state.sessionId.length > 0);
        });
    });

    // ============================================================================
    // Configuration Tests
    // ============================================================================

    suite('Configuration', () => {
        test('should have valid backend configuration', () => {
            const config = core.getConfig();
            assert.ok(config.backend.host);
            assert.ok(typeof config.backend.port === 'number');
        });

        test('should have all required feature flags', () => {
            const config = core.getConfig();
            assert.ok('cognitive' in config.features);
            assert.ok('autonomous' in config.features);
            assert.ok('realtime' in config.features);
        });

        test('should have diagnostics configuration', () => {
            const config = core.getConfig();
            assert.ok(config.diagnostics);
            assert.ok(typeof config.diagnostics.interval === 'number');
            assert.ok(Array.isArray(config.diagnostics.layers));
        });

        test('should have memory configuration', () => {
            const config = core.getConfig();
            assert.ok(config.memory);
            assert.ok(typeof config.memory.maxItems === 'number');
            assert.ok(typeof config.memory.consolidationInterval === 'number');
        });

        test('should update configuration', () => {
            core.updateConfig({ backend: { host: 'newhost', port: 9999 } } as any);
            const config = core.getConfig();
            assert.strictEqual(config.backend.host, 'newhost');
            assert.strictEqual(config.backend.port, 9999);
        });
    });

    // ============================================================================
    // State Management Tests
    // ============================================================================

    suite('State Management', () => {
        test('should update state correctly', () => {
            core.updateState({ isActive: true });
            const state = core.getState();
            assert.strictEqual(state.isActive, true);
        });

        test('should preserve existing state on partial update', () => {
            const originalSessionId = core.getState().sessionId;
            core.updateState({ pendingTasks: 5 });
            const state = core.getState();
            assert.strictEqual(state.sessionId, originalSessionId);
            assert.strictEqual(state.pendingTasks, 5);
        });

        test('should enable features', () => {
            core.enableFeature('testFeature');
            const state = core.getState();
            assert.ok(state.activeFeatures.has('testFeature'));
        });

        test('should disable features', () => {
            core.enableFeature('testFeature');
            core.disableFeature('testFeature');
            const state = core.getState();
            assert.ok(!state.activeFeatures.has('testFeature'));
        });

        test('should track multiple features', () => {
            core.enableFeature('feature1');
            core.enableFeature('feature2');
            core.enableFeature('feature3');
            const state = core.getState();
            assert.strictEqual(state.activeFeatures.size, 3);
        });
    });

    // ============================================================================
    // Event System Tests
    // ============================================================================

    suite('Event System', () => {
        test('should emit and receive events', (done) => {
            core.on('testEvent', (data) => {
                assert.strictEqual(data, 'testData');
                done();
            });
            core.emit('testEvent', 'testData');
        });

        test('should handle multiple listeners for same event', () => {
            let count = 0;
            core.on('multiEvent', () => count++);
            core.on('multiEvent', () => count++);
            core.emit('multiEvent', null);
            assert.strictEqual(count, 2);
        });

        test('should emit state change events', (done) => {
            core.on('stateChanged', (state) => {
                assert.strictEqual(state.isActive, true);
                done();
            });
            core.updateState({ isActive: true });
        });

        test('should remove event listeners', () => {
            let called = false;
            const handler = () => { called = true; };
            core.on('removeTest', handler);
            core.off('removeTest', handler);
            core.emit('removeTest', null);
            assert.strictEqual(called, false);
        });
    });

    // ============================================================================
    // Storage Tests
    // ============================================================================

    suite('Storage', () => {
        test('should store and retrieve data', async () => {
            await core.setStoredData('testKey', { value: 42 });
            const data = await core.getStoredData<{ value: number }>('testKey');
            assert.deepStrictEqual(data, { value: 42 });
        });

        test('should return undefined for non-existent keys', async () => {
            const data = await core.getStoredData('nonExistent');
            assert.strictEqual(data, undefined);
        });

        test('should handle complex data structures', async () => {
            const complexData = {
                array: [1, 2, 3],
                nested: { deep: { value: 'test' } },
                date: new Date().toISOString(),
            };
            await core.setStoredData('complex', complexData);
            const retrieved = await core.getStoredData<typeof complexData>('complex');
            assert.deepStrictEqual(retrieved, complexData);
        });
    });

    // ============================================================================
    // Logging Tests
    // ============================================================================

    suite('Logging', () => {
        test('should log info messages', () => {
            // Should not throw
            core.log('Test info message');
        });

        test('should log warning messages', () => {
            core.log('Test warning', 'warn');
        });

        test('should log error messages', () => {
            core.log('Test error', 'error');
        });

        test('should handle undefined messages', () => {
            core.log(undefined as any);
        });
    });

    // ============================================================================
    // Connection State Tests
    // ============================================================================

    suite('Connection State', () => {
        test('should emit connectionChanged event', (done) => {
            core.on('connectionChanged', (connected) => {
                assert.strictEqual(typeof connected, 'boolean');
                done();
            });
            core.emit('connectionChanged', true);
        });

        test('should track connection status in state', () => {
            core.updateState({ backendConnected: true, wsConnected: true });
            const state = core.getState();
            assert.strictEqual(state.backendConnected, true);
            assert.strictEqual(state.wsConnected, true);
        });
    });

    // ============================================================================
    // Cleanup Tests
    // ============================================================================

    suite('Cleanup', () => {
        test('should dispose cleanly', () => {
            const disposableCore = new GraceOSCore(context);
            assert.doesNotThrow(() => disposableCore.dispose());
        });

        test('should clear subscriptions on dispose', () => {
            const disposableCore = new GraceOSCore(context);
            disposableCore.enableFeature('test');
            disposableCore.dispose();
            // Accessing after dispose should still work but with default values
        });
    });
});
