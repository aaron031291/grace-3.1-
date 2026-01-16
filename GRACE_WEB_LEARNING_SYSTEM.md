# GRACE Web Learning System

**Purpose:** Enable LLMs to access the web for learning, verification, and current information while maintaining GRACE's trust and security architecture.

---

## 🎯 Why Web Access for LLMs?

### Benefits

1. **Current Information**
   - Latest documentation for technologies
   - Current best practices
   - Recent updates to frameworks/libraries
   - Real-time factual information

2. **Fact Verification**
   - Verify LLM claims against authoritative sources
   - Cross-check technical information
   - Validate code examples and patterns

3. **Learning New Patterns**
   - Discover new coding patterns
   - Learn from open-source projects
   - Study industry best practices
   - Understand emerging technologies

4. **Knowledge Expansion**
   - Fill gaps in knowledge base
   - Learn domain-specific information
   - Access specialized documentation

---

## 🏗️ Architecture Integration

### GRACE Integration Points

All web access must flow through GRACE's architecture:

```
Web Request
    ↓
Layer 1 (OODA Loop + Trust Scoring)
    ↓
Genesis Key Assignment
    ↓
Web Search/Scraping (with safety checks)
    ↓
Content Extraction & Analysis
    ↓
Trust Scoring (source reliability)
    ↓
Learning Memory Storage
    ↓
RAG Indexing (if high-trust)
    ↓
LLM Context Injection
```

---

## 🔐 Security & Safety

### 1. **Whitelist System**
- Only allow access to trusted domains
- Whitelist categories:
  - Official documentation (python.org, nodejs.org, etc.)
  - Reputable tech sites (Stack Overflow, GitHub, etc.)
  - Academic sources (.edu domains)
  - Known API documentation sites

### 2. **Content Filtering**
- Filter malicious content
- Block executable code downloads
- Sanitize HTML/JavaScript
- Rate limiting to prevent abuse

### 3. **Trust Scoring**
- Source reliability scoring:
  - Official docs: 0.95
  - Reputable sites: 0.85
  - Community sites: 0.70
  - Unknown sites: 0.50 (requires verification)

### 4. **User Approval**
- Optional: Require user approval for web access
- Log all web requests with Genesis Keys
- Allow users to review and approve/disapprove

---

## 📋 Implementation Plan

### Phase 1: Web Search Integration (HIGH PRIORITY)

**File:** `backend/llm_orchestrator/web_learning_system.py`

```python
class WebLearningSystem:
    """
    Enables LLMs to access web for learning and verification.
    
    Features:
    - Web search with safety checks
    - Content extraction and analysis
    - Trust scoring based on source
    - Learning memory integration
    - Genesis Key tracking
    """
    
    def __init__(
        self,
        cognitive_layer1,
        learning_memory,
        whitelist_domains: List[str] = None,
        require_user_approval: bool = False
    ):
        self.layer1 = cognitive_layer1
        self.learning_memory = learning_memory
        self.whitelist = whitelist_domains or self._get_default_whitelist()
        self.require_approval = require_user_approval
    
    def search_and_learn(
        self,
        query: str,
        user_id: str,
        task_type: str = "learning",
        max_results: int = 5
    ) -> Dict[str, Any]:
        """
        Search web and learn from results.
        
        Flow:
        1. Layer 1 processing (OODA + trust)
        2. Genesis Key assignment
        3. Web search (with whitelist check)
        4. Content extraction
        5. Trust scoring
        6. Learning memory storage
        7. Return results for LLM context
        """
        # Step 1: Process through Layer 1
        result = self.layer1.process_system_event(
            event_type="web_learning_request",
            event_data={"query": query, "user_id": user_id},
            metadata={"task_type": task_type}
        )
        
        genesis_key_id = result.get("genesis_key_id")
        
        # Step 2: Web search (with safety checks)
        search_results = self._safe_web_search(query, max_results)
        
        # Step 3: Extract and score content
        learned_content = []
        for result in search_results:
            if self._is_whitelisted(result["url"]):
                content = self._extract_content(result["url"])
                trust_score = self._calculate_source_trust(result["url"])
                
                learned_content.append({
                    "url": result["url"],
                    "title": result.get("title", ""),
                    "content": content,
                    "trust_score": trust_score,
                    "genesis_key_id": genesis_key_id
                })
        
        # Step 4: Store in learning memory (if high-trust)
        high_trust_content = [c for c in learned_content if c["trust_score"] >= 0.8]
        if high_trust_content and self.learning_memory:
            for content in high_trust_content:
                self.learning_memory.record_example(
                    content=content["content"],
                    source=content["url"],
                    trust_score=content["trust_score"],
                    example_type="web_learning"
                )
        
        return {
            "genesis_key_id": genesis_key_id,
            "query": query,
            "results": learned_content,
            "high_trust_count": len(high_trust_content),
            "timestamp": datetime.now().isoformat()
        }
```

