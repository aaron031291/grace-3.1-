# GRACE Business Intelligence System

## Architecture Overview

The Business Intelligence (BI) system is a closed-loop intelligence engine integrated into GRACE. It operates in six phases:

```
COLLECT -> SYNTHESIZE -> IDENTIFY -> VALIDATE -> BUILD -> SCALE

Phase 1: COLLECT     - Pull data from all connected platforms
Phase 2: SYNTHESIZE  - Detect trends, aggregate insights, LLM reasoning
Phase 3: IDENTIFY    - Find pain points, competitors, market gaps
Phase 4: VALIDATE    - Run ads, collect waitlist, test demand
Phase 5: BUILD       - Generate product concepts, plan development
Phase 6: SCALE       - Archetype targeting, cross-domain expansion, lookalikes
```

The system auto-advances phases based on data sufficiency. Grace tracks her own confidence level and flags when she needs more data or knowledge.

---

## System Map (45 files, ~10,000 lines)

```
backend/business_intelligence/
├── __init__.py                          # Package root, version
├── config.py                            # Central config, env loading, connector configs
├── BUSINESS_INTELLIGENCE.md             # This file
│
├── connectors/                          # Data source integrations
│   ├── base.py                          # BaseConnector, ConnectorRegistry
│   ├── google_analytics.py              # GA4 Data API - traffic, audience, conversions
│   ├── shopify_connector.py             # Shopify Admin API - products, orders, revenue
│   ├── amazon_connector.py              # Amazon PA-API 5.0 - product listings, reviews
│   ├── junglescout_connector.py         # Jungle Scout API - sales estimates, keyword volume
│   ├── meta_connector.py                # Meta Marketing API - ad performance, audiences
│   ├── instagram_connector.py           # Instagram Graph API - insights, hashtags, demographics
│   ├── youtube_connector.py             # YouTube Data API v3 + Analytics - video/channel stats
│   ├── tiktok_connector.py              # TikTok Marketing API - ad reports, performance
│   ├── serpapi_connector.py             # SerpAPI - Google search, shopping, trends
│   └── web_scraping_connector.py        # Reddit/forum scraping for pain points
│
├── models/
│   └── data_models.py                   # Core data structures (35+ dataclasses)
│
├── market_research/                     # Pain point discovery and competitor analysis
│   ├── pain_point_engine.py             # NLP extraction, clustering, scoring
│   ├── review_analyzer.py              # Negative review mining, feature request extraction
│   ├── competitor_analyzer.py           # Pricing gaps, feature gaps, entry difficulty
│   └── research_orchestrator.py         # Full research pipeline coordinator
│
├── synthesis/                           # Intelligence aggregation and reasoning
│   ├── intelligence_engine.py           # Central engine, state management, cycle runner
│   ├── trend_detector.py                # Time-series analysis, seasonality, inflections
│   ├── opportunity_scorer.py            # 6-dimension scoring with configurable weights
│   └── reasoning_engine.py              # LLM reasoning with hallucination guards
│
├── campaigns/                           # Demand validation and advertising
│   ├── ad_copy_generator.py             # Ethical, pain-point-driven ad copy
│   ├── campaign_manager.py              # Campaign plans, A/B testing, result tracking
│   ├── waitlist_manager.py              # GDPR-compliant waitlist with demographics
│   ├── validation_engine.py             # Go/no-go decision engine
│   ├── lookalike_engine.py              # Meta lookalike audiences, traffic strategy
│   ├── ad_optimizer.py                  # Real-time performance optimization
│   └── dynamic_creative.py              # DCO: Meta, TikTok, Google, Canva, AdCreative.ai
│
├── customer_intelligence/               # Customer analysis and targeting
│   ├── archetype_engine.py              # Aggregate customer profiling (min cluster: 10)
│   └── pattern_analyzer.py              # Cross-domain expansion strategy
│
├── product_discovery/                   # Product ideation from intelligence
│   ├── niche_finder.py                  # Niche scoring with Grace advantage calc
│   └── product_ideation.py              # Product concepts, pricing, product ladders
│
├── historical/                          # Persistence and time-series
│   └── data_store.py                    # JSON file storage, timeline, retention
│
└── utils/
    ├── initializer.py                   # BISystem facade, connector registration
    └── secrets_vault.py                 # AES-encrypted credential storage
```

