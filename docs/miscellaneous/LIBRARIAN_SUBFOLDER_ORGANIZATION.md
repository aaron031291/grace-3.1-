# Librarian Subfolder Organization - Complete Guide

## ✅ Yes! Librarian Can Organize into Subfolders and Files

The librarian **fully supports** organizing documents into **nested subfolders** with multiple levels of hierarchy. Files are automatically placed in the appropriate subfolder structure.

---

## 🗂️ Organization Capabilities

### 1. **Automatic Organization Patterns** ✅

The librarian supports multiple organization patterns that create nested subfolders:

#### Pattern: `category/type`
Creates: `documents/{category}/{file_type}/`
```
documents/
├── ai/
│   ├── pdf/
│   │   └── research_paper.pdf
│   └── txt/
│       └── notes.txt
└── research/
    └── pdf/
        └── article.pdf
```

#### Pattern: `category/type/date`
Creates: `documents/{category}/{file_type}/{year-month}/`
```
documents/
├── ai/
│   └── pdf/
│       ├── 2025-01/
│       │   └── paper1.pdf
│       └── 2025-02/
│           └── paper2.pdf
```

#### Pattern: `date/category/type`
Creates: `documents/{year}/{month}/{category}/{file_type}/`
```
documents/
├── 2025/
│   └── 01/
│       ├── ai/
│       │   └── pdf/
│       └── research/
│           └── pdf/
```

#### Pattern: `tags/hierarchy`
Creates: `documents/{tag1}/{tag2}/{tag3}/` (from document tags)
```
documents/
├── ai/
│   └── research/
│       └── machine-learning/
│           └── paper.pdf
```

#### Pattern: `category/tags`
Creates: `documents/{category}/{tag1}/{tag2}/`
```
documents/
├── ai/
│   ├── neural-networks/
│   │   └── paper1.pdf
│   └── transformers/
│       └── paper2.pdf
```

---

### 2. **Tag-Based Subfolder Organization** ✅

Organize documents into nested folders based on their tags:

```python
# Organize by tags (creates nested folders)
result = librarian.file_organizer.organize_by_tags(
    document_id=123,
    tag_names=["ai", "research", "papers", "2025"],
    max_depth=5
)
# Creates: documents/ai/research/papers/2025/document.pdf
```

**API:**
```bash
POST /librarian/organize/{document_id}
{
  "tag_names": ["ai", "research", "papers"],
  "max_depth": 5
}
```

---

### 3. **Explicit Folder Hierarchy** ✅

Organize documents into a specific nested folder structure:

```python
# Organize into explicit subfolder hierarchy
result = librarian.file_organizer.organize_into_subfolder(
    document_id=123,
    folder_hierarchy=["ai", "research", "neural-networks", "2025"],
    base_path="documents"
)
# Creates: documents/ai/research/neural-networks/2025/document.pdf
```

**API:**
```bash
POST /librarian/organize/{document_id}
{
  "folder_hierarchy": ["ai", "research", "neural-networks", "2025"]
}
```

---

### 4. **Automatic Folder Creation** ✅

The librarian **automatically creates all necessary subfolders**:

```python
# When organizing, all subfolders are created automatically
result = librarian.file_organizer.organize_document(
    document_id=123,
    auto_create_folders=True  # Default: True
)
# If path is: documents/ai/research/papers/2025/
# All folders are created: documents → ai → research → papers → 2025
```

**What Gets Created:**
- All parent folders in the path
- Nested subfolder structure
- Target folder itself
- Uses `mkdir(parents=True, exist_ok=True)` - creates entire hierarchy

---

## 📋 Complete Examples

### Example 1: Organize by Tags (3-Level Nested)
```bash
POST /librarian/organize/123
{
  "tag_names": ["ai", "research", "papers"]
}
```
**Result:**
```
documents/
└── ai/
    └── research/
        └── papers/
            └── document.pdf
```

### Example 2: Explicit Hierarchy (4-Level Nested)
```bash
POST /librarian/organize/123
{
  "folder_hierarchy": ["projects", "ai", "research", "2025"]
}
```
**Result:**
```
documents/
└── projects/
    └── ai/
        └── research/
            └── 2025/
                └── document.pdf
```

