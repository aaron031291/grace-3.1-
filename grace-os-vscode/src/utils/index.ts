/**
 * Utility Functions for Grace OS VSCode Extension
 */

import * as vscode from 'vscode';
import * as crypto from 'crypto';

/**
 * Generate a unique ID
 */
export function generateId(): string {
    return crypto.randomUUID();
}

/**
 * Hash content using SHA-256
 */
export function hashContent(content: string): string {
    return crypto.createHash('sha256').update(content).digest('hex');
}

/**
 * Debounce function execution
 */
export function debounce<T extends (...args: any[]) => any>(
    func: T,
    wait: number
): (...args: Parameters<T>) => void {
    let timeout: NodeJS.Timeout | null = null;

    return (...args: Parameters<T>) => {
        if (timeout) {
            clearTimeout(timeout);
        }
        timeout = setTimeout(() => {
            func(...args);
        }, wait);
    };
}

/**
 * Throttle function execution
 */
export function throttle<T extends (...args: any[]) => any>(
    func: T,
    limit: number
): (...args: Parameters<T>) => void {
    let inThrottle = false;

    return (...args: Parameters<T>) => {
        if (!inThrottle) {
            func(...args);
            inThrottle = true;
            setTimeout(() => {
                inThrottle = false;
            }, limit);
        }
    };
}

/**
 * Get language ID from file extension
 */
export function getLanguageFromExtension(extension: string): string {
    const mapping: Record<string, string> = {
        '.js': 'javascript',
        '.jsx': 'javascriptreact',
        '.ts': 'typescript',
        '.tsx': 'typescriptreact',
        '.py': 'python',
        '.java': 'java',
        '.c': 'c',
        '.cpp': 'cpp',
        '.cs': 'csharp',
        '.go': 'go',
        '.rs': 'rust',
        '.rb': 'ruby',
        '.php': 'php',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.scala': 'scala',
        '.r': 'r',
        '.sql': 'sql',
        '.html': 'html',
        '.css': 'css',
        '.scss': 'scss',
        '.json': 'json',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.xml': 'xml',
        '.md': 'markdown',
        '.sh': 'shellscript',
        '.bash': 'shellscript',
    };

    return mapping[extension.toLowerCase()] || 'plaintext';
}

/**
 * Truncate string with ellipsis
 */
export function truncate(str: string, length: number): string {
    if (str.length <= length) return str;
    return str.substring(0, length - 3) + '...';
}

/**
 * Format bytes to human-readable size
 */
export function formatBytes(bytes: number): string {
    if (bytes === 0) return '0 B';

    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Format duration in milliseconds to human-readable string
 */
export function formatDuration(ms: number): string {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    if (ms < 3600000) return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
    return `${Math.floor(ms / 3600000)}h ${Math.floor((ms % 3600000) / 60000)}m`;
}

/**
 * Get relative time string
 */
export function getRelativeTime(date: Date): string {
    const now = new Date();
    const diff = now.getTime() - date.getTime();

    if (diff < 60000) return 'just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    if (diff < 604800000) return `${Math.floor(diff / 86400000)}d ago`;

    return date.toLocaleDateString();
}

/**
 * Extract code blocks from markdown
 */
export function extractCodeBlocks(markdown: string): Array<{ language: string; code: string }> {
    const codeBlockRegex = /```(\w*)\n([\s\S]*?)```/g;
    const blocks: Array<{ language: string; code: string }> = [];

    let match;
    while ((match = codeBlockRegex.exec(markdown)) !== null) {
        blocks.push({
            language: match[1] || 'plaintext',
            code: match[2].trim(),
        });
    }

    return blocks;
}

/**
 * Create VS Code diagnostic from Grace insight
 */
export function createDiagnostic(
    range: vscode.Range,
    message: string,
    severity: 'error' | 'warning' | 'info' | 'hint'
): vscode.Diagnostic {
    const severityMap: Record<string, vscode.DiagnosticSeverity> = {
        error: vscode.DiagnosticSeverity.Error,
        warning: vscode.DiagnosticSeverity.Warning,
        info: vscode.DiagnosticSeverity.Information,
        hint: vscode.DiagnosticSeverity.Hint,
    };

    return new vscode.Diagnostic(
        range,
        message,
        severityMap[severity] || vscode.DiagnosticSeverity.Information
    );
}

/**
 * Get workspace-relative path
 */
export function getWorkspaceRelativePath(absolutePath: string): string {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders) return absolutePath;

    for (const folder of workspaceFolders) {
        if (absolutePath.startsWith(folder.uri.fsPath)) {
            return absolutePath.substring(folder.uri.fsPath.length + 1);
        }
    }

    return absolutePath;
}

/**
 * Check if file is a code file
 */
export function isCodeFile(filePath: string): boolean {
    const codeExtensions = [
        '.js', '.jsx', '.ts', '.tsx', '.py', '.java', '.c', '.cpp',
        '.cs', '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala',
        '.r', '.sql', '.sh', '.bash', '.html', '.css', '.scss', '.vue',
        '.svelte', '.astro',
    ];

    const ext = filePath.substring(filePath.lastIndexOf('.'));
    return codeExtensions.includes(ext.toLowerCase());
}

/**
 * Parse JSON safely
 */
export function safeJsonParse<T>(str: string, defaultValue: T): T {
    try {
        return JSON.parse(str);
    } catch {
        return defaultValue;
    }
}

/**
 * Deep merge objects
 */
export function deepMerge<T extends Record<string, any>>(target: T, source: Partial<T>): T {
    const result = { ...target };

    for (const key in source) {
        if (source[key] instanceof Object && key in target && target[key] instanceof Object) {
            result[key] = deepMerge(target[key], source[key] as any);
        } else {
            result[key] = source[key] as any;
        }
    }

    return result;
}
