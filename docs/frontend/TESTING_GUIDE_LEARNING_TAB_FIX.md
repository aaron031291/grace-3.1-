# Testing Guide: Learning Tab Backend Connection Fix

**Date**: January 30, 2026  
**Fix**: Frontend Learning Tab → Backend Autonomous Learning API Integration  
**Priority**: Critical #1

---

## What Was Fixed

### Backend Improvements (`backend/api/autonomous_learning.py`)
1. ✅ **Auto-start orchestrator** - System now starts automatically if not running when tasks submitted
2. ✅ **Input validation** - Empty topics/skills are rejected with clear error messages
3. ✅ **Better error handling** - Specific error messages instead of generic failures
4. ✅ **Improved responses** - Returns task_id, queue_size, and descriptive messages
5. ✅ **New endpoint** - `GET /autonomous-learning/tasks/{task_id}/status` for status tracking

### Frontend Improvements (`frontend/src/components/LearningTab.jsx`)
1. ✅ **Better success messages** - Shows task ID and queue size
2. ✅ **Auto-refresh status** - Refreshes orchestrator status after task submission
3. ✅ **Improved error display** - Clear ✓/✗ indicators for success/failure

### UI Improvements (`frontend/src/components/LearningTab.css`)
1. ✅ **Status styling** - Green background for success, red for errors
2. ✅ **Multi-line support** - Task ID shown on separate line
3. ✅ **Left border accent** - Visual indicator for status type

---

## Step-by-Step Testing Instructions

### Prerequisites
1. Make sure backend server is running on port 8000
2. Make sure frontend is running on port 5173
3. Open browser to http://localhost:5173

### Test 1: Submit Study Task

#### Steps:
1. Navigate to **Learning Tab** in the UI
2. Locate the **Training Actions** section (bottom of the page)
3. In the "Study topic" input field, enter: `Python decorators`
4. Click the **📖 Start Study Session** button

#### Expected Results:
```
✓ Study task queued successfully. Subagent will process in background. (X tasks in queue)
Task ID: study-0
```

**Success Indicators**:
- ✅ Green background message appears
- ✅ Task ID is displayed
- ✅ Queue size shown in parentheses
- ✅ No error message

**If you see errors**:
- ❌ "Topic cannot be empty" → Input validation working correctly
- ❌ "Failed to submit study task: ..." → Check backend logs for details
- ❌ No message appears → Check browser console (F12) for errors

---

### Test 2: Submit Practice Task

#### Steps:
1. Stay in **Learning Tab** → **Training Actions** section
2. In "Practice skill" input: `Python programming`
3. In "Practice task" input: `Write a function to calculate fibonacci numbers`
4. Click **⚡ Start Practice Session** button

#### Expected Results:
```
✓ Practice task queued successfully. Subagent will process in background. (X tasks in queue)
Task ID: practice-0
```

**Success Indicators**:
- ✅ Green background message appears
- ✅ Task ID is displayed
- ✅ Queue size shown in parentheses

---

### Test 3: Test Empty Input Validation

#### Steps:
1. Clear the "Study topic" field completely
2. Click **📖 Start Study Session** button

#### Expected Results:
```
✗ Study task failed: Topic cannot be empty
```

**Success Indicators**:
- ✅ Red background error message
- ✅ Clear validation message
- ✅ Task NOT submitted to backend

---

### Test 4: Check Backend Orchestrator Status

#### Steps:
1. Open a new terminal
2. Run: `curl http://localhost:8000/api/autonomous-learning/status`

#### Expected Results (JSON):
```json
{
  "status": "running",
  "total_subagents": 6,
  "study_agents": 3,
  "practice_agents": 2,
  "study_queue_size": 1,
  "practice_queue_size": 1,
  "total_tasks_submitted": 2,
  "total_tasks_completed": 0
}
```

**Success Indicators**:
- ✅ `"status": "running"` (orchestrator started automatically)
- ✅ `total_tasks_submitted` matches number of tasks you submitted
- ✅ Queue sizes show pending tasks

---

### Test 5: Check Task Status Endpoint

#### Steps:
1. Use the task_id from Test 1 (e.g., `study-0`)
2. Run: `curl http://localhost:8000/api/autonomous-learning/tasks/study-0/status`

#### Expected Results (JSON):
```json
{
  "task_id": "study-0",
  "status": "tracking_limited",
  "message": "Task submitted successfully. Check orchestrator status for overall progress.",
  "orchestrator_status": {
    "running": true,
    "tasks_completed": 0,
    "study_queue_size": 1,
    "practice_queue_size": 1
  }
}
```

