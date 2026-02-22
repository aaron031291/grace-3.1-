# knowledge_daemon

Continuous background knowledge growth daemon.

## Location
`cognitive/knowledge_daemon.py`

## Classes
- **KnowledgeDaemon**: Background daemon that continuously grows Grace's knowledge.

## Background Loops
- **KNN Expansion** (every 60s): Picks random topics, runs vector similarity search, feeds discoveries back
- **Knowledge Mining** (every 300s): Mines weakest domains from arXiv/external sources, vectorizes results
- **Kimi Proactive Learning** (every 600s): Identifies knowledge gaps, asks Kimi Cloud, compiles responses

## Functions
- `start_knowledge_daemon()` - Start the daemon (call once at app startup)
- `get_knowledge_daemon()` - Get singleton instance