### Example 3: Auto-Organization (Pattern-Based)
```python
librarian = LibrarianEngine(
    organization_pattern="category/type/date"
)
result = librarian.process_document(document_id=123)
```
**Result:**
```
documents/
└── ai/
    └── pdf/
        └── 2025-01/
            └── document.pdf
```

### Example 4: Date-Based Deep Nesting
```bash
POST /librarian/organize/123
{
  "folder_hierarchy": ["2025", "01", "research", "ai", "papers"]
}
```
**Result:**
```
documents/
└── 2025/
    └── 01/
        └── research/
            └── ai/
                └── papers/
                    └── document.pdf
```

---

## 🎯 Organization Patterns Supported

| Pattern | Depth | Example Path |
|---------|-------|--------------|
| `category/type` | 2 levels | `documents/ai/pdf/` |
| `category/type/date` | 3 levels | `documents/ai/pdf/2025-01/` |
| `date/category/type` | 3+ levels | `documents/2025/01/ai/pdf/` |
| `tags/hierarchy` | Up to 5 levels | `documents/ai/research/papers/` |
| `category/tags` | 3 levels | `documents/ai/neural-networks/` |
| **Custom hierarchy** | **Unlimited** | **Any depth you specify** |

---

## 🔧 Configuration

### Setting Organization Pattern

```python
librarian = LibrarianEngine(
    organization_pattern="category/type/date",  # 3-level nesting
    auto_organize=True
)
```

### Available Patterns:
- `category/type` - 2 levels
- `type/category` - 2 levels
- `date/category` - 3 levels (date splits into year/month)
- `category/date` - 3 levels
- `category/type/date` - 3 levels
- `date/category/type` - 4+ levels
- `tags/hierarchy` - Up to 5 levels (from tags)
- `category/tags` - 3 levels (category + tags)

---

## ✅ Features

### 1. **Automatic Subfolder Creation** ✅
- Creates all necessary parent folders
- Handles any depth of nesting
- Safe folder creation (no overwrites)

### 2. **Multiple Organization Methods** ✅
- Pattern-based (automatic)
- Tag-based (dynamic)
- Explicit hierarchy (manual)
- Hybrid (combination)

### 3. **File Movement** ✅
- Moves files to organized locations
- Updates database paths
- Safe file operations

### 4. **Index File Creation** ✅
- Creates INDEX.md in folders
- Lists all documents in subfolder
- Includes metadata and tags

---

## 📊 Real-World Examples

### Academic Papers Organization
```bash
# Organize research papers by topic, type, and date
POST /librarian/organize/123
{
  "folder_hierarchy": ["research", "ai", "papers", "2025", "january"]
}
```
**Structure:**
```
documents/
└── research/
    └── ai/
        └── papers/
            └── 2025/
                └── january/
                    ├── paper1.pdf
                    ├── paper2.pdf
                    └── INDEX.md
```

### Project Documentation
```bash
# Organize by project, category, and version
POST /librarian/organize/456
{
  "tag_names": ["project-alpha", "documentation", "v2.0"]
}
```
**Structure:**
```
documents/
└── project-alpha/
    └── documentation/
        └── v2.0/
            └── README.md
```

### Multi-Level Date Organization
```bash
# Year → Month → Category → Type
POST /librarian/organize/789
{
  "folder_hierarchy": ["2025", "01", "meetings", "notes"]
}
```
**Structure:**
```
documents/
└── 2025/
    └── 01/
        └── meetings/
            └── notes/
                └── meeting_notes.md
```

---

## 🎯 Summary

**Yes, the librarian can organize into subfolders and files!**

✅ **Supported:**
- Nested subfolders (any depth)
- Multiple organization patterns
- Tag-based hierarchy
- Explicit folder structures
- Automatic folder creation
- File movement to subfolders
- Index file generation

✅ **How to Use:**
1. **Auto-organization**: Set `organization_pattern` in LibrarianEngine
2. **Tag-based**: Use `tag_names` in organize request
3. **Explicit**: Use `folder_hierarchy` in organize request
4. **Hybrid**: Combine methods as needed

**All subfolders are created automatically, and files are organized into the nested structure!** 🎉
