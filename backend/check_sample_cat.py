import sqlite3

db_path = "data/grace.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get the latest sample.cat scraping job
cursor.execute("""
    SELECT id, url, status 
    FROM scraping_jobs 
    WHERE url LIKE '%sample.cat%'
    ORDER BY id DESC 
    LIMIT 1
""")

job = cursor.fetchone()
if job:
    job_id, url, status = job
    print(f"Latest sample.cat job: ID={job_id}, Status={status}")
    print(f"URL: {url}\n")
    
    # Get all URLs found during scraping
    cursor.execute("""
        SELECT url, status, title
        FROM scraped_pages 
        WHERE job_id = ?
        ORDER BY id
        LIMIT 25
    """, (job_id,))
    
    pages = cursor.fetchall()
    print(f"Found {len(pages)} pages:\n")
    for page_url, page_status, title in pages:
        print(f"[{page_status}] {page_url[:80]}")
        if title:
            print(f"  Title: {title[:60]}")
        print()
else:
    print("No sample.cat jobs found")

conn.close()
