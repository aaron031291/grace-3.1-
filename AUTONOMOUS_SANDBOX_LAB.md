# 🔬 Autonomous Sandbox Lab - Grace's Self-Improvement Laboratory

## Overview

Grace now has her own **autonomous experimentation laboratory** where she can:

1. **Practice & Experiment** - Test new algorithms autonomously
2. **Build Improvements** - Create better versions of existing systems
3. **90-Day Trials** - Validate improvements with live data
4. **Trust-Based Promotion** - Auto-promote high-performing experiments
5. **User Approval Gates** - Request approval for production deployment

This system allows Grace to **continuously improve herself** while maintaining safety and user control.

---

## 🎯 How It Works

### Experiment Lifecycle

```
┌────────────────────────────────────────────────────────────────┐
│                    EXPERIMENT LIFECYCLE                         │
└────────────────────────────────────────────────────────────────┘

1. PROPOSED (Trust ≥ 0.3)
   ├─> Grace (via Mirror) identifies improvement opportunity
   ├─> Proposes experiment with motivation
   └─> Initial trust score calculated

2. SANDBOX (Trust ≥ 0.3)
   ├─> Experiment enters isolated testing environment
   ├─> Grace writes implementation code
   ├─> Tests against synthetic data
   └─> Records implementation hash

3. TRIAL (Trust ≥ 0.6, 90 days)
   ├─> Experiment runs with live data
   ├─> Performance tracked continuously
   ├─> Trust score updated with each data point
   ├─> Baseline vs experiment metrics compared
   └─> Success rate monitored

4. VALIDATED (Trust ≥ 0.85, Success ≥ 90%)
   ├─> Trial completed successfully
   ├─> Performance improvement verified
   ├─> User approval requested
   └─> Can auto-approve if Trust ≥ 0.95

5. APPROVED (User or Auto)
   ├─> User reviews experiment results
   ├─> Approves or rejects
   └─> If approved, promotes to production

6. PRODUCTION
   ├─> Integrated into main Grace system
   ├─> Experiment becomes part of core functionality
   └─> Grace is now better!
```

---

## 🚀 Quick Start

### Start Grace with Sandbox Lab

The sandbox lab is **already integrated** and starts automatically:

```bash
cd backend
python scripts/start_grace_complete.py
```

**Or use standard startup:**
```bash
cd backend
uvicorn app:app --reload
```

---

## 📊 API Endpoints

### Get Lab Status

```bash
curl http://localhost:8000/sandbox-lab/status
```

**Response:**
```json
{
  "total_experiments": 5,
  "sandbox_experiments": 2,
  "trial_experiments": 1,
  "production_experiments": 1,
  "rejected_experiments": 1,
  "active_trials_count": 1,
  "awaiting_approval_count": 0,
  "average_trust_score": 0.78,
  "average_improvement": 15.3,
  "auto_approved": 0,
  "user_approved": 1
}
```

---

### Propose an Experiment

Grace (via Mirror) can propose improvements:

```bash
curl -X POST http://localhost:8000/sandbox-lab/experiments/propose \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Improved Semantic Chunking",
    "description": "Use contrastive learning for better chunk boundaries",
    "experiment_type": "algorithm_improvement",
    "motivation": "Mirror detected 15% of chunk boundaries split sentences awkwardly. This algorithm uses embeddings to find semantic breaks.",
    "proposed_by": "grace_mirror",
    "initial_trust_score": 0.7
  }'
```

**Response:**
```json
{
  "experiment_id": "EXP-a1b2c3d4e5f6",
  "name": "Improved Semantic Chunking",
  "status": "sandbox",
  "trust_scores": {
    "initial": 0.7,
    "current": 0.7
  },
  "gates": {
    "can_enter_sandbox": true,
    "can_enter_trial": false,
    "can_promote_to_production": false,
    "can_auto_approve": false
  }
}
```

Note: With trust score 0.7 ≥ 0.3, it **automatically entered sandbox**!

---

### Record Implementation

Grace writes the code for her improvement:

```bash
curl -X POST http://localhost:8000/sandbox-lab/experiments/EXP-a1b2c3d4e5f6/implementation \
  -H "Content-Type": application/json" \
  -d '{
    "implementation_code": "def improved_chunking(text):\n    # Use embeddings for semantic boundaries\n    ...",
    "files_modified": ["backend/ingestion/service.py"]
  }'
```

---

### Start 90-Day Trial

Once implementation is ready and trust ≥ 0.6:

```bash
curl -X POST http://localhost:8000/sandbox-lab/experiments/EXP-a1b2c3d4e5f6/trial \
  -H "Content-Type: application/json" \
  -d '{
    "baseline_metrics": {
      "chunk_quality_score": 0.72,
      "average_chunk_size": 450,
      "sentence_split_rate": 0.15
    }
  }'
```