### Phase 2: LLM Context Integration

**Enhance LLM Orchestrator** to use web learning:

```python
# In llm_orchestrator.py

def _enhance_prompt_with_web_context(
    self,
    prompt: str,
    task_type: TaskType
) -> str:
    """Enhance prompt with web-learned context if needed."""
    
    # Determine if web search would help
    if self._should_use_web_learning(prompt, task_type):
        # Search and learn
        web_results = self.web_learning.search_and_learn(
            query=extract_search_query(prompt),
            user_id=task_request.user_id,
            task_type=task_type.value
        )
        
        # Add high-trust results to context
        if web_results["high_trust_count"] > 0:
            context = "\n\nWeb-Learned Context (High Trust):\n"
            for result in web_results["results"][:3]:  # Top 3
                if result["trust_score"] >= 0.8:
                    context += f"- {result['title']}: {result['content'][:200]}...\n"
                    context += f"  Source: {result['url']} (Trust: {result['trust_score']:.2f})\n"
            
            return f"{context}\n\nUser Query: {prompt}"
    
    return prompt
```

### Phase 3: Automatic Learning Triggers

**When to use web learning:**

1. **Low Confidence Responses**
   - If LLM confidence < 0.7, search web for verification

2. **Unknown Topics**
   - If topic not in learning memory, search web

3. **Current Information Needed**
   - Questions about "latest", "current", "recent"

4. **Technical Verification**
   - Code examples, API usage, framework features

5. **User Request**
   - User explicitly requests web search

---

## 🔧 Technical Implementation

### Web Search Options

**Option 1: DuckDuckGo (Privacy-focused)**
```python
from duckduckgo_search import DDGS

def _safe_web_search(self, query: str, max_results: int = 5):
    """Search web using DuckDuckGo."""
    with DDGS() as ddgs:
        results = []
        for result in ddgs.text(query, max_results=max_results):
            if self._is_whitelisted(result["href"]):
                results.append({
                    "title": result["title"],
                    "url": result["href"],
                    "snippet": result["body"]
                })
        return results
```

**Option 2: SerpAPI (Google Search API)**
```python
from serpapi import GoogleSearch

def _safe_web_search(self, query: str, max_results: int = 5):
    """Search web using SerpAPI."""
    params = {
        "q": query,
        "api_key": os.getenv("SERPAPI_KEY"),
        "num": max_results
    }
    search = GoogleSearch(params)
    results = search.get_dict()
    
    return [
        {
            "title": r["title"],
            "url": r["link"],
            "snippet": r.get("snippet", "")
        }
        for r in results.get("organic_results", [])
        if self._is_whitelisted(r["link"])
    ]
```

**Option 3: Custom Web Scraper**
```python
import requests
from bs4 import BeautifulSoup

def _extract_content(self, url: str) -> str:
    """Extract text content from URL."""
    try:
        response = requests.get(url, timeout=10, headers={"User-Agent": "GRACE/1.0"})
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Remove scripts, styles
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Extract text
        text = soup.get_text()
        return text[:5000]  # Limit length
    except Exception as e:
        logger.error(f"Error extracting content from {url}: {e}")
        return ""
```