**Note**: Full task tracking requires expanded shared state (future enhancement). For now, this confirms task was queued.

---

### Test 6: Monitor Backend Logs

#### Steps:
1. Watch the backend terminal output
2. Submit a study task from the UI

#### Expected Log Messages:
```
INFO:     [API] Auto-started orchestrator for study task submission
INFO:     [ORCHESTRATOR] Study task submitted: Python decorators
INFO:     [study-agent-0] Studying 'Python decorators'...
INFO:     [study-agent-0] Studied 'Python decorators': 5 concepts in 2.3s
```

**Success Indicators**:
- ✅ "Auto-started orchestrator" appears (if first task)
- ✅ "Study task submitted" confirms queue entry
- ✅ Agent picks up task and processes it
- ✅ Results logged with timing

---

### Test 7: Verify Auto-Start Functionality

#### Steps:
1. Stop the backend server (Ctrl+C)
2. Restart the backend: `cd backend && uvicorn app:app --reload --port 8000`
3. **WITHOUT** manually starting the orchestrator, submit a study task from UI

#### Expected Behavior:
- ✅ Task submission should succeed
- ✅ Backend logs show: `[API] Auto-started orchestrator for study task submission`
- ✅ Green success message in frontend
- ✅ Orchestrator status shows "running": true

**This confirms the fix**: Orchestrator starts automatically when needed, no manual intervention required.

---

## Common Issues & Solutions

### Issue 1: "Connection refused" error
**Cause**: Backend not running  
**Solution**: Start backend: `cd backend && uvicorn app:app --reload --port 8000`

---

### Issue 2: Empty success message (no task ID)
**Cause**: Backend returned unexpected response format  
**Solution**: 
1. Check backend logs for errors
2. Verify autonomous_learning.py changes were saved
3. Restart backend server

---

### Issue 3: Tasks submitted but never processed
**Cause**: Orchestrator started but subagents crashed  
**Solution**:
1. Check backend logs for Python errors
2. Ensure `LIGHTWEIGHT_MODE=true` in `.env` (for development)
3. Check if database is accessible
4. Verify `knowledge_base/` folder exists

---

### Issue 4: "Failed to submit: 'LearningOrchestrator' object has no attribute 'study_queue'"
**Cause**: Using thread-based orchestrator on Windows but accessing process-based attributes  
**Solution**: Check `backend/api/autonomous_learning.py` line 22-25 - should auto-select correct orchestrator

---

## Success Criteria

✅ **All tests passed if you see**:
1. Green success messages for valid submissions
2. Red error messages for invalid submissions (empty fields)
3. Task IDs displayed in responses
4. Backend logs show orchestrator auto-start
5. Backend logs show agents processing tasks
6. Status endpoint returns orchestrator details

---

## What to Report

### If Tests Pass:
```
✅ All tests passed!

Test Results:
- Study task submission: SUCCESS
- Practice task submission: SUCCESS
- Empty validation: SUCCESS
- Orchestrator auto-start: SUCCESS
- Backend logs: CLEAN
- Task processing: WORKING
```

### If Tests Fail:
```
❌ Test failures:

Failed Test: [Test number and name]
Error Message: [Exact error from UI or backend]
Backend Logs: [Copy relevant log lines]
Browser Console: [F12 → Console tab errors]
```

---

## Next Steps After Testing

### If Successful:
1. Test with real learning content (add PDFs to knowledge_base/)
2. Monitor task completion rates
3. Check memory mesh for learned concepts
4. Test proactive learning suggestions

### If Failed:
1. Share test results with developer
2. Provide screenshots of errors
3. Share backend log output
4. Include browser console errors (F12)

---

## Technical Details (For Reference)

### Files Modified:
- `backend/api/autonomous_learning.py` - Lines 350-497 (study/practice endpoints + validation)
- `frontend/src/components/LearningTab.jsx` - Lines 221-268 (submission handlers)
- `frontend/src/components/LearningTab.css` - Added `.training-action-status` styles

### Key Changes:
1. Auto-start check: `if not status.get("running", False): orchestrator.start()`
2. Input validation: `if not request.topic or len(request.topic.strip()) == 0`
3. Better messages: `"message": "Study task queued successfully..."`
4. Status endpoint: `GET /tasks/{task_id}/status`

---

**Testing Time**: ~15 minutes  
**Required Setup**: Backend + Frontend running  
**Difficulty**: Easy  

Good luck! 🚀
