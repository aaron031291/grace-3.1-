# Create Desktop Shortcut for Grace

Quick guide to add Grace launcher to your desktop like other apps.

## Method 1: PowerShell Script (Easiest)

1. Open PowerShell in the Grace project folder
2. Run:
   ```powershell
   powershell -ExecutionPolicy Bypass -File create_desktop_shortcut.ps1
   ```
3. ✓ Shortcut created on your desktop!

## Method 2: Python Script

1. Make sure you have `pywin32` installed:
   ```bash
   pip install pywin32
   ```
2. Run:
   ```bash
   python create_desktop_shortcut.py
   ```
3. ✓ Shortcut created!

## Method 3: Manual Creation (No Scripts Needed)

1. **Right-click on your desktop** → **New** → **Shortcut**
2. In the "Type the location of the item" field, browse to:
   ```
   C:\Users\aaron\grace 3.1\grace-3.1-\launch_grace.bat
   ```
   (Or use the full path: `"C:\Users\aaron\grace 3.1\grace-3.1-\launch_grace.bat"`)
3. Click **Next**
4. Name it **"Grace"** (or whatever you want)
5. Click **Finish**

### Optional: Change Icon

1. Right-click the shortcut → **Properties**
2. Click **Change Icon**
3. Choose an icon:
   - Browse to: `C:\Windows\System32\shell32.dll`
   - Pick any icon you like (folder icons work well)
4. Click **OK** → **Apply** → **OK**

## What the Shortcut Does

When you double-click the "Grace" shortcut on your desktop:
1. Opens a command window
2. Changes to the Grace project directory
3. Runs `python launch_grace.py`
4. Launches Grace with the strict launcher
5. Shows Grace startup messages

## Customize the Icon (Advanced)

To use a custom Grace icon:

1. Create or download a `.ico` file for Grace
2. Place it in the project root (e.g., `grace.ico`)
3. Edit `create_desktop_shortcut.ps1` or recreate the shortcut
4. Point IconLocation to your `.ico` file:
   ```powershell
   $shortcut.IconLocation = "C:\Users\aaron\grace 3.1\grace-3.1-\grace.ico"
   ```

## Troubleshooting

### "Python not found" error
- Make sure Python is in your PATH
- Or edit `launch_grace.bat` to use full Python path:
  ```batch
  "C:\Python39\python.exe" launch_grace.py
  ```

### Shortcut opens but closes immediately
- Check that `launch_grace.py` exists in the project root
- Check Python path is correct
- Remove `pause` from `launch_grace.bat` if you want it to close automatically (or keep it to see errors)

### Want to hide the console window?
- Use `launch_grace.vbs` instead (see below)

## Alternative: Hidden Console Window

Create `launch_grace.vbs`:

```vbscript
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\aaron\grace 3.1\grace-3.1-"
WshShell.Run "python launch_grace.py", 0, False
Set WshShell = Nothing
```

Then point the shortcut to `launch_grace.vbs` instead of `.bat`. The console window will be hidden.

---

**That's it!** You now have Grace on your desktop, just like VS Code, Docker, etc.
