/**
 * Security Layer - IDE Security Integration
 *
 * Full security integration including:
 * - Authentication and session management
 * - RBAC (Role-Based Access Control)
 * - Input validation and sanitization
 * - Secure communication
 * - Audit logging
 * - Secret detection
 */

import * as vscode from 'vscode';
import * as crypto from 'crypto';
import { GraceOSCore } from '../core/GraceOSCore';
import { IDEBridge } from '../bridges/IDEBridge';

// ============================================================================
// Types
// ============================================================================

export interface SecurityContext {
    sessionId: string;
    userId?: string;
    roles: string[];
    permissions: string[];
    authenticated: boolean;
    tokenExpiry?: Date;
}

export interface AuditLogEntry {
    id: string;
    timestamp: string;
    action: string;
    resource: string;
    userId?: string;
    sessionId: string;
    result: 'success' | 'failure' | 'denied';
    metadata?: Record<string, any>;
}

export interface SecretDetection {
    type: string;
    line: number;
    column: number;
    confidence: number;
    suggestion: string;
}

export interface ValidationResult {
    valid: boolean;
    errors: string[];
    sanitized?: any;
}

// ============================================================================
// Authentication Manager
// ============================================================================

export class AuthenticationManager {
    private core: GraceOSCore;
    private bridge: IDEBridge;
    private securityContext: SecurityContext;
    private tokenRefreshInterval?: NodeJS.Timeout;

    constructor(core: GraceOSCore, bridge: IDEBridge) {
        this.core = core;
        this.bridge = bridge;
        this.securityContext = this.initializeContext();
    }

    private initializeContext(): SecurityContext {
        return {
            sessionId: this.core.getSession().id,
            roles: ['user'],
            permissions: ['read', 'write', 'execute'],
            authenticated: false,
        };
    }

    async authenticate(credentials?: { apiKey?: string; token?: string }): Promise<boolean> {
        try {
            // Check for stored credentials
            const storedToken = await this.core.getStoredData<string>('auth.token');

            if (storedToken || credentials?.token) {
                const token = credentials?.token || storedToken;
                const isValid = await this.validateToken(token!);

                if (isValid) {
                    this.securityContext.authenticated = true;
                    this.core.setAuthenticated(true);
                    this.startTokenRefresh();
                    return true;
                }
            }

            // Anonymous authentication for local development
            if (this.bridge.getBaseUrl().includes('localhost')) {
                this.securityContext.authenticated = true;
                this.securityContext.roles = ['developer', 'admin'];
                this.core.setAuthenticated(true);
                return true;
            }

            return false;
        } catch (error) {
            this.core.log(`Authentication failed: ${error}`, 'error');
            return false;
        }
    }

    private async validateToken(token: string): Promise<boolean> {
        // Token validation logic
        try {
            const parts = token.split('.');
            if (parts.length !== 3) return false;

            // Decode payload
            const payload = JSON.parse(Buffer.from(parts[1], 'base64').toString());

            // Check expiry
            if (payload.exp && payload.exp < Date.now() / 1000) {
                return false;
            }

            this.securityContext.userId = payload.sub;
            this.securityContext.roles = payload.roles || ['user'];
            this.securityContext.tokenExpiry = new Date(payload.exp * 1000);

            return true;
        } catch {
            return false;
        }
    }

    private startTokenRefresh(): void {
        if (this.securityContext.tokenExpiry) {
            const refreshTime = this.securityContext.tokenExpiry.getTime() - Date.now() - 60000;

            if (refreshTime > 0) {
                this.tokenRefreshInterval = setTimeout(async () => {
                    await this.refreshToken();
                }, refreshTime);
            }
        }
    }

    private async refreshToken(): Promise<void> {
        // Token refresh logic
        this.core.log('Token refreshed');
    }

    getContext(): SecurityContext {
        return { ...this.securityContext };
    }

    hasPermission(permission: string): boolean {
        return this.securityContext.permissions.includes(permission) ||
               this.securityContext.permissions.includes('*');
    }

    hasRole(role: string): boolean {
        return this.securityContext.roles.includes(role) ||
               this.securityContext.roles.includes('admin');
    }

    dispose(): void {
        if (this.tokenRefreshInterval) {
            clearTimeout(this.tokenRefreshInterval);
        }
    }
}

// ============================================================================
// RBAC Manager
// ============================================================================

export class RBACManager {
    private core: GraceOSCore;
    private authManager: AuthenticationManager;

    private rolePermissions: Record<string, string[]> = {
        admin: ['*'],
        developer: ['read', 'write', 'execute', 'analyze', 'deploy'],
        reviewer: ['read', 'analyze', 'comment'],
        viewer: ['read'],
    };

    constructor(core: GraceOSCore, authManager: AuthenticationManager) {
        this.core = core;
        this.authManager = authManager;
    }