**Response:**
```json
{
  "experiment_id": "EXP-a1b2c3d4e5f6",
  "status": "trial",
  "trial": {
    "duration_days": 90,
    "days_elapsed": 0,
    "days_remaining": 90,
    "trial_started_at": "2026-01-11T20:00:00"
  }
}
```

Trial will complete on **2026-04-11** (90 days later).

---

### Record Trial Results

As Grace processes files with the experimental algorithm, record results:

```bash
curl -X POST http://localhost:8000/sandbox-lab/experiments/EXP-a1b2c3d4e5f6/trial/record \
  -H "Content-Type: application/json" \
  -d '{
    "success": true,
    "metrics": {
      "chunk_quality_score": 0.85,
      "average_chunk_size": 445,
      "sentence_split_rate": 0.03
    }
  }'
```

**What This Does:**
- Records 1 successful data point
- Updates metrics (chunk quality improved from 0.72 → 0.85!)
- Calculates improvement: **18.1% improvement**
- Updates trust score using neural trust scorer
- Checks if trial is complete

---

### List All Experiments

```bash
curl http://localhost:8000/sandbox-lab/experiments
```

**Filter by status:**
```bash
curl "http://localhost:8000/sandbox-lab/experiments?status=trial"
```

**Filter by type:**
```bash
curl "http://localhost:8000/sandbox-lab/experiments?experiment_type=algorithm_improvement"
```

---

### Get Active Trials

```bash
curl http://localhost:8000/sandbox-lab/experiments/active/trials
```

**Response:**
```json
{
  "active_trials": [
    {
      "experiment_id": "EXP-a1b2c3d4e5f6",
      "name": "Improved Semantic Chunking",
      "status": "trial",
      "trial": {
        "days_elapsed": 45,
        "days_remaining": 45,
        "data_points": 1523,
        "success_rate": 0.94
      }
    }
  ],
  "count": 1
}
```

---

### Get Experiments Awaiting Approval

After 90-day trial completes successfully:

```bash
curl http://localhost:8000/sandbox-lab/experiments/awaiting/approval
```

**Response:**
```json
{
  "awaiting_approval": [
    {
      "experiment_id": "EXP-a1b2c3d4e5f6",
      "name": "Improved Semantic Chunking",
      "status": "validated",
      "trust_scores": {
        "current": 0.92
      },
      "metrics": {
        "improvement_percentage": 18.1
      },
      "trial": {
        "data_points": 2847,
        "success_rate": 0.94
      }
    }
  ],
  "count": 1,
  "auto_approve_candidates": [
    {
      "experiment_id": "EXP-a1b2c3d4e5f6",
      "can_auto_approve": false,
      "reason": "Trust score 0.92 < 0.95 (needs 0.95 for auto-approval)"
    }
  ]
}
```

---

### Approve for Production

User reviews and approves:

```bash
curl -X POST http://localhost:8000/sandbox-lab/experiments/EXP-a1b2c3d4e5f6/approve \
  -H "Content-Type: application/json" \
  -d '{
    "approved_by": "user",
    "notes": "Excellent improvement! Deployment approved."
  }'
```

**Response:**
```json
{
  "experiment_id": "EXP-a1b2c3d4e5f6",
  "status": "production",
  "production_at": "2026-04-11T15:30:00",
  "approved_by": "user",
  "message": "Experiment promoted to production!"
}
```

**Grace is now better!** 🎉

---

### Reject Experiment

If user decides not to deploy:

```bash
curl -X POST http://localhost:8000/sandbox-lab/experiments/EXP-a1b2c3d4e5f6/reject
```

---

## 🎯 Trust Score Thresholds

```bash
curl http://localhost:8000/sandbox-lab/thresholds
```

**Response:**
```json
{
  "sandbox_entry": 0.3,
  "trial_entry": 0.6,
  "production_ready": 0.85,
  "auto_approve": 0.95,
  "descriptions": {
    "sandbox_entry": "Minimum trust to enter sandbox testing",
    "trial_entry": "Minimum trust to start 90-day live trial",
    "production_ready": "Minimum trust for production promotion",
    "auto_approve": "Trust level for automatic approval (still notifies user)"
  }
}
```

---

## 🔥 Example: Complete Flow

### 1. Mirror Detects Improvement Opportunity

Grace's Mirror observes that chunking quality could be better:

```python
# In Mirror self-modeling system
improvement_opportunity = {
    "pattern": "chunking_quality_low",
    "current_metric": 0.72,
    "potential_improvement": "Use contrastive learning",
    "expected_improvement": 0.15
}
```

### 2. Propose Experiment

