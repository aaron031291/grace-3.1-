# Quick Start: Reset & Re-ingestion

## TL;DR (5 seconds)

```bash
cd /home/umer/Public/projects/grace_3/backend
python reset_and_reingest.py
```

Done! Your knowledge base is now reset and all files are re-ingested.

## What Happened

✅ Deleted all documents from database  
✅ Deleted all vectors from Qdrant  
✅ Reset file tracking state  
✅ Re-ingested every file in `knowledge_base/`  
✅ Showed real-time progress for each file

## What You'll See

```
[INGESTION START] NEW FILE
  File: text.txt
  Size: 1.2 KB
  ...

[INGESTION SUCCESS] text.txt
  Document ID: 1
  Processing time: 0.45 seconds
  Content length: 1234 characters
  ...
```

## Summary

When complete:

- **Total processed:** 47
- **Successful:** 47
- **Failed:** 0
- **Duration:** 28.5 seconds

## You're Done! 🎉

Your knowledge base is ready:

- All files are indexed
- All vectors are stored
- All search/RAG features work
- Auto-ingestion monitor is running

## If You Want Details

Read these files:

- `RESET_REINGEST_GUIDE.md` - Complete guide with examples
- `INGESTION_LOGGING_GUIDE.md` - Understanding the logs
- `RESET_REINGEST_SUMMARY.md` - Technical summary

## Troubleshooting

**Script fails?** Make sure:

- You're in the `backend/` directory
- Qdrant is running (on localhost:6333)
- You have write permissions

**Files not ingesting?** Check:

- Files are in `knowledge_base/` directory
- File extensions are supported (see guide)
- Database is accessible

## Watch Live Progress

```bash
python reset_and_reingest.py 2>&1 | tail -f
```

Or save to file:

```bash
python reset_and_reingest.py > ingestion.log 2>&1
```

## Reset Again Later?

Just run the script again - it resets everything:

```bash
python reset_and_reingest.py
```

No configuration needed!
