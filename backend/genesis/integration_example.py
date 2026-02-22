"""
Genesis Comprehensive Tracking - Integration Example

This shows how the comprehensive tracking system captures ALL inputs:
- User uploads
- AI responses
- Coding agent actions
- External API calls
- Web fetches
- File operations
- Database changes
- Librarian actions

Every action creates a Genesis Key for complete audit trail.

Key Methods:
- `example_user_upload_with_tracking()`
- `example_ai_code_generation()`
- `example_external_api_tracking()`
- `example_web_fetch_tracking()`
- `example_session_tracking()`
- `example_complete_user_journey()`
"""

from database.session import initialize_session_factory, SessionLocal
from genesis.comprehensive_tracker import ComprehensiveTracker
from genesis.tracking_middleware import SessionTracker


# ==================== Example 1: User Upload with Full Tracking ====================

def example_user_upload_with_tracking():
    """
    Example: User uploads a PDF, gets ingested, librarian processes it.

    Creates Genesis Keys for:
    1. User upload
    2. File ingestion
    3. AI text extraction (if used)
    4. Librarian processing
    5. Tag assignment
    6. Relationship detection
    """
    SessionLocal = initialize_session_factory()
    db = SessionLocal()

    # User context
    user_id = "user_12345"
    tracker = ComprehensiveTracker(db_session=db, user_id=user_id)

    # 1. Track user upload
    upload_key = tracker.track_user_upload(
        filename="research_paper.pdf",
        file_path="/knowledge_base/research/research_paper.pdf",
        file_size=1024768,
        file_type="application/pdf",
        metadata={"uploaded_via": "web_ui", "folder": "research"}
    )

    print(f"✓ Created upload Genesis Key: {upload_key.key_id}")

    # 2. Track file ingestion (after text extraction and chunking)
    ingestion_key = tracker.track_file_ingestion(
        filename="research_paper.pdf",
        file_path="/knowledge_base/research/research_paper.pdf",
        document_id=123,
        chunks_created=25,
        embeddings_created=25,
        parent_key_id=upload_key.key_id  # Link to upload
    )

    print(f"✓ Created ingestion Genesis Key: {ingestion_key.key_id}")

    # 3. Track AI text extraction (if AI was used)
    ai_key = tracker.track_ai_response(
        prompt="Extract text from PDF: research_paper.pdf",
        response="Successfully extracted 25 pages of text...",
        model="text-extraction-model",
        tokens_used=500,
        parent_key_id=upload_key.key_id
    )

    print(f"✓ Created AI extraction Genesis Key: {ai_key.key_id}")

    # 4. Track librarian auto-processing
    librarian_key = tracker.track_librarian_action(
        document_id=123,
        action_type="auto_categorize",
        tags_assigned=["pdf", "research", "AI", "machine-learning"],
        relationships_detected=3,
        rules_matched=["PDF Documents", "AI Research Folder"],
        parent_key_id=ingestion_key.key_id
    )

    print(f"✓ Created librarian Genesis Key: {librarian_key.key_id}")

    # Now we have complete chain: upload → ingestion → AI extraction → librarian
    print(f"\n✓ Complete Genesis Key chain created for user upload!")
    print(f"  Upload → Ingestion → AI → Librarian")
    print(f"  All actions linked and traceable")

    db.close()


# ==================== Example 2: AI Code Generation Tracking ====================

def example_ai_code_generation():
    """
    Example: AI generates code for a new feature.

    Tracks:
    1. User request
    2. AI code generation
    3. File write
    4. Database update
    """
    db = SessionLocal()
    tracker = ComprehensiveTracker(db_session=db, user_id="user_12345")

    # 1. Track user request
    request_key = tracker.track_user_input(
        message="Create a new TagManager component for the frontend",
        message_type="feature_request",
        metadata={"priority": "high", "component": "frontend"}
    )

    # 2. Track AI code generation
    code_key = tracker.track_ai_code_generation(
        file_path="/frontend/src/components/TagManager.jsx",
        code_generated="import React from 'react';\n\nfunction TagManager() {...}",
        language="javascript",
        purpose="Create TagManager component for tag management UI",
        model="claude-sonnet-4.5",
        parent_key_id=request_key.key_id
    )

    # 3. Track file write
    file_key = tracker._create_genesis_key(
        key_type="FILE_OPERATION",
        what_description="Created file: TagManager.jsx",
        where_location="/frontend/src/components/TagManager.jsx",
        why_reason="AI code generation",
        parent_key_id=code_key.key_id
    )

    print(f"✓ Tracked AI code generation with complete chain:")
    print(f"  User Request → AI Generation → File Write")

    db.close()


# ==================== Example 3: External API Call Tracking ====================

def example_external_api_tracking():
    """
    Example: System fetches data from external API.

    Tracks:
    1. API call to external service
    2. Response processing
    3. Database storage
    """
    db = SessionLocal()
    tracker = ComprehensiveTracker(db_session=db, user_id="system")

    # Track external API call
    api_key = tracker.track_external_api_call(
        api_name="GitHub API",
        endpoint="/repos/anthropics/claude-code/releases/latest",
        method="GET",
        request_data={"headers": {"Accept": "application/json"}},
        response_data={"tag_name": "v1.2.3", "published_at": "2024-01-01"},
        status_code=200,
        metadata={"purpose": "Check for updates"}
    )

    print(f"✓ Tracked external API call: {api_key.key_id}")

    db.close()


