# Version Control Feature Documentation

## Overview

The Version Control feature provides comprehensive Git repository tracking and visualization directly from the Grace UI. Built with **Dulwich** (Python's pure Git implementation), it enables users to:

- View complete commit history with timeline visualization
- Explore file tree structure at any commit
- Review changes and diffs for each commit
- Track module/directory history and statistics
- Revert to any previous commit with safety confirmation

## Architecture

### Backend Components

#### 1. Git Service (`backend/version_control/git_service.py`)

Core service class that interfaces with Dulwich to perform Git operations.

**Key Methods:**

- `get_commits()` - Retrieve paginated commit history
- `get_commit_details()` - Get detailed information for a specific commit
- `get_commit_diff()` - Get file changes in a commit
- `get_file_history()` - Get commit history for specific files
- `get_tree_structure()` - Get file tree at a commit
- `get_module_statistics()` - Get directory/module statistics
- `revert_to_commit()` - Revert working directory to a commit
- `get_diff_between_commits()` - Compare two commits

#### 2. API Routes (`backend/api/version_control.py`)

FastAPI endpoints that expose Git operations to the frontend.

**Endpoints:**

- `GET /api/version-control/commits` - List commits with pagination
- `GET /api/version-control/commits/{sha}` - Get commit details
- `GET /api/version-control/commits/{sha}/diff` - Get commit diff
- `GET /api/version-control/diff` - Compare two commits
- `GET /api/version-control/files/{path}/history` - Get file history
- `GET /api/version-control/tree` - Get file tree structure
- `GET /api/version-control/modules/statistics` - Get module stats
- `POST /api/version-control/revert` - Revert to commit

### Frontend Components

#### 1. Main Component (`VersionControl.jsx`)

Master component managing the entire version control interface.

**Features:**

- Tab navigation between Timeline, Tree, Changes, and Modules views
- Commit selection and details display
- Error handling and loading states
- Revert modal management

#### 2. Sub-Components

##### CommitTimeline (`version_control/CommitTimeline.jsx`)

Interactive timeline visualization of commits with SVG backdrop.

**Features:**

- Scrollable commit list with visual timeline
- Latest commit indicator (highlighted in orange)
- Expandable commit details
- Quick revert action button

##### GitTree (`version_control/GitTree.jsx`)

File tree structure explorer with directory expansion.

**Features:**

- Hierarchical file/directory visualization
- Expandable folders with smooth animations
- Color-coded icons (yellow for directories, blue for files)
- SVG grid background pattern

##### DiffViewer (`version_control/DiffViewer.jsx`)

Visual diff summary showing file changes.

**Features:**

- Change status badges (added, modified, deleted, renamed)
- Line addition/deletion counts
- Color-coded statistics summary
- File list with detailed stats

##### ModuleHistory (`version_control/ModuleHistory.jsx`)

Module/directory commit tracking and statistics.

**Features:**

- Module commit count badges
- Expandable module details
- Recent commits for each module
- SVG icons for directories and files

##### RevertModal (`version_control/RevertModal.jsx`)

Safety confirmation modal before reverting.

**Features:**

- Warning message with icon
- Full commit details preview
- Cancel/Confirm buttons
- Backdrop blur effect

## Installation

### Backend Setup

1. Install Dulwich in your Python environment:

```bash
pip install dulwich
```

Or update requirements.txt and install:

```bash
pip install -r requirements.txt
```

2. The Git service automatically initializes a repository at the project root if one doesn't exist.

### Frontend Setup

No additional installations needed - all components use React hooks and CSS3 only.

## Usage

### Access Version Control Tab

1. Click the "Version Control" button in the sidebar (bottom of the tab list)
2. The interface will load and display the commit history

### View Timeline

- **Default View**: Shows all commits in reverse chronological order
- **Latest Commit**: Highlighted in orange with visual indicator
- **Expand Commit**: Click to see full SHA, message, and committer details
- **Revert**: Click "Revert to this commit" button to open confirmation modal

### Explore File Tree

1. Click the "Tree" tab
2. Directories expand on click to show contents
3. Color coding helps identify file types

### Review Changes

1. Click the "Changes" tab
2. See file modifications grouped by status
3. Line counts show additions and deletions

### Track Module History

1. Click the "Modules" tab
2. View modules and their commit counts
3. Expand modules to see recent changes
4. Quick access to commit details

### Revert to Previous Version

1. Select a commit from the timeline
2. Click "Revert to this commit" button
3. Review commit details in the modal
4. Confirm revert (this changes all working directory files)

## API Response Examples

### Get Commits

```json
{
  "commits": [
    {
      "sha": "abc1234...",
      "message": "Initial commit",
      "author": "John Doe",
      "author_email": "john@example.com",
      "committer": "John Doe",
      "timestamp": "2024-01-15T10:30:00",
      "parent_shas": []
    }
  ],
  "total": 1
}
```

### Get Commit Diff

```json
{
  "commit_sha": "abc1234...",
  "files_changed": [
    {
      "path": "src/components/App.jsx",
      "status": "modified",
      "additions": 15,
      "deletions": 3
    }
  ],
  "stats": {
    "additions": 15,
    "deletions": 3,
    "files_modified": 1
  }
}
```

## Styling

All components use custom CSS with:

- Dark theme (background: #0f0f0f, #1a1a1a)
- Accent color: #4a9eff (blue)
- Danger color: #d97706 (orange/yellow for destructive actions)
- SVG-based icons without emojis
- Smooth transitions and hover effects

### CSS Files

- `VersionControl.css` - Main container and layout
- `version_control/CommitTimeline.css` - Timeline styling
- `version_control/GitTree.css` - Tree view styling
- `version_control/DiffViewer.css` - Diff display styling
- `version_control/ModuleHistory.css` - Module tracking styling
- `version_control/RevertModal.css` - Modal styling

## Performance Considerations

1. **Pagination**: Commit list is paginated (default 50, max 100)
2. **Lazy Loading**: Tree and diff data loaded on-demand
3. **Scrolling**: Native browser scrolling with custom scrollbars
4. **SVG Backgrounds**: Used sparingly for visual effects, not performance-critical

## Error Handling

- API errors display in red error banner
- Failed requests show user-friendly messages
- No commit history? "No commits found" message displayed
- All async operations have proper error boundaries

## Future Enhancements

1. **Branch Support**: Switch between different branches
2. **Blame View**: See who modified each line
3. **Merge/Cherry-pick**: Merge or cherry-pick commits
4. **Stash Management**: View and apply stashes
5. **Search**: Filter commits by author, message, or date
6. **Diff Viewer**: Line-by-line diff visualization
7. **Remote Sync**: Push/pull from remote repositories

## Troubleshooting

### "No commits found"

- Ensure the Git repository is properly initialized
- The service automatically creates a repo if missing

### API returns 500 error

- Check backend logs for detailed error messages
- Verify the Git repository path is correct
- Ensure Dulwich is properly installed

### Slow performance with large repos

- Consider paginating further (adjust limit parameter)
- The service is optimized for typical project sizes

## Dependencies

**Backend:**

- `dulwich` - Pure Python Git implementation

**Frontend:**

- React (hooks only)
- CSS3 (no external CSS libraries)
- SVG (inline SVG icons, no icon library)

## License

Part of the Grace project - follow project-specific licensing.