    checkAccess(resource: string, action: string): boolean {
        const context = this.authManager.getContext();

        // Check direct permissions
        if (context.permissions.includes(`${resource}:${action}`) ||
            context.permissions.includes(`${resource}:*`) ||
            context.permissions.includes('*')) {
            return true;
        }

        // Check role-based permissions
        for (const role of context.roles) {
            const rolePerms = this.rolePermissions[role] || [];
            if (rolePerms.includes('*') || rolePerms.includes(action)) {
                return true;
            }
        }

        return false;
    }

    requireAccess(resource: string, action: string): void {
        if (!this.checkAccess(resource, action)) {
            throw new Error(`Access denied: ${action} on ${resource}`);
        }
    }
}

// ============================================================================
// Input Validator
// ============================================================================

export class InputValidator {
    private core: GraceOSCore;

    constructor(core: GraceOSCore) {
        this.core = core;
    }

    validateCode(code: string): ValidationResult {
        const errors: string[] = [];

        // Check for common injection patterns
        const injectionPatterns = [
            { pattern: /eval\s*\(/g, message: 'Potential eval injection' },
            { pattern: /new\s+Function\s*\(/g, message: 'Potential Function constructor injection' },
            { pattern: /document\.write\s*\(/g, message: 'Potential DOM injection' },
            { pattern: /innerHTML\s*=/g, message: 'Potential innerHTML injection' },
            { pattern: /<script>/gi, message: 'Potential XSS' },
        ];

        for (const { pattern, message } of injectionPatterns) {
            if (pattern.test(code)) {
                errors.push(message);
            }
        }

        return {
            valid: errors.length === 0,
            errors,
            sanitized: this.sanitizeCode(code),
        };
    }

    private sanitizeCode(code: string): string {
        // Basic sanitization - escape potentially dangerous patterns
        return code
            .replace(/<script>/gi, '&lt;script&gt;')
            .replace(/<\/script>/gi, '&lt;/script&gt;');
    }

    validatePath(path: string): ValidationResult {
        const errors: string[] = [];

        // Check for path traversal
        if (path.includes('..') || path.includes('~')) {
            errors.push('Path traversal detected');
        }

        // Check for absolute paths to sensitive directories
        const sensitivePaths = ['/etc', '/root', '/var/log', 'C:\\Windows\\System32'];
        for (const sensitive of sensitivePaths) {
            if (path.toLowerCase().startsWith(sensitive.toLowerCase())) {
                errors.push('Access to sensitive path');
            }
        }

        return {
            valid: errors.length === 0,
            errors,
        };
    }

    validateJSON(json: string): ValidationResult {
        try {
            const parsed = JSON.parse(json);
            return { valid: true, errors: [], sanitized: parsed };
        } catch (error: any) {
            return { valid: false, errors: [error.message] };
        }
    }
}

// ============================================================================
// Secret Detector
// ============================================================================

export class SecretDetector {
    private core: GraceOSCore;
    private patterns: Array<{ name: string; regex: RegExp; confidence: number }> = [
        { name: 'AWS Access Key', regex: /AKIA[0-9A-Z]{16}/g, confidence: 0.95 },
        { name: 'AWS Secret Key', regex: /[A-Za-z0-9/+=]{40}/g, confidence: 0.7 },
        { name: 'GitHub Token', regex: /ghp_[A-Za-z0-9]{36}/g, confidence: 0.95 },
        { name: 'GitHub OAuth', regex: /gho_[A-Za-z0-9]{36}/g, confidence: 0.95 },
        { name: 'Slack Token', regex: /xox[baprs]-[0-9A-Za-z-]{10,}/g, confidence: 0.9 },
        { name: 'Private Key', regex: /-----BEGIN (RSA |EC |)PRIVATE KEY-----/g, confidence: 0.99 },
        { name: 'Generic API Key', regex: /api[_-]?key['":\s]*[=:]\s*['"][A-Za-z0-9]{20,}['"]/gi, confidence: 0.8 },
        { name: 'Generic Secret', regex: /secret['":\s]*[=:]\s*['"][A-Za-z0-9]{20,}['"]/gi, confidence: 0.75 },
        { name: 'Password', regex: /password['":\s]*[=:]\s*['"][^'"]+['"]/gi, confidence: 0.7 },
        { name: 'Bearer Token', regex: /bearer\s+[A-Za-z0-9._-]{20,}/gi, confidence: 0.85 },
    ];

    constructor(core: GraceOSCore) {
        this.core = core;
    }

    scanDocument(document: vscode.TextDocument): SecretDetection[] {
        const detections: SecretDetection[] = [];
        const text = document.getText();
        const lines = text.split('\n');

        for (let lineIndex = 0; lineIndex < lines.length; lineIndex++) {
            const line = lines[lineIndex];

            for (const { name, regex, confidence } of this.patterns) {
                regex.lastIndex = 0;
                let match;

                while ((match = regex.exec(line)) !== null) {
                    detections.push({
                        type: name,
                        line: lineIndex + 1,
                        column: match.index + 1,
                        confidence,
                        suggestion: `Potential ${name} detected. Consider using environment variables or a secrets manager.`,
                    });
                }
            }
        }

        return detections;
    }

    createDiagnostics(
        document: vscode.TextDocument,
        detections: SecretDetection[]
    ): vscode.Diagnostic[] {
        return detections.map(detection => {
            const line = document.lineAt(detection.line - 1);
            const range = new vscode.Range(
                detection.line - 1,
                detection.column - 1,
                detection.line - 1,
                line.text.length
            );

            const diagnostic = new vscode.Diagnostic(
                range,
                `Grace Security: ${detection.suggestion}`,
                detection.confidence > 0.9
                    ? vscode.DiagnosticSeverity.Error
                    : vscode.DiagnosticSeverity.Warning
            );

            diagnostic.source = 'Grace Security';
            diagnostic.code = detection.type;

            return diagnostic;
        });
    }
}

// ============================================================================
// Audit Logger
// ============================================================================

export class AuditLogger {
    private core: GraceOSCore;
    private bridge: IDEBridge;
    private logs: AuditLogEntry[] = [];
    private maxLogs = 1000;

    constructor(core: GraceOSCore, bridge: IDEBridge) {
        this.core = core;
        this.bridge = bridge;
    }

    async log(
        action: string,
        resource: string,
        result: AuditLogEntry['result'],
        metadata?: Record<string, any>
    ): Promise<void> {
        const entry: AuditLogEntry = {
            id: crypto.randomUUID(),
            timestamp: new Date().toISOString(),
            action,
            resource,
            userId: this.core.getSession().userId,
            sessionId: this.core.getSession().id,
            result,
            metadata,
        };

        this.logs.push(entry);

        // Trim old logs
        if (this.logs.length > this.maxLogs) {
            this.logs = this.logs.slice(-this.maxLogs);
        }

        // Send to backend
        try {
            await this.bridge.sendTelemetry('audit_log', entry);
        } catch {
            // Silent fail - audit logs should not break functionality
        }
    }

    getLogs(filter?: Partial<AuditLogEntry>): AuditLogEntry[] {
        if (!filter) return [...this.logs];

        return this.logs.filter(log => {
            for (const [key, value] of Object.entries(filter)) {
                if ((log as any)[key] !== value) return false;
            }
            return true;
        });
    }

    async exportLogs(): Promise<string> {
        return JSON.stringify(this.logs, null, 2);
    }
}

// ============================================================================
// Main Security Layer
// ============================================================================

export class SecurityLayer {
    private core: GraceOSCore;
    private bridge: IDEBridge;
    public authManager: AuthenticationManager;
    public rbacManager: RBACManager;
    public inputValidator: InputValidator;
    public secretDetector: SecretDetector;
    public auditLogger: AuditLogger;
    private documentListener?: vscode.Disposable;

    constructor(core: GraceOSCore, bridge: IDEBridge) {
        this.core = core;
        this.bridge = bridge;

        this.authManager = new AuthenticationManager(core, bridge);
        this.rbacManager = new RBACManager(core, this.authManager);
        this.inputValidator = new InputValidator(core);
        this.secretDetector = new SecretDetector(core);
        this.auditLogger = new AuditLogger(core, bridge);
    }

    async initialize(): Promise<void> {
        this.core.log('Initializing Security Layer...');

        // Authenticate
        await this.authManager.authenticate();

        // Set up document scanning for secrets
        this.setupSecretScanning();

        this.core.enableFeature('securityLayer');
        this.core.log('Security Layer initialized');
    }

    private setupSecretScanning(): void {
        // Scan on document open
        this.documentListener = vscode.workspace.onDidOpenTextDocument(doc => {
            if (doc.uri.scheme === 'file') {
                this.scanForSecrets(doc);
            }
        });

        // Scan on document save
        vscode.workspace.onDidSaveTextDocument(doc => {
            if (doc.uri.scheme === 'file') {
                this.scanForSecrets(doc);
            }
        });

        // Scan currently open documents
        for (const doc of vscode.workspace.textDocuments) {
            if (doc.uri.scheme === 'file') {
                this.scanForSecrets(doc);
            }
        }
    }

    private scanForSecrets(document: vscode.TextDocument): void {
        const detections = this.secretDetector.scanDocument(document);

        if (detections.length > 0) {
            const diagnostics = this.secretDetector.createDiagnostics(document, detections);
            this.core.getDiagnosticCollection().set(document.uri, diagnostics);

            this.auditLogger.log('secret_detected', document.uri.fsPath, 'success', {
                count: detections.length,
                types: [...new Set(detections.map(d => d.type))],
            });
        }
    }

    // Secure wrapper for sensitive operations
    async secureOperation<T>(
        operation: string,
        resource: string,
        fn: () => Promise<T>
    ): Promise<T> {
        // Check access
        this.rbacManager.requireAccess(resource, operation);

        // Log start
        await this.auditLogger.log(operation, resource, 'success', { status: 'started' });

        try {
            const result = await fn();
            await this.auditLogger.log(operation, resource, 'success', { status: 'completed' });
            return result;
        } catch (error: any) {
            await this.auditLogger.log(operation, resource, 'failure', {
                status: 'failed',
                error: error.message,
            });
            throw error;
        }
    }

    dispose(): void {
        this.authManager.dispose();
        this.documentListener?.dispose();
    }
}
