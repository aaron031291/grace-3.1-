# Folder-Specific Chat - Quick Start Guide

## What's New?

Your Grace application now supports **folder-specific chat histories**. Each chat is tied to a specific folder, meaning:

- ✅ Different folders = Different chat histories
- ✅ One chat cannot cross between folders
- ✅ Easy folder filtering in the UI
- ✅ Clear visual indication of which folder a chat belongs to

## How to Use

### 1. Select a Folder

In the left sidebar (Chat list), you'll see a new **"📁 Select Folder"** button at the top.

```
┌─────────────────────┐
│  Chats              │
│  ────────────────   │
│  [+]                │
├─────────────────────┤
│  📁 Select Folder   │ ← Click here
├─────────────────────┤
│ Chat 1              │
│ Chat 2              │
│ ...                 │
```

### 2. Enter a Folder Path

Click "📁 Select Folder" to see the input form:

```
┌─────────────────────────────────────┐
│ [Enter folder path...     ] [Apply] │
│                           [✕]       │
└─────────────────────────────────────┘
```

Example folder paths:

- `/documents/projects/my-project`
- `/data/research`
- `documents/reports`
- Any path that makes sense for your setup

### 3. Apply the Filter

Type your folder path and click **"Apply"**. The chat list now shows only chats from that folder.

Active folder display:

```
┌──────────────────────────────┐
│ 📁 /documents/projects/my-project [✕] │ ← Blue badge shows active folder
├──────────────────────────────┤
│ Chat for Project A           │
│ Chat for Project B           │
│ ...                          │
```

### 4. Create New Chats in This Folder

Click the **[+]** button to create a new chat. It will automatically be assigned to the selected folder.

On each chat item, you'll see the folder path:

```
┌─────────────────────────┐
│ Chat Title              │
│ 📁 /documents/project   │ ← Folder badge
└─────────────────────────┘
```

### 5. Switch Between Folders

Simply select a different folder path to view chats from a different folder.

### 6. Clear the Filter

Click the **[✕]** button on the active folder badge to clear the filter and see all chats.

## Features

| Feature          | What It Does                                     |
| ---------------- | ------------------------------------------------ |
| Folder Selection | Choose which folder to work with                 |
| Chat Filtering   | See only chats from the selected folder          |
| Folder Badges    | Visual indicator on each chat showing its folder |
| Folder Context   | Chat window header shows which folder you're in  |
| Auto-Assignment  | New chats automatically get the current folder   |
| Clear Filter     | Show all chats by clearing the folder selection  |

## Visual Indicators

### In Chat List

- **Blue highlighted area** = Active folder filter
- **Small gray badge** = Folder path on each chat
- **"Select Folder" button** = No folder selected yet

### In Chat Window

- **Blue badge next to title** = Current folder context
  ```
  My Chat Title 📁 /documents/project
  ```

## Important Notes

- 📌 Each chat belongs to exactly one folder
- 📌 Folder paths are case-sensitive (usually)
- 📌 A chat cannot be moved between folders directly (but can be created in a new folder)
- 📌 Existing chats without a folder path will appear when no filter is applied
- 📌 The folder path is just metadata - it doesn't affect document storage

## API (For Developers)

### Create a chat for a folder

```bash
curl -X POST http://localhost:8000/chats \
  -H "Content-Type: application/json" \
  -d '{"title": "My Chat", "folder_path": "/documents/project"}'
```

### List chats for a specific folder

```bash
curl "http://localhost:8000/chats?folder_path=%2Fdocuments%2Fproject"
```

### List all chats (no filter)

```bash
curl "http://localhost:8000/chats"
```

## Migration (For New Installations)

If you're setting up fresh or need to add this feature to existing database:

```bash
cd backend
python migrate_add_folder_path.py
```

This script:

- ✅ Adds the `folder_path` column if missing
- ✅ Creates an index for fast queries
- ✅ Works with PostgreSQL, MySQL, and SQLite
- ✅ Is safe to run multiple times

## Troubleshooting

### No chats showing up?

- Check if you've selected a folder with the "Select Folder" button
- Click the [✕] button to clear the filter and see all chats
- Make sure the folder path matches exactly (case-sensitive)

### Chats not showing in the selected folder?

- The chats may have been created before selecting that folder
- Chats get their folder assignment at creation time
- You might need to create a new chat with the folder selected

### Can't create a chat?

- Make sure you have a valid folder path selected
- Or clear the folder filter to create a general chat

## Summary

| Before                           | After                             |
| -------------------------------- | --------------------------------- |
| All chats mixed together         | Chats organized by folder         |
| No folder context                | Clear folder badges everywhere    |
| Can't filter by folder           | Easy folder filtering             |
| Confusing when switching folders | Visual feedback of current folder |

Enjoy your organized chats! 🎉
