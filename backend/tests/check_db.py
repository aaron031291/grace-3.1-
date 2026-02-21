import sqlite3
import sys

try:
    conn = sqlite3.connect('data/grace.db')
    cursor = conn.cursor()
    
    # Count chats
    cursor.execute('SELECT COUNT(*) FROM chats')
    total_chats = cursor.fetchone()[0]
    print(f'Total chats in database: {total_chats}')
    
    # Get recent chats
    cursor.execute('SELECT id, title, created_at FROM chats ORDER BY created_at DESC LIMIT 5')
    print('\nRecent chats:')
    for row in cursor.fetchall():
        print(f'  ID={row[0]}, Title={row[1][:50] if row[1] else "Untitled"}, Created={row[2]}')
    
    # Count messages
    cursor.execute('SELECT COUNT(*) FROM chat_history')
    total_messages = cursor.fetchone()[0]
    print(f'\nTotal messages in database: {total_messages}')
    
    conn.close()
    print('\n✅ Database is accessible and contains data')
    
except Exception as e:
    print(f'❌ Error accessing database: {e}')
    sys.exit(1)