---

## Data Connectors

Each connector inherits from `BaseConnector` and registers with `ConnectorRegistry`. Connectors degrade gracefully when credentials are missing -- the system continues with whatever data sources are available.

### Connector Status

| Connector | API Key Env Var | Status When Missing | What It Provides |
|-----------|----------------|---------------------|------------------|
| Google Analytics | `GA_API_KEY`, `GA_PROPERTY_ID` | Degraded | Traffic sources, sessions, bounce rate, conversions |
| Shopify | `SHOPIFY_API_KEY`, `SHOPIFY_ACCESS_TOKEN`, `SHOPIFY_STORE_URL` | Degraded | Product sales, revenue, inventory, orders |
| Amazon PA-API | `AMAZON_ACCESS_KEY`, `AMAZON_SECRET_KEY`, `AMAZON_PARTNER_TAG` | Degraded | Product listings, ratings, features |
| Jungle Scout | `JUNGLESCOUT_API_KEY`, `JUNGLESCOUT_API_NAME` | Degraded | Est. revenue, sales volume, keyword search volume, niche scores |
| Meta Marketing | `META_ACCESS_TOKEN`, `META_AD_ACCOUNT_ID` | Degraded | Ad performance, campaign metrics, audience insights |
| Instagram | `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_BUSINESS_ID` | Degraded | Account insights, hashtag volume, audience demographics |
| YouTube | `YOUTUBE_API_KEY` (+ `YOUTUBE_OAUTH_TOKEN`, `YOUTUBE_CHANNEL_ID` for analytics) | Degraded | Video search, engagement, channel stats, niche analysis |
| TikTok | `TIKTOK_ACCESS_TOKEN`, `TIKTOK_ADVERTISER_ID` | Degraded | Ad campaign reports, spend, conversions |
| SerpAPI | `SERPAPI_KEY` | Degraded | Google search results, shopping, trends |
| Web Scraping | Always active | Active | Reddit posts, forum discussions, review sites |

### Connector Health API

```
GET /bi/connectors
```

Returns real-time status of every connector including error counts and last successful pull.

---

## Core Data Models

All models are in `models/data_models.py`:

- **MarketDataPoint** -- Single data observation from any source
- **KeywordMetric** -- Search keyword performance (volume, CPC, trend)
- **TrafficSource** -- Website traffic source analytics
- **ReviewAnalysis** -- Parsed product review with sentiment and pain points
- **PainPoint** -- Validated customer complaint with severity and frequency
- **CompetitorProduct** -- Competitor product with pricing, ratings, features
- **MarketOpportunity** -- Scored market opportunity with pain points and competitors
- **CustomerArchetype** -- Aggregate customer profile (never individual)
- **CampaignResult** -- Ad campaign performance metrics
- **WaitlistEntry** -- GDPR-compliant waitlist signup
- **ProductConcept** -- Generated product idea with features, pricing, development estimate
- **IntelligenceSnapshot** -- Point-in-time snapshot of entire intelligence state

---

## Pipeline Deep-Dive

### Phase 1: Data Collection

```
POST /bi/intelligence/cycle
{
    "niches": ["ai automation tools"],
    "keywords": {"ai automation tools": ["ai workflow", "automation software", "no-code ai"]},
    "force_collection": false
}
```

The intelligence engine calls `ConnectorRegistry.collect_all()` which fans out to every active connector. Each connector returns `MarketDataPoint` objects. Data is appended to the engine's state and pruned by retention period (default: 365 days).

### Phase 2: Synthesis