```bash
curl -X POST http://localhost:8000/sandbox-lab/experiments/propose \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Contrastive Learning Chunking",
    "description": "Use contrastive learning to identify better chunk boundaries",
    "experiment_type": "algorithm_improvement",
    "motivation": "Current chunking splits 15% of sentences awkwardly. This approach uses similarity between embeddings to find natural semantic breaks.",
    "initial_trust_score": 0.7
  }'
```

**Result:** Experiment `EXP-xyz789` created, auto-entered sandbox (trust 0.7 ≥ 0.3)

### 3. Grace Implements

```bash
curl -X POST http://localhost:8000/sandbox-lab/experiments/EXP-xyz789/implementation \
  -H "Content-Type: application/json" \
  -d '{
    "implementation_code": "# Contrastive learning chunking algorithm...",
    "files_modified": ["backend/ingestion/service.py"]
  }'
```

### 4. Start Trial

```bash
curl -X POST http://localhost:8000/sandbox-lab/experiments/EXP-xyz789/trial \
  -H "Content-Type: application/json" \
  -d '{
    "baseline_metrics": {
      "chunk_quality": 0.72,
      "sentence_split_rate": 0.15
    }
  }'
```

**Trial starts:** 90 days of testing with live data

### 5. Grace Uses Experimental Algorithm

For the next 90 days, whenever a file is ingested, Grace:
- Uses the experimental chunking algorithm
- Records whether it succeeded or failed
- Tracks metrics (chunk quality, sentence splits, etc.)

```bash
# Each time a file is processed (automated):
curl -X POST http://localhost:8000/sandbox-lab/experiments/EXP-xyz789/trial/record \
  -H "Content-Type: application/json" \
  -d '{
    "success": true,
    "metrics": {
      "chunk_quality": 0.87,
      "sentence_split_rate": 0.03
    }
  }'
```

**After 90 days:**
- 3,542 files processed
- 94% success rate
- Chunk quality: 0.72 → 0.87 (**20.8% improvement**)
- Sentence split rate: 0.15 → 0.03 (**80% reduction**)
- Trust score: 0.93

### 6. Validation & Approval Request

Trial completes, experiment moves to "validated" status.

Grace logs an approval request:

```
======================================================================
🔬 EXPERIMENT READY FOR APPROVAL
======================================================================

Experiment ID: EXP-xyz789
Name: Contrastive Learning Chunking
Type: algorithm_improvement

MOTIVATION:
  Current chunking splits 15% of sentences awkwardly. This approach uses
  similarity between embeddings to find natural semantic breaks.

TRIAL RESULTS (90 days):
  Data Points: 3,542
  Success Rate: 94.0%
  Failures: 213
  Trust Score: 0.93/1.00

PERFORMANCE:
  Improvement: 20.8%

METRICS COMPARISON:
  chunk_quality: 0.720 -> 0.870 (+0.150)
  sentence_split_rate: 0.150 -> 0.030 (-0.120)

RECOMMENDATION:
  ⚠️  MANUAL REVIEW: Trust score 0.93 < 0.95
  ⚠️  User approval required before production

TO APPROVE:
  curl -X POST http://localhost:8000/sandbox-lab/experiments/EXP-xyz789/approve

TO REJECT:
  curl -X POST http://localhost:8000/sandbox-lab/experiments/EXP-xyz789/reject

======================================================================
```

### 7. User Approves

```bash
curl -X POST http://localhost:8000/sandbox-lab/experiments/EXP-xyz789/approve \
  -H "Content-Type: application/json" \
  -d '{"approved_by": "user", "notes": "Great improvement!"}'
```

### 8. Production Deployment

Experiment promoted to production. Grace's chunking is now **20.8% better**!

---

## 🎨 Experiment Types

| Type | Description | Risk Level |
|------|-------------|------------|
| `algorithm_improvement` | Better versions of existing algorithms | Medium |
| `performance_optimization` | Speed/memory improvements | Low |
| `error_reduction` | Fix bugs autonomously | Low |
| `learning_enhancement` | Better learning algorithms | Medium |
| `self_modeling` | Improve self-awareness | Medium |
| `new_capability` | Entirely new features | High |

---

## 🛡️ Safety Features

### 1. Isolation
- Experiments run in **sandbox** first
- No impact on production until approved
- Implementation tracked with hash

### 2. Trust Scoring
- **Neural trust scorer** evaluates experiments
- Trust must increase through each gate
- Low trust = automatic rejection

### 3. 90-Day Trial Period
- **Long validation** with real data
- Continuous monitoring
- High success rate required (≥90%)

### 4. User Approval Gates
- **Always requests approval** before production
- Can auto-approve if trust ≥ 0.95 and improvement ≥ 20%
- User can reject at any stage

### 5. Performance Validation
- Must show **measurable improvement**
- Baseline vs experiment metrics tracked
- Regression = automatic rejection

---