# ==================== Example 4: Web Fetch Tracking ====================

def example_web_fetch_tracking():
    """
    Example: System fetches HTML content from web.

    Tracks web fetch with full content metadata.
    """
    db = SessionLocal()
    tracker = ComprehensiveTracker(db_session=db)

    # Track web fetch
    web_key = tracker.track_web_fetch(
        url="https://docs.anthropic.com/claude/reference",
        content="<html><body>Claude API documentation...</body></html>",
        content_type="text/html",
        status_code=200,
        purpose="Fetch Claude API documentation for reference",
        metadata={"cached": False, "fetch_time": 1.2}
    )

    print(f"✓ Tracked web fetch: {web_key.key_id}")

    db.close()


# ==================== Example 5: Session Tracking (Multiple Operations) ====================

def example_session_tracking():
    """
    Example: Track entire session with multiple operations.

    Uses SessionTracker context manager to automatically track
    session start, all operations, and session end.
    """
    with SessionTracker("librarian-batch-processing", user_id="admin") as tracker:
        # All operations in this context are tracked under same session

        # Process multiple documents
        for doc_id in [1, 2, 3, 4, 5]:
            tracker.track_librarian_action(
                document_id=doc_id,
                action_type="reprocess",
                tags_assigned=["reprocessed"],
                relationships_detected=0,
                rules_matched=[]
            )

        # Track AI analysis
        tracker.track_ai_response(
            prompt="Analyze document categories",
            response="Found 5 document categories...",
            model="claude-sonnet-4.5"
        )

        print("✓ All operations tracked under single session")
        print("  Session start/end automatically recorded")


# ==================== Example 6: Complete User Journey ====================

def example_complete_user_journey():
    """
    Example: Complete user journey from input to result.

    Demonstrates full tracking of:
    1. User asks question
    2. AI processes query
    3. System retrieves documents (with tags)
    4. External API enrichment
    5. AI generates response
    6. Response delivered to user
    """
    db = SessionLocal()
    tracker = ComprehensiveTracker(db_session=db, user_id="user_jane")

    # 1. User input
    input_key = tracker.track_user_input(
        message="What are the latest developments in transformer models?",
        message_type="query"
    )

    # 2. AI processes query
    query_key = tracker.track_ai_response(
        prompt="Parse user query: What are the latest developments in transformer models?",
        response="Query intent: research_latest, topic: transformer_models",
        model="claude-sonnet-4.5",
        parent_key_id=input_key.key_id
    )

    # 3. System retrieves documents (simulated)
    # This would trigger tag-aware retrieval, creating more Genesis Keys

    # 4. External API enrichment (fetch latest papers)
    api_key = tracker.track_external_api_call(
        api_name="ArXiv API",
        endpoint="/search",
        method="GET",
        request_data={"query": "transformer models", "sort": "recent"},
        response_data={"papers": [..., ...]},
        status_code=200,
        parent_key_id=query_key.key_id
    )

    # 5. AI generates final response
    response_key = tracker.track_ai_response(
        prompt="Generate answer using retrieved docs and ArXiv papers",
        response="The latest developments in transformer models include...",
        model="claude-sonnet-4.5",
        tokens_used=2500,
        parent_key_id=query_key.key_id
    )

    print(f"✓ Complete user journey tracked:")
    print(f"  Input → Query Processing → Retrieval → API Enrichment → Response")
    print(f"  All {5} steps linked with Genesis Keys")

    # Get full session timeline
    timeline = tracker.get_session_timeline()
    print(f"\n✓ Session timeline: {len(timeline)} events")
    for event in timeline:
        print(f"  - {event.what_description}")

    db.close()


# ==================== Run Examples ====================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("GENESIS COMPREHENSIVE TRACKING - EXAMPLES")
    print("="*70)

    print("\n--- Example 1: User Upload with Full Tracking ---")
    example_user_upload_with_tracking()

    print("\n--- Example 2: AI Code Generation ---")
    example_ai_code_generation()

    print("\n--- Example 3: External API Call ---")
    example_external_api_tracking()

    print("\n--- Example 4: Web Fetch ---")
    example_web_fetch_tracking()

    print("\n--- Example 5: Session Tracking ---")
    example_session_tracking()

    print("\n--- Example 6: Complete User Journey ---")
    example_complete_user_journey()

    print("\n" + "="*70)
    print("ALL EXAMPLES COMPLETED")
    print("="*70)
    print("\nGenesis Keys track:")
    print("  ✓ User inputs (messages, uploads)")
    print("  ✓ AI responses (decisions, code generation)")
    print("  ✓ Coding agent actions")
    print("  ✓ External API calls")
    print("  ✓ Web fetches (HTML content)")
    print("  ✓ File operations")
    print("  ✓ Database changes")
    print("  ✓ Librarian actions")
    print("  ✓ System events")
    print("\nComplete audit trail for EVERYTHING!")