After collection, the engine runs:
1. **TrendDetector** -- Analyzes time-series data for rising/declining/seasonal patterns
2. **BIReasoningEngine** -- Pipes data through GRACE's LLM with hallucination guards
3. **OpportunityScorer** -- Scores opportunities across 6 dimensions:
   - Pain severity (25%)
   - Market size (15%)
   - Competition gap (20%)
   - Trend momentum (15%)
   - Entry feasibility (15%)
   - Revenue potential (10%)

### Phase 3: Market Research

```
POST /bi/research
{
    "niche": "ai automation tools",
    "keywords": ["ai workflow", "automation software"],
    "depth": "standard"
}
```

The `MarketResearchOrchestrator` coordinates:
1. Data collection from all connectors
2. Pain point extraction (NLP pattern matching against 8 complaint categories)
3. Pain point clustering by theme
4. Competitor landscape analysis (pricing gaps, feature gaps, quality gaps)
5. Opportunity scoring
6. Grace self-assessment (confidence level with stated concerns)

### Phase 4: Validation

```
POST /bi/campaigns/plan
POST /bi/waitlist/signup
GET  /bi/validation/evaluate
```

The validation loop:
1. Generate ad copy from pain points (`AdCopyGenerator`)
2. Create campaign plan (requires human approval)
3. Run ads on Meta/TikTok/Google
4. Collect waitlist signups (500+ = validated demand)
5. `ValidationEngine` produces go/no-go verdict

### Phase 5: Product Discovery

```
POST /bi/products/ideate
POST /bi/products/ladder
```

The `ProductIdeationEngine` generates product concepts from validated opportunities:
- Converts pain points into features
- Calculates competitive pricing from market data
- Estimates development time by product type
- Generates product ladders (free lead magnet -> course -> SaaS -> community)

### Phase 6: Scaling

```
POST /bi/lookalike/create
GET  /bi/traffic/strategy
GET  /bi/customers/cross-patterns
```

The scaling phase:
1. Build customer archetypes from waitlist data
2. Create lookalike audiences (Meta, TikTok)
3. Find cross-domain expansion opportunities
4. Generate phased expansion strategy

---

## Dynamic Creative Optimization

```
POST /bi/creative/pipeline
GET  /bi/creative/tools
POST /bi/creative/meta-dco
```

Real-time ad creative editing is available through:

| Tool | What It Edits | How |
|------|--------------|-----|
| Meta DCO | Headlines, body text, images, CTAs | Auto-tests all combinations per impression |
| Canva Connect API | Fonts, colors, image positions, layouts | Programmatic design editing via REST API |
| AdCreative.ai | Full creatives with AI | AI generates and optimizes creatives |
| TikTok Symphony | Video scripts, AI avatars, trending formats | AI creative generation |
| Google Responsive | Headlines, descriptions | ML auto-combines per search query |

---

## Secrets Vault

```
POST /bi/vault/store
GET  /bi/vault/keys
GET  /bi/vault/status
```

AES-encrypted (Fernet) storage for API credentials. Set `BI_VAULT_PASSPHRASE` environment variable to enable. Automatically loads stored secrets into environment variables on startup.

---

## GDPR Compliance

Built into every component:

- **WaitlistManager**: Requires explicit consent, provides opt-out, auto-anonymizes after retention period
- **ArchetypeEngine**: Minimum cluster size of 10 (never profiles individuals), consent verification
- **SecretsVault**: Prohibited fields auto-redacted (SSN, passport, credit cards, medical, biometric)
- **LookalikeEngine**: Only uses consented, hashed emails for audience creation
- **Config**: `require_consent_for_tracking`, `anonymize_after_days`, `prohibited_data_fields`

---

## LLM Reasoning Integration

The `BIReasoningEngine` connects to GRACE's existing LLM infrastructure:

- Uses `get_llm_client()` from `llm_orchestrator.factory`
- All outputs pass through `HallucinationGuard`
- System prompt enforces data-backed conclusions only
- Tasks: market analysis, opportunity evaluation, campaign optimization, product strategy, daily briefings
- Falls back gracefully to data-only mode when LLM is unavailable

