/**
 * Grace Chat Panel
 *
 * Interactive chat interface for communicating with Grace
 * directly within VSCode.
 */

import * as vscode from 'vscode';
import { GraceOSCore } from '../core/GraceOSCore';
import { GraceWebSocketBridge, StreamChunk } from '../bridges/WebSocketBridge';

export class GraceChatPanel implements vscode.WebviewViewProvider {
    private core: GraceOSCore;
    private context: vscode.ExtensionContext;
    private wsBridge: GraceWebSocketBridge;
    private webviewView?: vscode.WebviewView;
    private messages: Array<{ role: string; content: string; timestamp: Date }> = [];

    constructor(
        core: GraceOSCore,
        context: vscode.ExtensionContext,
        wsBridge: GraceWebSocketBridge
    ) {
        this.core = core;
        this.context = context;
        this.wsBridge = wsBridge;

        // Listen for streaming responses
        this.wsBridge.on('streamChunk', (chunk: StreamChunk) => {
            this.handleStreamChunk(chunk);
        });

        this.wsBridge.on('streamEnd', (data: any) => {
            this.handleStreamEnd(data);
        });
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
                case 'sendMessage':
                    await this.handleUserMessage(message.text);
                    break;
                case 'clear':
                    this.messages = [];
                    this.updateWebview();
                    break;
                case 'insertCode':
                    this.insertCodeInEditor(message.code);
                    break;
            }
        });

        // Update webview with existing messages
        this.updateWebview();
    }

    private async handleUserMessage(text: string): Promise<void> {
        // Add user message
        this.messages.push({
            role: 'user',
            content: text,
            timestamp: new Date(),
        });
        this.updateWebview();

        // Get context from current editor
        const editor = vscode.window.activeTextEditor;
        const context: Record<string, any> = {};

        if (editor) {
            context.filePath = editor.document.uri.fsPath;
            context.language = editor.document.languageId;
            context.selection = editor.document.getText(editor.selection);

            // Get surrounding context
            const cursorLine = editor.selection.active.line;
            const startLine = Math.max(0, cursorLine - 10);
            const endLine = Math.min(editor.document.lineCount - 1, cursorLine + 10);
            context.surroundingCode = editor.document.getText(
                new vscode.Range(startLine, 0, endLine, editor.document.lineAt(endLine).text.length)
            );
        }

        // Add placeholder for assistant response
        this.messages.push({
            role: 'assistant',
            content: '',
            timestamp: new Date(),
        });
        this.updateWebview();

        // Send via WebSocket for streaming, with HTTP fallback
        if (this.wsBridge.isConnected()) {
            this.wsBridge.sendChatMessage(text, context);
        } else {
            // HTTP fallback
            try {
                const config = this.core.getConfig();
                const axios = require('axios');
                const response = await axios.post(`${config.backendUrl}/api/chat`, {
                    message: text,
                    context,
                    session_id: this.core.getSession().id,
                });
                const lastMessage = this.messages[this.messages.length - 1];
                if (lastMessage && lastMessage.role === 'assistant') {
                    lastMessage.content = response.data?.content || response.data || 'No response';
                    this.updateWebview();
                }
            } catch (err: any) {
                const lastMessage = this.messages[this.messages.length - 1];
                if (lastMessage && lastMessage.role === 'assistant') {
                    lastMessage.content = `Connection error: ${err.message}. Check that Grace backend is running.`;
                    this.updateWebview();
                }
            }
        }
    }

    private handleStreamChunk(chunk: StreamChunk): void {
        // Append to last assistant message
        const lastMessage = this.messages[this.messages.length - 1];
        if (lastMessage && lastMessage.role === 'assistant') {
            lastMessage.content += chunk.content;
            this.updateWebview();
        }
    }

    private handleStreamEnd(data: any): void {
        // Finalize the message
        const lastMessage = this.messages[this.messages.length - 1];
        if (lastMessage && lastMessage.role === 'assistant') {
            // Store to memory if significant
            if (lastMessage.content.length > 100) {
                this.core.emit('chatMessageCompleted', {
                    query: this.messages[this.messages.length - 2]?.content,
                    response: lastMessage.content,
                });
            }
        }
    }

    private insertCodeInEditor(code: string): void {
        const editor = vscode.window.activeTextEditor;
        if (editor) {
            editor.edit(editBuilder => {
                editBuilder.insert(editor.selection.active, code);
            });
        }
    }

    private updateWebview(): void {
        if (this.webviewView) {
            this.webviewView.webview.postMessage({
                command: 'updateMessages',
                messages: this.messages,
            });
        }
    }

    private getHtmlContent(): string {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Grace Chat</title>
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
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        .header {
            padding: 8px 12px;
            border-bottom: 1px solid var(--vscode-panel-border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header h3 {
            font-size: 13px;
            font-weight: 600;
        }
        .header button {
            background: transparent;
            border: none;
            color: var(--vscode-foreground);
            cursor: pointer;
            padding: 4px 8px;
            border-radius: 3px;
        }
        .header button:hover {
            background: var(--vscode-toolbar-hoverBackground);
        }
        .messages {
            flex: 1;
            overflow-y: auto;
            padding: 12px;
        }
        .message {
            margin-bottom: 16px;
            animation: fadeIn 0.2s ease;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(4px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .message-role {
            font-size: 11px;
            font-weight: 600;
            margin-bottom: 4px;
            text-transform: uppercase;
            color: var(--vscode-descriptionForeground);
        }
        .message-role.user {
            color: var(--vscode-textLink-foreground);
        }
        .message-role.assistant {
            color: var(--vscode-terminal-ansiGreen);
        }
        .message-content {
            background: var(--vscode-input-background);
            padding: 8px 12px;
            border-radius: 6px;
            white-space: pre-wrap;
            word-break: break-word;
            line-height: 1.5;
        }
        .message.user .message-content {
            background: var(--vscode-textBlockQuote-background);
        }
        .code-block {
            background: var(--vscode-textCodeBlock-background);
            border: 1px solid var(--vscode-panel-border);
            border-radius: 4px;
            margin: 8px 0;
            overflow: hidden;
        }
        .code-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 4px 8px;
            background: var(--vscode-editorGroupHeader-tabsBackground);
            font-size: 11px;
        }
        .code-block pre {
            padding: 8px;
            overflow-x: auto;
            margin: 0;
        }
        .code-block code {
            font-family: var(--vscode-editor-font-family);
            font-size: var(--vscode-editor-font-size);
        }
        .copy-btn, .insert-btn {
            background: transparent;
            border: none;
            color: var(--vscode-foreground);
            cursor: pointer;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 11px;
        }
        .copy-btn:hover, .insert-btn:hover {
            background: var(--vscode-toolbar-hoverBackground);
        }
        .input-area {
            padding: 12px;
            border-top: 1px solid var(--vscode-panel-border);
        }
        .input-container {
            display: flex;
            gap: 8px;
        }
        textarea {
            flex: 1;
            background: var(--vscode-input-background);
            color: var(--vscode-input-foreground);
            border: 1px solid var(--vscode-input-border);
            border-radius: 4px;
            padding: 8px;
            font-family: var(--vscode-font-family);
            font-size: var(--vscode-font-size);
            resize: none;
            min-height: 60px;
        }
        textarea:focus {
            outline: none;
            border-color: var(--vscode-focusBorder);
        }
        .send-btn {
            background: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            cursor: pointer;
            font-weight: 500;
        }
        .send-btn:hover {
            background: var(--vscode-button-hoverBackground);
        }
        .send-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .typing-indicator {
            display: inline-flex;
            gap: 4px;
            padding: 8px;
        }
        .typing-indicator span {
            width: 6px;
            height: 6px;
            background: var(--vscode-foreground);
            border-radius: 50%;
            animation: bounce 1.4s infinite ease-in-out;
        }
        .typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
        .typing-indicator span:nth-child(2) { animation-delay: -0.16s; }
        @keyframes bounce {
            0%, 80%, 100% { transform: scale(0); }
            40% { transform: scale(1); }
        }
        .empty-state {
            text-align: center;
            padding: 40px 20px;
            color: var(--vscode-descriptionForeground);
        }
        .empty-state h4 {
            margin-bottom: 8px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h3>Grace Chat</h3>
        <button onclick="clearChat()" title="Clear chat">Clear</button>
    </div>

    <div class="messages" id="messages">
        <div class="empty-state">
            <h4>Welcome to Grace</h4>
            <p>Ask questions about your code, request explanations, or get help with development tasks.</p>
        </div>
    </div>

    <div class="input-area">
        <div class="input-container">
            <textarea
                id="input"
                placeholder="Ask Grace anything..."
                onkeydown="handleKeydown(event)"
            ></textarea>
            <button class="send-btn" onclick="sendMessage()">Send</button>
        </div>
    </div>

    <script>
        const vscode = acquireVsCodeApi();
        let messages = [];

        function handleKeydown(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        }

        function sendMessage() {
            const input = document.getElementById('input');
            const text = input.value.trim();
            if (!text) return;

            vscode.postMessage({ command: 'sendMessage', text });
            input.value = '';
        }

        function clearChat() {
            vscode.postMessage({ command: 'clear' });
        }

        function copyCode(code) {
            navigator.clipboard.writeText(code);
        }

        function insertCode(code) {
            vscode.postMessage({ command: 'insertCode', code });
        }

        function renderMessages() {
            const container = document.getElementById('messages');

            if (messages.length === 0) {
                container.innerHTML = \`
                    <div class="empty-state">
                        <h4>Welcome to Grace</h4>
                        <p>Ask questions about your code, request explanations, or get help with development tasks.</p>
                    </div>
                \`;
                return;
            }

            container.innerHTML = messages.map(msg => \`
                <div class="message \${msg.role}">
                    <div class="message-role \${msg.role}">\${msg.role}</div>
                    <div class="message-content">\${formatContent(msg.content)}</div>
                </div>
            \`).join('');

            // Scroll to bottom
            container.scrollTop = container.scrollHeight;
        }

        function formatContent(content) {
            if (!content) {
                return '<div class="typing-indicator"><span></span><span></span><span></span></div>';
            }

            // Escape HTML
            content = content.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

            // Format code blocks
            content = content.replace(/\`\`\`(\\w*)\\n([\\s\\S]*?)\`\`\`/g, (match, lang, code) => {
                const escapedCode = code.trim();
                return \`
                    <div class="code-block">
                        <div class="code-header">
                            <span>\${lang || 'code'}</span>
                            <div>
                                <button class="copy-btn" onclick="copyCode(\\\`\${escapedCode.replace(/\`/g, '\\\\\`')}\\\`)">Copy</button>
                                <button class="insert-btn" onclick="insertCode(\\\`\${escapedCode.replace(/\`/g, '\\\\\`')}\\\`)">Insert</button>
                            </div>
                        </div>
                        <pre><code>\${escapedCode}</code></pre>
                    </div>
                \`;
            });

            // Format inline code
            content = content.replace(/\`([^\`]+)\`/g, '<code>$1</code>');

            // Format bold
            content = content.replace(/\\*\\*([^*]+)\\*\\*/g, '<strong>$1</strong>');

            // Format newlines
            content = content.replace(/\\n/g, '<br>');

            return content;
        }

        window.addEventListener('message', event => {
            const message = event.data;
            if (message.command === 'updateMessages') {
                messages = message.messages;
                renderMessages();
            }
        });
    </script>
</body>
</html>`;
    }
}