### Default Whitelist

```python
DEFAULT_WHITELIST = [
    # Official Documentation
    "python.org",
    "nodejs.org",
    "react.dev",
    "vuejs.org",
    "angular.io",
    "fastapi.tiangolo.com",
    "pytorch.org",
    "tensorflow.org",
    
    # Reputable Tech Sites
    "stackoverflow.com",
    "github.com",
    "github.io",
    "docs.github.com",
    "developer.mozilla.org",
    "w3.org",
    
    # Academic
    "*.edu",
    
    # API Documentation
    "api.python.org",
    "docs.python.org",
    "npmjs.com",
    "pypi.org",
    
    # Trusted Tech Blogs
    "medium.com/@*",  # Specific authors only
    "dev.to",
    "hackernoon.com",
]
```

---

## 📊 Trust Scoring System

### Source Reliability Scores

```python
def _calculate_source_trust(self, url: str) -> float:
    """Calculate trust score for URL."""
    
    # Official documentation
    if any(domain in url for domain in [
        "python.org", "nodejs.org", "react.dev",
        "docs.python.org", "developer.mozilla.org"
    ]):
        return 0.95
    
    # GitHub (official repos)
    if "github.com" in url and "/docs" in url:
        return 0.90
    
    # Stack Overflow (community, but reputable)
    if "stackoverflow.com" in url:
        return 0.80
    
    # Academic (.edu)
    if ".edu" in url:
        return 0.85
    
    # Known tech sites
    if any(domain in url for domain in [
        "dev.to", "medium.com", "hackernoon.com"
    ]):
        return 0.70
    
    # Whitelisted but unknown
    if self._is_whitelisted(url):
        return 0.60
    
    # Not whitelisted
    return 0.30
```

---

## 🎯 Usage Examples

### Example 1: Learning New Technology

```python
# LLM needs to learn about a new framework
web_results = web_learning.search_and_learn(
    query="FastAPI async best practices 2024",
    user_id="user123",
    task_type="learning"
)

# Results stored in learning memory if trust >= 0.8
# Available for future LLM context
```

### Example 2: Verifying Code Example

```python
# LLM generates code, but confidence is low
if response.confidence_score < 0.7:
    # Search web to verify
    verification = web_learning.search_and_learn(
        query="Python FastAPI async endpoint example",
        user_id="user123",
        task_type="verification"
    )
    
    # Compare with LLM response
    if verification["high_trust_count"] > 0:
        # Use verified information
        enhanced_response = merge_with_web_verification(
            llm_response=response,
            web_results=verification
        )
```

### Example 3: Current Information Query

```python
# User asks: "What's the latest version of Python?"
# LLM doesn't have current info, so search web
web_results = web_learning.search_and_learn(
    query="Python latest version 2024",
    user_id="user123",
    task_type="current_information"
)

# High-trust result stored in learning memory
# Future queries can use this without web search
```

---

## 🔄 Integration with Existing Systems

### 1. **Hallucination Guard Integration**

```python
# In hallucination_guard.py
def verify_with_web(self, content: str) -> Dict[str, Any]:
    """Verify content against web sources."""
    if not self.web_learning:
        return {"verified": False, "reason": "Web learning not enabled"}
    
    # Extract claims from content
    claims = self._extract_claims(content)
    
    # Search web for each claim
    verification_results = []
    for claim in claims:
        results = self.web_learning.search_and_learn(
            query=claim,
            user_id="system",
            task_type="verification"
        )
        verification_results.append(results)
    
    # Determine if verified
    verified = any(r["high_trust_count"] > 0 for r in verification_results)
    
    return {
        "verified": verified,
        "sources": [r["results"] for r in verification_results],
        "confidence": 0.8 if verified else 0.5
    }
```

### 2. **Learning Memory Integration**

