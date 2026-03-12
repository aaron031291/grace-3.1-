"""
Database migration: Add query intelligence tables.

Creates tables for tracking multi-tier query handling:
- query_handling_log: Tracks tier usage and confidence scores
- knowledge_gaps: Stores identified knowledge gaps
- context_submissions: Records user-provided context
"""

from sqlalchemy import create_engine, text
from database.connection import DatabaseConnection
from database.base import Base


def upgrade():
    """Create query intelligence tables."""
    engine = DatabaseConnection.get_engine()
    
    with engine.connect() as conn:
        # Table 1: Query Handling Log
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS query_handling_log (
                id SERIAL PRIMARY KEY,
                query_id VARCHAR(255) UNIQUE NOT NULL,
                query_text TEXT NOT NULL,
                tier_used VARCHAR(50) NOT NULL,
                confidence_score FLOAT,
                
                -- Tier 1: VectorDB metrics
                vectordb_attempted BOOLEAN DEFAULT FALSE,
                vectordb_quality FLOAT,
                vectordb_result_count INTEGER,
                
                -- Tier 2: Model Knowledge metrics
                model_attempted BOOLEAN DEFAULT FALSE,
                model_confidence FLOAT,
                uncertainty_detected BOOLEAN DEFAULT FALSE,
                
                -- Tier 3: Context Request metrics
                context_requested BOOLEAN DEFAULT FALSE,
                context_provided BOOLEAN DEFAULT FALSE,
                
                -- Outcome
                final_success BOOLEAN DEFAULT FALSE,
                response_time_ms INTEGER,
                
                -- Tracking
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                genesis_key_id VARCHAR(255),
                user_id VARCHAR(255)
            )
        """))
        
        # Table 2: Knowledge Gaps
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS knowledge_gaps (
                id SERIAL PRIMARY KEY,
                query_id VARCHAR(255) NOT NULL,
                gap_id VARCHAR(255) UNIQUE NOT NULL,
                gap_topic VARCHAR(255) NOT NULL,
                specific_question TEXT NOT NULL,
                required BOOLEAN DEFAULT TRUE,
                
                -- Resolution tracking
                resolved BOOLEAN DEFAULT FALSE,
                resolution_source VARCHAR(50),
                resolved_at TIMESTAMP,
                
                -- Metadata
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (query_id) REFERENCES query_handling_log(query_id) ON DELETE CASCADE
            )
        """))
        
        # Table 3: Context Submissions
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS context_submissions (
                id SERIAL PRIMARY KEY,
                query_id VARCHAR(255) NOT NULL,
                gap_id VARCHAR(255),
                submitted_context TEXT NOT NULL,
                
                -- Usage tracking
                used_in_response BOOLEAN DEFAULT FALSE,
                improved_response BOOLEAN,
                
                -- Trust scoring
                trust_score FLOAT DEFAULT 0.5,
                validated BOOLEAN DEFAULT FALSE,
                
                -- Tracking
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id VARCHAR(255),
                genesis_key_id VARCHAR(255),
                
                FOREIGN KEY (query_id) REFERENCES query_handling_log(query_id) ON DELETE CASCADE,
                FOREIGN KEY (gap_id) REFERENCES knowledge_gaps(gap_id) ON DELETE SET NULL
            )
        """))
        
        # Create indexes for performance
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_query_handling_log_tier 
            ON query_handling_log(tier_used)
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_query_handling_log_created 
            ON query_handling_log(created_at DESC)
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_knowledge_gaps_query 
            ON knowledge_gaps(query_id)
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_knowledge_gaps_resolved 
            ON knowledge_gaps(resolved)
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_context_submissions_query 
            ON context_submissions(query_id)
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_context_submissions_gap 
            ON context_submissions(gap_id)
        """))
        
        conn.commit()
        
    print("[OK] Query intelligence tables created successfully")


def downgrade():
    """Drop query intelligence tables."""
    engine = DatabaseConnection.get_engine()
    
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS context_submissions CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS knowledge_gaps CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS query_handling_log CASCADE"))
        conn.commit()
        
    print("[OK] Query intelligence tables dropped successfully")


if __name__ == "__main__":
    print("Running query intelligence tables migration...")
    upgrade()
    print("Migration complete!")
