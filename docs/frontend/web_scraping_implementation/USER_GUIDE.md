# Web Scraper - User Guide

## 🌐 Overview

The Web Scraper feature allows you to automatically extract content from websites and store it in your knowledge base. You can control how deep the scraper goes by following links on each page.

---

## 🚀 Getting Started

### Accessing the Web Scraper

1. Open Grace in your browser (http://localhost:5174)
2. Navigate to the **Documents** tab
3. Click on the **Web Scraper** tab (🌐 icon)

---

## 📝 How to Use

### Step 1: Enter a URL

Enter the website URL you want to scrape in the "URL to Scrape" field.

**Examples:**
- `https://example.com`
- `https://docs.python.org/3/tutorial/`
- `https://reactjs.org/docs/getting-started.html`

> [!IMPORTANT]
> Make sure to include `http://` or `https://` in the URL

### Step 2: Set Crawl Depth

Use the slider to set how deep you want the scraper to go:

| Depth | What It Does |
|-------|--------------|
| **0** | Only scrapes the single page you entered |
| **1** | Scrapes the page + all pages it links to |
| **2** | Scrapes 2 levels deep (page → links → their links) |
| **3-5** | Scrapes even deeper (use with caution!) |

**Recommendation:** Start with depth 1-2 for most websites

### Step 3: Configure Advanced Options (Optional)

Click "Advanced Options" to customize:

- **Stay on same domain**: Only scrape pages from the same website (recommended)
- **Max pages**: Limit how many pages to scrape (default: 100)
- **Save to folder**: Choose where to save the scraped content

### Step 4: Start Scraping

Click the **"🚀 Start Scraping"** button and watch the progress!

---

## 📊 Understanding the Progress

While scraping, you'll see:

- **Progress bar**: Visual indicator of completion
- **Pages scraped**: How many pages have been successfully scraped
- **Failed**: Pages that couldn't be scraped
- **Status**: Current activity (running, pending, completed)

You can **cancel** the scraping job at any time by clicking the "Cancel" button.

---

## ✅ Viewing Results

When scraping is complete, you'll see:

### Summary Cards
- Total pages successfully scraped
- Number of failed pages
- Total content size

### Page List
Each scraped page shows:
- ✓ Success indicator (green) or ✗ failure (red)
- Page title
- URL
- Depth level
- Content size

---

## 🎯 Best Practices

### DO:
- ✅ Start with small depths (0-1) to test
- ✅ Use "Stay on same domain" for focused scraping
- ✅ Set a reasonable max pages limit
- ✅ Scrape documentation sites and blogs
- ✅ Be patient - large sites take time

### DON'T:
- ❌ Scrape sites that require login
- ❌ Use very high depths (4-5) without limits
- ❌ Scrape sites with terms against automated access
- ❌ Expect JavaScript-heavy SPAs to work perfectly
- ❌ Try to scrape Google Drive or cloud storage links

---

## ⚠️ Limitations & Edge Cases

### What Doesn't Work

| Type | Why | Alternative |
|------|-----|-------------|
| **Google Drive links** | Not a website | Download files and upload directly |
| **Dropbox/OneDrive** | Cloud storage | Download files and upload directly |
| **Sites requiring login** | No authentication | Export content manually |
| **JavaScript SPAs** | No JS execution | May get partial content |
| **PDFs, images** | Binary files | Upload files directly instead |

### Error Messages

**"Cloud storage links are not supported"**
- You tried to scrape a Google Drive, Dropbox, or similar link
- **Solution**: Download the files and upload them to Grace directly

**"URL must use http or https"**
- Invalid URL format
- **Solution**: Make sure URL starts with `http://` or `https://`

**"Failed to fetch content"**
- Website is down or blocking scrapers
- **Solution**: Try again later or check if site allows automated access

**"Content too large"**
- Page exceeds 1 MB limit
- **Solution**: This is automatic - the page will be skipped

---

## 💡 Use Cases

### Documentation Sites
**Perfect for:**
- Python docs
- React documentation
- API references

**Example:**
```
URL: https://docs.python.org/3/tutorial/
Depth: 2
Max Pages: 50
```

### Blog Posts
**Perfect for:**
- Technical blogs
- Tutorial series
- Knowledge bases

**Example:**
```
URL: https://blog.example.com
Depth: 1
Max Pages: 20
Stay on same domain: ✓
```

### Company Websites
**Perfect for:**
- About pages
- Product information
- Public documentation

**Example:**
```
URL: https://company.com/docs
Depth: 2
Max Pages: 100
Stay on same domain: ✓
```

---

## 🔍 After Scraping

### What Happens to Scraped Content?

1. **Stored in Database**: All content is saved to the Grace database
2. **Organized by Folder**: Saved in the folder you specified (or auto-generated)
3. **Ready for Search**: Content is available for semantic search (if AI models enabled)
4. **Ready for Chat**: Can be used in RAG-powered conversations (if AI models enabled)

### Finding Your Scraped Content

1. Go to the **Files** tab
2. Navigate to the folder where content was saved
3. You'll see text files for each scraped page

---

## 🛠️ Troubleshooting

### Scraping is Slow
- **Normal**: Large sites with many pages take time
- **Tip**: Reduce max pages or depth

### Many Pages Failed
- **Possible Causes**: Site blocking, broken links, binary files
- **Solution**: Check the failed URLs in results

### No Content Extracted
- **Possible Causes**: JavaScript-heavy site, paywall, login required
- **Solution**: Try a different site or export content manually

### Scraper Stuck
- **Solution**: Click "Cancel" and try again with lower depth/max pages

---

## 📞 Tips & Tricks

### Efficient Scraping
1. **Test first**: Use depth 0 to test a single page
2. **Incremental**: Start with depth 1, then increase if needed
3. **Monitor**: Watch the progress to see if it's working as expected
4. **Limits**: Set reasonable max pages to avoid overwhelming the system

### Best Results
- Choose well-structured websites (documentation, blogs)
- Avoid sites with heavy JavaScript
- Use "Stay on same domain" to avoid wandering off-topic
- Set max pages to prevent runaway scraping

---

## ❓ FAQ

**Q: Can I scrape multiple URLs at once?**  
A: Not currently - scrape one URL at a time

**Q: How long does scraping take?**  
A: Depends on depth and number of pages. Typically 1-5 minutes for small sites

**Q: Can I scrape password-protected sites?**  
A: No - authentication is not supported

**Q: What happens if I close the browser while scraping?**  
A: The scraping job continues on the server. Refresh to see progress

**Q: Can I edit the scraped content?**  
A: Yes - navigate to the Files tab and edit the text files

**Q: Will this work with any website?**  
A: Most static websites work well. JavaScript-heavy SPAs may have issues

---

## 🎉 You're Ready!

Start scraping websites to build your knowledge base. Remember to:
- Start small (depth 0-1)
- Set reasonable limits
- Monitor progress
- Check results

Happy scraping! 🚀