```python
# Web-learned content automatically stored in learning memory
# High-trust examples (>= 0.8) become part of knowledge base
# Available for RAG retrieval
# Can be used for fine-tuning
```

### 3. **Genesis Key Tracking**

```python
# Every web request gets a Genesis Key
# Complete audit trail:
# - What was searched
# - What was learned
# - Trust scores
# - Source URLs
# - Timestamp
```

---

## ⚠️ Safety Considerations

### 1. **Rate Limiting**
- Max 10 web searches per hour per user
- Max 100 web searches per day system-wide
- Prevents abuse and API costs

### 2. **Content Sanitization**
- Strip all JavaScript
- Remove executable code
- Sanitize HTML
- Limit content length (5000 chars)

### 3. **User Control**
- Option to disable web learning
- Review web requests before execution
- Approve/disapprove learned content

### 4. **Privacy**
- Don't log user queries to external services
- Use privacy-focused search (DuckDuckGo)
- Anonymize requests where possible

---

## 📈 Success Metrics

### Learning Metrics
- **New Knowledge Learned**: Number of high-trust examples from web
- **Knowledge Gaps Filled**: Topics now covered that weren't before
- **Verification Rate**: % of low-confidence responses verified

### Quality Metrics
- **Trust Score Distribution**: Average trust of web-learned content
- **Source Diversity**: Number of unique trusted sources
- **Learning Memory Growth**: Increase in knowledge base size

### Performance Metrics
- **Response Quality**: Improvement in LLM responses with web context
- **Confidence Improvement**: Increase in confidence scores
- **User Satisfaction**: Feedback on web-enhanced responses

---

## ✅ Implementation Checklist

### Phase 1: Core Web Learning (Week 1-2)
- [ ] Create `web_learning_system.py`
- [ ] Implement web search (DuckDuckGo or SerpAPI)
- [ ] Add whitelist system
- [ ] Implement trust scoring
- [ ] Integrate with Layer 1 (Genesis Keys)

### Phase 2: Learning Memory Integration (Week 2-3)
- [ ] Store high-trust web content in learning memory
- [ ] Index in RAG system
- [ ] Make available for LLM context

### Phase 3: LLM Integration (Week 3-4)
- [ ] Enhance LLM orchestrator with web context
- [ ] Automatic web search for low-confidence responses
- [ ] User-triggered web search

### Phase 4: Safety & Polish (Week 4-5)
- [ ] Rate limiting
- [ ] Content sanitization
- [ ] User controls
- [ ] Monitoring and logging

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install duckduckgo-search beautifulsoup4 requests
# OR
pip install serpapi beautifulsoup4 requests
```

### 2. Enable Web Learning

```python
from llm_orchestrator.web_learning_system import WebLearningSystem

web_learning = WebLearningSystem(
    cognitive_layer1=layer1,
    learning_memory=learning_memory,
    require_user_approval=False  # Set to True for safety
)

# Integrate with LLM orchestrator
orchestrator.web_learning = web_learning
```

### 3. Test

```python
# Test web learning
results = web_learning.search_and_learn(
    query="Python async best practices",
    user_id="test_user",
    task_type="learning"
)

print(f"Genesis Key: {results['genesis_key_id']}")
print(f"High Trust Results: {results['high_trust_count']}")
```

---

## 📝 Summary

**YES, LLMs should have web access for learning purposes**, but it must be:

1. ✅ **Integrated with GRACE's architecture** (Layer 1, Genesis Keys, trust scoring)
2. ✅ **Safe and controlled** (whitelist, rate limiting, content filtering)
3. ✅ **Trust-scored** (source reliability, content quality)
4. ✅ **Stored in learning memory** (high-trust content becomes knowledge)
5. ✅ **Tracked with Genesis Keys** (complete audit trail)

This enables LLMs to:
- Learn current information
- Verify facts
- Fill knowledge gaps
- Stay up-to-date with technologies

All while maintaining GRACE's trust, security, and cognitive framework.
