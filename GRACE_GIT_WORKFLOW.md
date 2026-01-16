# Grace Git Workflow Guide

## Environment ID System

Your environment is configured with:
- **Environment ID**: `aaron`
- **Developer Name**: `aaron`
- **Auto-commit to develop**: `true`

This ID is stored in git config and allows the system to recognize your commits.

## Branch Structure

- **`main`**: Production-ready code
- **`develop`**: Development branch (your default working branch)
- **`umer`**: Umer's development branch

## How to Commit

### Option 1: Using the Grace Commit Script (Recommended)

**Commit to develop:**
```bash
python grace-commit.py commit "Your commit message"
```

Or on Windows:
```bash
grace-commit.bat commit "Your commit message"
```

This will:
1. Automatically switch to `develop` branch
2. Stage all changes
3. Commit with your message
4. Push to `origin/develop`

**Merge develop to main:**
```bash
python grace-commit.py merge
```

Or on Windows:
```bash
grace-commit.bat merge
```

This will:
1. Switch to `main` branch
2. Merge `develop` into `main`
3. Push to `origin/main`

### Option 2: Manual Git Commands

**Commit to develop:**
```bash
git checkout develop
git add -A
git commit -m "Your commit message"
git push origin develop
```

**Merge to main:**
```bash
git checkout main
git merge develop
git push origin main
```

## Checking Your Environment ID

To verify your environment ID:
```bash
git config --local grace.env-id
```

## Workflow

1. **Work on develop branch** - All your commits go here first
2. **Test and verify** - Make sure everything works on develop
3. **Merge to main** - When ready, merge develop to main using the script

## Important Notes

- The system recognizes you by your Environment ID (`aaron`)
- All commits automatically go to `develop` first
- Only merge to `main` when code is production-ready
- Never commit directly to `main` - always go through `develop`
- Umer's branch (`umer`) is separate and should not be touched