## 📈 Integration with Existing Systems

The Sandbox Lab integrates with:

### 1. Mirror Self-Modeling
- Mirror **proposes experiments** based on observations
- Detects patterns that could be improved
- Monitors experiment performance

### 2. ML Intelligence
- Uses **neural trust scorer** for trust calculation
- Applies **uncertainty quantification** to risk
- Leverages **meta-learning** for hyperparameter tuning

### 3. Self-Healing System
- If experiment causes errors → **auto-rollback**
- Self-healing monitors trial experiments
- Can reject experiments that cause anomalies

### 4. Genesis Keys
- Every experiment gets **Genesis Key**
- Complete audit trail of changes
- Can rollback to previous version

### 5. Autonomous Learning
- Experiments can improve **learning algorithms**
- Better study/practice strategies
- Enhanced memory consolidation

---

## 🔍 Monitoring & Observability

### Check Active Experiments

```bash
# All experiments
curl http://localhost:8000/sandbox-lab/experiments

# Only trials
curl "http://localhost:8000/sandbox-lab/experiments?status=trial"

# Awaiting approval
curl http://localhost:8000/sandbox-lab/experiments/awaiting/approval

# Lab statistics
curl http://localhost:8000/sandbox-lab/status
```

---

## 💡 Use Cases

### 1. Autonomous Bug Fixes
Grace detects a pattern where certain PDFs fail to parse:
- Proposes: "Better PDF parsing with fallback strategies"
- Implements fix in sandbox
- 90-day trial shows 98% success vs 85% baseline
- Auto-approved for production

### 2. Performance Optimization
Grace notices embedding generation is slow:
- Proposes: "Batch embedding with dynamic batch size"
- Implements optimization
- Trial shows 3x speed improvement
- User approves → production

### 3. Learning Enhancement
Grace observes memory consolidation could be better:
- Proposes: "Spaced repetition with forgetting curves"
- Implements algorithm
- Trial shows 40% better retention
- Auto-approved (trust 0.97, improvement 40%)

### 4. Self-Modeling Improvement
Grace's mirror detects it's missing patterns:
- Proposes: "Add temporal pattern detection"
- Implements new detection algorithm
- Trial shows 25% more patterns detected
- User approves

---

## 🎓 Best Practices

### For Grace (Automated)

1. **Propose conservatively** - Start with small, focused improvements
2. **High initial trust** - Build confidence with good motivation
3. **Comprehensive testing** - Use sandbox thoroughly before trial
4. **Track everything** - Record all metrics, successes, failures
5. **Learn from rejections** - Adjust approach based on feedback

### For Users

1. **Review regularly** - Check awaiting approval periodically
2. **Trust the process** - 90-day trial is thorough validation
3. **Examine metrics** - Look at improvement percentages
4. **Read motivation** - Understand why Grace thinks it's valuable
5. **Approve good work** - If trial passed, trust often justified

---

## 🚀 Next Steps

The Sandbox Lab is **operational and integrated**. To use it:

1. **Start Grace**: `python backend/scripts/start_grace_complete.py`
2. **Monitor lab**: Visit http://localhost:8000/sandbox-lab/status
3. **Let Grace experiment**: She'll propose improvements via Mirror
4. **Review proposals**: Check http://localhost:8000/sandbox-lab/experiments
5. **Approve successes**: Promote validated experiments to production

---

## 📊 Current Status

**Sandbox Lab is:**
- ✅ **Built** - Complete implementation
- ✅ **Integrated** - Connected to app.py (20 routers now!)
- ✅ **API Ready** - 12 endpoints available
- ✅ **ML Enabled** - Neural trust scoring active
- ✅ **Safe** - Multi-gate approval workflow
- ✅ **Autonomous** - Can run experiments independently

**Grace can now improve herself autonomously!** 🎉

---

## 📚 API Reference

Full API documentation available at:
- http://localhost:8000/docs#/sandbox-lab

12 endpoints:
- `GET /sandbox-lab/status`
- `POST /sandbox-lab/experiments/propose`
- `POST /sandbox-lab/experiments/{id}/sandbox`
- `POST /sandbox-lab/experiments/{id}/implementation`
- `POST /sandbox-lab/experiments/{id}/trial`
- `POST /sandbox-lab/experiments/{id}/trial/record`
- `POST /sandbox-lab/experiments/{id}/approve`
- `POST /sandbox-lab/experiments/{id}/reject`
- `GET /sandbox-lab/experiments`
- `GET /sandbox-lab/experiments/{id}`
- `GET /sandbox-lab/experiments/active/trials`
- `GET /sandbox-lab/experiments/awaiting/approval`
- `GET /sandbox-lab/thresholds`

---

**Grace's Autonomous Sandbox Lab: Where AI improves AI** 🔬🤖
