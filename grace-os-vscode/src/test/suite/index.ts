/**
 * Grace OS VSCode Test Suite Runner
 *
 * Comprehensive test suite for all Grace systems
 */

import * as path from 'path';
import Mocha from 'mocha';
import glob from 'glob';

export function run(): Promise<void> {
    // Create the mocha test
    const mocha = new Mocha({
        ui: 'tdd',
        color: true,
        timeout: 60000, // 60 second timeout for complex tests
        slow: 5000,
        reporter: 'spec',
    });

    const testsRoot = path.resolve(__dirname, '.');

    return new Promise((resolve, reject) => {
        glob('**/*.test.js', { cwd: testsRoot }, (err, files) => {
            if (err) {
                return reject(err);
            }

            // Add files to the test suite
            files.forEach(f => mocha.addFile(path.resolve(testsRoot, f)));

            try {
                // Run the mocha test
                mocha.run(failures => {
                    if (failures > 0) {
                        reject(new Error(`${failures} tests failed.`));
                    } else {
                        resolve();
                    }
                });
            } catch (err) {
                reject(err);
            }
        });
    });
}

// Test categories for selective running
export const testCategories = {
    core: ['GraceOSCore.test.js'],
    diagnostics: ['DiagnosticMachine.test.js'],
    memory: ['DeepMagmaMemory.test.js'],
    security: ['SecurityLayer.test.js'],
    agent: ['EnterpriseAgent.test.js'],
    ai: ['NeuralSymbolicAI.test.js'],
    ingestion: ['IngestionPipeline.test.js'],
    all: [
        'GraceOSCore.test.js',
        'DiagnosticMachine.test.js',
        'DeepMagmaMemory.test.js',
        'SecurityLayer.test.js',
        'EnterpriseAgent.test.js',
        'NeuralSymbolicAI.test.js',
        'IngestionPipeline.test.js',
    ],
};

export function runCategory(category: keyof typeof testCategories): Promise<void> {
    const mocha = new Mocha({
        ui: 'tdd',
        color: true,
        timeout: 60000,
    });

    const testsRoot = path.resolve(__dirname, '.');
    const files = testCategories[category];

    files.forEach(f => {
        mocha.addFile(path.resolve(testsRoot, f));
    });

    return new Promise((resolve, reject) => {
        try {
            mocha.run(failures => {
                if (failures > 0) {
                    reject(new Error(`${failures} tests failed.`));
                } else {
                    resolve();
                }
            });
        } catch (err) {
            reject(err);
        }
    });
}
