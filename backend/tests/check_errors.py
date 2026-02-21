import sqlite3

db_path = "data/grace.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get a failed page to check if error_message exists
cursor.execute("""
    SELECT url, status, error_message, title
    FROM scraped_pages 
    WHERE status = 'failed'
    ORDER BY id DESC 
    LIMIT 3
""")

pages = cursor.fetchall()
print("Failed pages in database:")
for url, status, error, title in pages:
    print(f"\nURL: {url[:60]}...")
    print(f"Status: {status}")
    print(f"Error: {error}")
    print(f"Title: {title}")

conn.close()
