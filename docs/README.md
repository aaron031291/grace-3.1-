# Documentation Organization

This directory contains all markdown documentation files organized by domain.

## Directory Structure

### Architecture (`architecture/`)
Architecture documents, layer descriptions, and system design documents.
- Layer architecture (LAYER1, LAYER2, LAYER3, LAYER4)
- Framework architectures (CLARITY_FRAMEWORK, COMPILER_GOVERNED)
- System architectures (ENTERPRISE_SECURITY, GRACE_NATIVE)

### Benchmarks (`benchmarks/`)
Benchmark results, integration guides, and performance analysis.
- HumanEval, MBPP, BigCodeBench results
- Benchmark integration and expansion reports
- Performance analysis and summaries

### Completion Reports (`completion-reports/`)
Documents marking completion of features, integrations, or systems.
- Integration completion reports
- System implementation completions
- Feature delivery confirmations

### Integration (`integration/`)
Integration guides, connection documentation, and unified system docs.
- System integrations (Oracle, Knowledge Base, LLM)
- Connection documentation
- Unified system integrations

### Roadmaps (`roadmaps/`)
Planning documents, projections, and strategic plans.
- Project roadmaps and plans
- Projection documents
- Strategic planning documents

### Status (`status/`)
Status reports, evaluation results, and current state documentation.
- System status reports
- Evaluation running status
- Current status confirmations

### Fixes (`fixes/`)
Fix summaries, applied fixes, and healing documentation.
- Fixes applied summaries
- Self-healing guides
- Diagnostic and healing enhancements

### Guides (`guides/`)
How-to guides, quick starts, and user documentation.
- Quick start guides
- Setup and authentication guides
- Usage and verification guides

### Analysis (`analysis/`)
Analysis documents, assessments, and investigation reports.
- Gap analysis
- Performance analysis
- System assessments

### System (`system/`)
System documentation, capabilities, and feature descriptions.
- System capabilities
- Feature documentation
- System improvements

### Enterprise (`enterprise/`)
Enterprise-specific documentation.
- Enterprise security architecture
- High-stakes domains documentation
- Enterprise capabilities

### Knowledge (`knowledge/`)
Knowledge base, learning, and template documentation.
- Knowledge integration
- Learning systems
- Template systems

### Healing (`healing/`)
Self-healing system documentation.
- Self-healing guides
- Healing knowledge sources
- Autonomous healing systems

### Evaluation (`evaluation/`)
Evaluation results and test reports.
- Stress test reports
- Evaluation results
- Test summaries

### Coding Agent (`coding-agent/`)
Coding agent documentation and IDE integration.
- Coding agent capabilities
- IDE integration
- Agent building guides

### Genesis (`genesis/`)
Genesis system and version control documentation.
- Genesis key solutions
- Version control documentation
- File tracking systems

### LLM (`llm/`)
LLM integration and orchestration documentation.
- LLM integration status
- Enhanced LLM systems
- Hallucination prevention

### Miscellaneous (`miscellaneous/`)
Files that don't fit into other categories or need further categorization.

## File Naming Conventions

Files are organized based on their content and purpose:
- **ARCHITECTURE**: System and component architectures
- **COMPLETE**: Completion reports
- **INTEGRATION**: Integration guides
- **STATUS**: Status reports
- **FIXES**: Fix documentation
- **GUIDE**: How-to guides
- **ANALYSIS**: Analysis documents
- **SYSTEM**: System documentation
- **BENCHMARK**: Benchmark-related files

## Finding Documentation

To find specific documentation:
1. Check the appropriate domain directory
2. Use your IDE's search functionality
3. Look for keywords in filenames (e.g., "LAYER4", "BENCHMARK", "INTEGRATION")

## Data Files Organization

Data files (JSON, logs, text outputs) are organized in the `data/` subdirectory by domain:
- **benchmarks/**: Benchmark results and performance data (JSON)
- **reports/**: Test reports, stress test results, and text output files (JSON, TXT)
- **config/**: Configuration files and system specifications (JSON)
- **knowledge/**: Knowledge base data, templates, and learning data (JSON)
- **genesis/**: Genesis system metadata and version tracking (JSON)
- **logs/**: Log files from debugging, testing, and system operations (.log)
- **scripts/**: Utility scripts organized in root `scripts/` directory (.ps1, .sh, .bat)
- **miscellaneous/**: Files that don't fit into other categories

See `data/README.md` for more details on data file organization.

## Notes

- Files from the `data/` directory are preserved in their original location
- Implementation-specific guides (like `web_scraping_implementation/`) remain in their original structure
- Some files may appear in multiple categories if they cover multiple domains
- Project configuration files (package.json, tsconfig.json, etc.) remain in their original locations
- Runtime data files in `knowledge_base/` and `backend/` are preserved in place