```
POST /bi/reasoning/market
POST /bi/reasoning/product-strategy
GET  /bi/reasoning/briefing
GET  /bi/reasoning/history
```

---

## API Quick Reference

### System
- `GET /bi/status` -- Full system status
- `GET /bi/connectors` -- Connector health

### Intelligence
- `POST /bi/intelligence/cycle` -- Run collection + analysis cycle
- `GET /bi/intelligence/snapshot` -- Latest state
- `POST /bi/intelligence/knowledge-request` -- Grace requests more data

### Research
- `POST /bi/research` -- Full market research
- `POST /bi/research/quick-scan` -- Lightweight scan
- `POST /bi/niches/find` -- Discover niches from keywords

### Platform-Specific
- `POST /bi/amazon/keyword-research` -- Jungle Scout keywords
- `POST /bi/amazon/product-database` -- Jungle Scout products
- `POST /bi/amazon/niche-analysis` -- Amazon niche scores
- `POST /bi/youtube/search` -- YouTube video search
- `POST /bi/youtube/niche-analysis` -- YouTube content landscape
- `GET /bi/youtube/channel-analytics` -- Own channel analytics
- `GET /bi/youtube/demographics` -- Own audience demographics
- `GET /bi/instagram/insights` -- Account insights
- `GET /bi/instagram/demographics` -- Audience demographics
- `GET /bi/instagram/media` -- Recent posts with engagement
- `POST /bi/instagram/hashtag` -- Hashtag volume research

### Campaigns
- `POST /bi/campaigns/plan` -- Create campaign (needs approval)
- `POST /bi/campaigns/{id}/approve` -- Approve campaign
- `POST /bi/campaigns/record-result` -- Record performance
- `GET /bi/campaigns/summary` -- All campaigns summary
- `GET /bi/campaigns/{id}/ab-results` -- A/B test analysis

### Ads
- `POST /bi/ads/generate` -- Generate ad copy variants
- `POST /bi/ads/landing-page-copy` -- Landing page copy
- `POST /bi/ads/optimize` -- Run ad optimization
- `GET /bi/ads/optimization-dashboard` -- Optimization state

### Creative
- `POST /bi/creative/pipeline` -- Full creative pipeline
- `POST /bi/creative/meta-dco` -- Meta Dynamic Creative spec
- `GET /bi/creative/tools` -- Available creative tools

### Waitlist
- `POST /bi/waitlist/signup` -- Add signup
- `POST /bi/waitlist/opt-out` -- Opt out
- `GET /bi/waitlist/stats` -- Statistics

### Validation
- `GET /bi/validation/evaluate` -- Go/no-go verdict

### Customers
- `GET /bi/customers/archetypes` -- Customer archetypes
- `GET /bi/customers/targeting` -- Targeting recommendations
- `GET /bi/customers/cross-patterns` -- Cross-domain patterns

### Products
- `POST /bi/products/ideate` -- Generate product concepts
- `POST /bi/products/ladder` -- Product ladder (free -> high ticket)

### Lookalike & Traffic
- `POST /bi/lookalike/prepare-seed` -- Prepare audience seed
- `POST /bi/lookalike/create` -- Create lookalike audience
- `GET /bi/lookalike/strategy` -- Audience strategy recommendations
- `GET /bi/traffic/strategy` -- Complete traffic acquisition strategy

### Reasoning
- `POST /bi/reasoning/market` -- LLM market analysis
- `POST /bi/reasoning/product-strategy` -- LLM product strategy
- `GET /bi/reasoning/briefing` -- Grace daily briefing
- `GET /bi/reasoning/history` -- Reasoning history

### History
- `GET /bi/history/timeline` -- Historical intelligence timeline
- `GET /bi/history/snapshots` -- Historical snapshots
- `POST /bi/history/cleanup` -- Clean old data

### Vault
- `POST /bi/vault/store` -- Store secret
- `GET /bi/vault/keys` -- List keys (no values)
- `DELETE /bi/vault/{key}` -- Delete secret
- `GET /bi/vault/status` -- Vault status
