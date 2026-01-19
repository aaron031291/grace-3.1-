import sqlite3
import sys

db_path = "data/grace.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get the latest scraping job
cursor.execute("SELECT id, url, status FROM scraping_jobs ORDER BY id DESC LIMIT 1")
job = cursor.fetchone()
print(f"Latest job: ID={job[0]}, URL={job[1]}, Status={job[2]}")
print()

# Get scraped pages for this job
cursor.execute("""
    SELECT url, status, error_message 
    FROM scraped_pages 
    WHERE job_id = ? 
    ORDER BY id DESC 
    LIMIT 5
""", (job[0],))

pages = cursor.fetchall()
print(f"Pages for job {job[0]}:")
for url, status, error in pages:
    print(f"\nURL: {url}")
    print(f"Status: {status}")
    print(f"Error: {error}")

conn.close()
