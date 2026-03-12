# GRACE 3.1 - Client Usage Documentation

Welcome to **GRACE** (Genesis-driven RAG Autonomous Cognitive Engine). This document provides a quick-start guide to using the application, interacting with its features, and keeping the system running.

---

## 🚀 Quick Start: How to Launch GRACE

GRACE consists of multiple services (Backend, Frontend, Vector Database, and LLM providers). It is designed to be easily launched with a single script.

### On Windows
1. Open **PowerShell** or **Command Prompt**.
2. Navigate to the project folder where GRACE is installed:
   ```powershell
   cd path\to\grace-3.1-
   ```
3. Run the start script:
   ```powershell
   .\start.bat
   ```
   *This command automatically starts the Qdrant database (if Docker is installed), the Python backend, and the React frontend.*

### On Linux or Mac
1. Open a terminal and navigate to the project directory:
   ```bash
   cd path/to/grace-3.1-
   ```
2. Run the start script:
   ```bash
   ./start.sh
   ```

### Accessing the Interface
Once the services start successfully, open your web browser and navigate to:
**👉 http://localhost:5173**

---

## 💬 Basic Usage: Core Features

### 1. Chat & Assistant Interface
When you open GRACE, you will be greeted by the **ChatWindow**. 
- You can type questions or requests directly.
- GRACE uses a **Multi-Tier RAG Pipeline** to answer your queries:
   1. It checks the built-in Vector Database for exact semantic matches.
   2. It falls back to the AI Model's underlying knowledge.
   3. It can perform a Web Search or ask for context if it lacks information.

### 2. Document Ingestion (Knowledge Base)
To teach GRACE about your specific business data or documents:
- Go to the **FileBrowser** or **Ingestion Dashboard** tab.
- You can upload PDFs, Word Documents (.docx), Excel sheets (.xlsx), Text files, or Code files.
- GRACE will automatically chunk, summarize, and embed these documents so it can recall them accurately in future chats. 
- *The AI Librarian System will automatically categorize and tag your uploads.*

### 3. Genesis Tracking System (Provenance Audit)
Every action, document mutation, and creation in the system is tracked through **Genesis Keys**.
- This acts as an immutable audit log.
- If you need to verify *why* the AI knows something, you can view the Genesis data to see exactly which document or interaction generated that piece of knowledge.

### 4. Sandbox Lab & Exploration
If enabled by your administrator, GRACE has an active **Sandbox Lab** where you can experiment with logic, configure AI models (like Ollama or OpenAI), and test the 4-layer Diagnostic Machine.

### 5. Advanced Cognitive Features
GRACE 3.1 includes several advanced autonomous and analytical subsystems:
- **Immune System:** A continuous monitoring layer that automatically detects anomalies and self-repairs system issues before failures occur.
- **Consensus Chat:** A specialized chat interface (`ConsensusChat` tab) where you can observe multiple AI sub-agents debate and validate complex technical topics to arrive at an optimized consensus.
- **Oracle / World Model:** A high-level strategic reasoning layer that tracks the overarching project state and guides architectural choices.
- **Business Intelligence (BI):** Check the **Business Intelligence Tab** for high-level technical analytics, trends, and progress metrics synthesized from system telemetry.
- **Flash Cache:** Experience ultra-fast, sub-millisecond response times for frequent actions, powered by GRACE's deterministic caching memory.

---

## 🛠️ Maintenance & Troubleshooting

### Viewing Logs
If something goes wrong (e.g., the AI isn't responding), the best place to check is the structured backend log file.
- **Location:** `backend/logs/grace.log`
- On Windows PowerShell, view the last 100 lines:
  ```powershell
  Get-Content backend\logs\grace.log -Tail 100
  ```

### Fixing GPU / AI Generation Issues
If the AI is responding too slowly or complains about GPU access:
- Open **http://localhost:8000/api/runtime/connectivity** in your browser.
- Check `cuda_available`. If it says `false` but you have an NVIDIA GPU, you may need to run `.\setup_gpu.bat` and restart the application.

### Safely Shutting Down
To gracefully stop the system:
1. Go to the terminal/command prompt window running `start.bat` or `start.sh`.
2. Press **`Ctrl + C`**. You will be prompted to terminate the batch job (`Y/N`). Press **`Y`** and hit Enter.
3. Close the terminal.

---

If you require advanced configuration, API documentation, or deployment instructions, please refer to the `README.md` and the comprehensive `docs/` folder included in the project repository.
