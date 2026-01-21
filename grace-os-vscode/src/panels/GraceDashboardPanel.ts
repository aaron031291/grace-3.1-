/**
 * Grace Dashboard Panel
 *
 * Unified dashboard showing Grace OS status, metrics, and quick actions.
 */

import * as vscode from 'vscode';
import { GraceOSCore } from '../core/GraceOSCore';

export class GraceDashboardPanel implements vscode.WebviewViewProvider {
    private core: GraceOSCore;
    private context: vscode.ExtensionContext;
    private webviewView?: vscode.WebviewView;

    constructor(core: GraceOSCore, context: vscode.ExtensionContext) {
        this.core = core;
        this.context = context;

        // Listen for state changes
        this.core.on('stateChanged', () => this.updateWebview());
        this.core.on('connectionChanged', () => this.updateWebview());
    }

    resolveWebviewView(
        webviewView: vscode.WebviewView,
        _context: vscode.WebviewViewResolveContext,
        _token: vscode.CancellationToken
    ): void {
        this.webviewView = webviewView;

        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this.context.extensionUri],
        };

        webviewView.webview.html = this.getHtmlContent();

        // Handle messages from webview
        webviewView.webview.onDidReceiveMessage(async (message) => {
            switch (message.command) {
                case 'runDiagnostics':
                    vscode.commands.executeCommand('graceOS.diagnostic.runCheck');
                    break;
                case 'openChat':
                    vscode.commands.executeCommand('graceOS.chat');
                    break;
                case 'queryMemory':
                    vscode.commands.executeCommand('graceOS.memory.query');
                    break;
                case 'viewHealth':
                    vscode.commands.executeCommand('graceOS.diagnostic.viewHealth');
                    break;
                case 'consolidateMemory':
                    vscode.commands.executeCommand('graceOS.magma.consolidate');
                    break;
                case 'openSettings':
                    vscode.commands.executeCommand('graceOS.settings');
                    break;
                case 'refresh':
                    this.updateWebview();
                    break;
            }
        });

        // Initial update
        this.updateWebview();
    }

    private updateWebview(): void {
        if (this.webviewView) {
            const state = this.core.getState();
            const session = this.core.getSession();
            const config = this.core.getConfig();

            this.webviewView.webview.postMessage({
                command: 'updateState',
                state: {
                    isConnected: state.isConnected,
                    healthStatus: state.healthStatus,
                    pendingTasks: state.pendingTasks,
                    activeGenesisKeys: state.activeGenesisKeys,
                    activeFeatures: Array.from(state.activeFeatures),
                    sessionId: session.id.substring(0, 8),
                    sessionStart: session.startTime.toISOString(),
                    backendUrl: config.backendUrl,
                },
            });
        }
    }

    private getHtmlContent(): string {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Grace OS Dashboard</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        body {
            font-family: var(--vscode-font-family);
            font-size: var(--vscode-font-size);
            color: var(--vscode-foreground);
            background: var(--vscode-sideBar-background);
            padding: 12px;
        }
        .header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--vscode-panel-border);
        }
        .logo {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .logo svg {
            width: 24px;
            height: 24px;
        }
        .logo h2 {
            font-size: 14px;
            font-weight: 600;
        }
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 500;
        }
        .status-badge.connected {
            background: rgba(75, 210, 143, 0.2);
            color: #4bd28f;
        }
        .status-badge.disconnected {
            background: rgba(255, 99, 71, 0.2);
            color: #ff6347;
        }
        .status-badge .dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: currentColor;
        }
        .section {
            margin-bottom: 16px;
        }
        .section-title {
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            color: var(--vscode-descriptionForeground);
            margin-bottom: 8px;
        }
        .metrics {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
        }
        .metric {
            background: var(--vscode-input-background);
            border-radius: 6px;
            padding: 12px;
            text-align: center;
        }
        .metric-value {
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 4px;
        }
        .metric-value.healthy { color: #4bd28f; }
        .metric-value.degraded { color: #ffcc00; }
        .metric-value.unhealthy { color: #ff6347; }
        .metric-value.unknown { color: var(--vscode-descriptionForeground); }
        .metric-label {
            font-size: 11px;
            color: var(--vscode-descriptionForeground);
        }
        .quick-actions {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .action-btn {
            display: flex;
            align-items: center;
            gap: 8px;
            background: var(--vscode-button-secondaryBackground);
            color: var(--vscode-button-secondaryForeground);
            border: none;
            border-radius: 4px;
            padding: 8px 12px;
            font-size: 12px;
            cursor: pointer;
            text-align: left;
            transition: background 0.1s;
        }
        .action-btn:hover {
            background: var(--vscode-button-secondaryHoverBackground);
        }
        .action-btn.primary {
            background: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
        }
        .action-btn.primary:hover {
            background: var(--vscode-button-hoverBackground);
        }
        .features {
            display: flex;
            flex-wrap: wrap;
            gap: 4px;
        }
        .feature-tag {
            background: var(--vscode-badge-background);
            color: var(--vscode-badge-foreground);
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 10px;
        }
        .session-info {
            font-size: 11px;
            color: var(--vscode-descriptionForeground);
        }
        .session-info p {
            margin-bottom: 4px;
        }
        .icon {
            width: 16px;
            height: 16px;
            opacity: 0.8;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">
            <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
            </svg>
            <h2>Grace OS</h2>
        </div>
        <div class="status-badge" id="connectionStatus">
            <span class="dot"></span>
            <span>Connecting...</span>
        </div>
    </div>

    <div class="section">
        <div class="section-title">System Status</div>
        <div class="metrics">
            <div class="metric">
                <div class="metric-value" id="healthStatus">--</div>
                <div class="metric-label">Health</div>
            </div>
            <div class="metric">
                <div class="metric-value" id="pendingTasks">0</div>
                <div class="metric-label">Tasks</div>
            </div>
            <div class="metric">
                <div class="metric-value" id="genesisKeys">0</div>
                <div class="metric-label">Genesis Keys</div>
            </div>
            <div class="metric">
                <div class="metric-value" id="activeFeatures">0</div>
                <div class="metric-label">Features</div>
            </div>
        </div>
    </div>

    <div class="section">
        <div class="section-title">Quick Actions</div>
        <div class="quick-actions">
            <button class="action-btn primary" onclick="sendCommand('openChat')">
                <svg class="icon" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/>
                </svg>
                Open Chat
            </button>
            <button class="action-btn" onclick="sendCommand('runDiagnostics')">
                <svg class="icon" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96z"/>
                </svg>
                Run Diagnostics
            </button>
            <button class="action-btn" onclick="sendCommand('queryMemory')">
                <svg class="icon" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
                </svg>
                Query Memory
            </button>
            <button class="action-btn" onclick="sendCommand('consolidateMemory')">
                <svg class="icon" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/>
                </svg>
                Consolidate Memory
            </button>
            <button class="action-btn" onclick="sendCommand('openSettings')">
                <svg class="icon" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M19.14 12.94c.04-.31.06-.63.06-.94 0-.31-.02-.63-.06-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.04.31-.06.63-.06.94s.02.63.06.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/>
                </svg>
                Settings
            </button>
        </div>
    </div>

    <div class="section">
        <div class="section-title">Active Features</div>
        <div class="features" id="featuresList">
            <span class="feature-tag">Loading...</span>
        </div>
    </div>

    <div class="section">
        <div class="section-title">Session Info</div>
        <div class="session-info">
            <p><strong>Session:</strong> <span id="sessionId">--</span></p>
            <p><strong>Started:</strong> <span id="sessionStart">--</span></p>
            <p><strong>Backend:</strong> <span id="backendUrl">--</span></p>
        </div>
    </div>

    <script>
        const vscode = acquireVsCodeApi();

        function sendCommand(command) {
            vscode.postMessage({ command });
        }

        function updateUI(state) {
            // Connection status
            const statusBadge = document.getElementById('connectionStatus');
            if (state.isConnected) {
                statusBadge.className = 'status-badge connected';
                statusBadge.innerHTML = '<span class="dot"></span><span>Connected</span>';
            } else {
                statusBadge.className = 'status-badge disconnected';
                statusBadge.innerHTML = '<span class="dot"></span><span>Disconnected</span>';
            }

            // Health status
            const healthEl = document.getElementById('healthStatus');
            healthEl.textContent = state.healthStatus.charAt(0).toUpperCase() + state.healthStatus.slice(1);
            healthEl.className = 'metric-value ' + state.healthStatus;

            // Metrics
            document.getElementById('pendingTasks').textContent = state.pendingTasks;
            document.getElementById('genesisKeys').textContent = state.activeGenesisKeys;
            document.getElementById('activeFeatures').textContent = state.activeFeatures.length;

            // Features
            const featuresEl = document.getElementById('featuresList');
            if (state.activeFeatures.length > 0) {
                featuresEl.innerHTML = state.activeFeatures
                    .map(f => '<span class="feature-tag">' + f + '</span>')
                    .join('');
            } else {
                featuresEl.innerHTML = '<span class="feature-tag">None active</span>';
            }

            // Session info
            document.getElementById('sessionId').textContent = state.sessionId + '...';
            document.getElementById('sessionStart').textContent = new Date(state.sessionStart).toLocaleString();
            document.getElementById('backendUrl').textContent = state.backendUrl;
        }

        window.addEventListener('message', event => {
            const message = event.data;
            if (message.command === 'updateState') {
                updateUI(message.state);
            }
        });
    </script>
</body>
</html>`;
    }
}
