# How to Get Stability Report

## Quick Start

The stability proof system runs automatically when Grace starts. To get a report:

### Option 1: Via API (Recommended)

1. **Start Grace Server**:
   ```bash
   cd backend
   python app.py
   ```

2. **Wait for server to start** (you'll see stability monitor initialization)

3. **Run the report script**:
   ```bash
   python scripts/get_stability_report.py
   ```

### Option 2: Direct API Call

If Grace is running, you can get the report directly:

```bash
# Get current stability proof
curl http://localhost:8000/health/stability-proof

# Get monitor status
curl http://localhost:8000/health/stability-monitor/status

# Force immediate check
curl -X POST http://localhost:8000/health/stability-monitor/force-check
```

### Option 3: Browser

Open in browser:
- `http://localhost:8000/health/stability-proof`
- `http://localhost:8000/health/stability-monitor/status`

## What the Report Shows

1. **Overall Status**
   - Stability level (PROVABLY_STABLE, STABLE, PARTIALLY_STABLE, UNSTABLE)
   - Overall confidence percentage
   - System state hash
   - Verification status

2. **Component Status**
   - 8 component checks:
     - Database stability
     - Cognitive engine stability
     - Invariant satisfaction
     - State machine validity
     - Deterministic operations
     - System health
     - Error rate
     - Component consistency
   - Each with confidence score and violations

3. **Mathematical Proof**
   - Theorem statement
   - Premises
   - Proof steps
   - Conclusion
   - Verification status

4. **Monitor Status**
   - Real-time monitor status
   - Total checks performed
   - Uptime
   - Recent alerts

5. **Recommendations**
   - Action items based on stability level

## Report File

The report is also exported to `stability_report.json` in the project root for programmatic access.

## Troubleshooting

**"Cannot connect to Grace server"**
- Ensure Grace server is running
- Check if server is on port 8000
- Verify firewall isn't blocking connections

**"Server not responding"**
- Check server logs for errors
- Verify database is accessible
- Check if all dependencies are installed

## Automatic Monitoring

The system automatically:
- Checks stability every 60 seconds
- Detects degradation
- Creates alerts
- Maintains history

You can view the latest status anytime via the API endpoints.
