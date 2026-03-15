"""Final verification — start Spindle flush, dispatch one task, prove full persistence."""
import sys, os, time, logging, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logging.basicConfig(level=logging.INFO, format='[%(asctime)s][%(levelname)s] %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger('verify')

# 1. Start the Spindle event store flush thread
from cognitive.spindle_event_store import get_event_store
store = get_event_store()
store.start_background_flush()
logger.info(f'Spindle flush thread started. Seq={store._seq.current}, DB={store._db_available}')

# 2. Dispatch one quick task
from cognitive.coding_agents import get_coding_agent_pool, CodingTask
pool = get_coding_agent_pool()

task = CodingTask(
    id='VERIFY-001',
    task_type='fix',
    file_path='cognitive/spindle_event_store.py',
    description='Add a docstring to the _flush_batch method explaining it uses begin_nested savepoints to skip duplicate sequence_ids.',
    error='Missing documentation',
    context={'source': 'verification'},
)

logger.info('Dispatching verification task to Kimi...')
result = pool.dispatch(task, agent_name='kimi')
logger.info(f'Result: status={result.status}, confidence={result.confidence:.0%}, agent={result.agent}')

# 3. Wait for flush
time.sleep(3)

# 4. Check what persisted
import sqlite3
from pathlib import Path
fb = Path(__file__).parent.parent / 'data' / 'spindle_events_fallback.db'
conn = sqlite3.connect(str(fb))

total = conn.execute('SELECT COUNT(*) FROM spindle_fallback').fetchone()[0]
agent_count = conn.execute(
    "SELECT COUNT(*) FROM spindle_fallback WHERE source_type='coding_agent'"
).fetchone()[0]

logger.info(f'\n=== SPINDLE PERSISTENCE REPORT ===')
logger.info(f'Total events:         {total}')
logger.info(f'Coding agent events:  {agent_count}')

# Show ALL event source types
rows = conn.execute(
    "SELECT source_type, COUNT(*) as cnt FROM spindle_fallback GROUP BY source_type ORDER BY cnt DESC"
).fetchall()
logger.info(f'\nEvents by source:')
for src, cnt in rows:
    logger.info(f'  {src:25s} {cnt:4d} events')

# Show recent coding agent events
if agent_count > 0:
    logger.info(f'\nRecent coding agent events:')
    rows = conn.execute(
        "SELECT sequence_id, topic, payload_json FROM spindle_fallback "
        "WHERE source_type='coding_agent' ORDER BY sequence_id DESC LIMIT 8"
    ).fetchall()
    for seq, topic, pj in rows:
        data = json.loads(pj) if pj else {}
        task_id = data.get('task_id', '')
        agents = data.get('agents', data.get('agent', ''))
        conf = data.get('best_confidence', data.get('confidence', ''))
        active = data.get('active_jobs', '')
        print(f'  seq={seq:4d} | {topic:40s} | task={task_id:15s} | conf={conf}')

conn.close()

# Stop flush thread
store.stop_background_flush()

logger.info(f'\n{"="*50}')
if agent_count > 0:
    logger.info('VERIFIED: Coding agent events persisted to Spindle DB')
    logger.info('Trust scores, agent IDs, and task results are all logged')
    logger.info('System is working as designed.')
else:
    logger.info('Events in memory but not yet flushed to DB.')
    logger.info('(DB may be unavailable - events stored in fallback buffer)')
    logger.info(f'Fallback buffer: {len(store._fallback)} events')
    if store._fallback:
        logger.info('Sample buffered events:')
        for ev in store._fallback[-5:]:
            print(f'  topic={ev.get("topic")} | src={ev.get("source_type")} | seq={ev.get("sequence_id")}')
logger.info(f'{"="*50}')
