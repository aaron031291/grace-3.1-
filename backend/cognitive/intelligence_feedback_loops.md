# intelligence_feedback_loops

Intelligence Feedback Loops

## Location
`cognitive/intelligence_feedback_loops.py`

## Classes
- **CriteriaEffectivenessTracker**: Loop 1: Track which criteria catch real problems vs noise.
- **QuestionEffectivenessTracker**: Loop 2: Track which questions Grace can self-answer vs need user.
- **ResearchQualityTracker**: Loop 3: Track which research sources lead to task success vs failure.
- **KnowledgeGapPriorityQueue**: Loop 7: Prioritize knowledge gaps by frequency.
- **PlaybookEvolution**: Loop 8: Playbooks improve with each use.
- **CrossTaskDependencyDetector**: Loop 9: Detect when tasks block each other.
- **VerificationGuardFeedback**: Loop 10: Task verification outcomes train the hallucination guard.
- **UnifiedTaskEnrichment**: Loop 6: Run task through all 9 intelligence layers for context.
- **IntelligenceFeedbackCoordinator**: Coordinates all 11 feedback loops.

## Functions
- `get_feedback_coordinator()`

