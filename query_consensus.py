import asyncio
from backend.cognitive.consensus_engine import get_consensus_engine

async def ask_consensus():
    try:
        engine = get_consensus_engine()
        prompt = '''
        Please review the activities performed on the Grace infrastructure tonight.
        We have completed Phase 18 of the Blueprint: Core Cognitive Infrastructure Integration.
        Specifically, we have written and passed integration tests for over 15 backend/cognitive/ components including:
        - The event_bus (ZMQ and IPC)
        - The idle_learner and auto_research modules (Kimi orchestration)
        - The autonomous_librarian (FlashCache and OS directory taxonomy)
        - The grace_compiler, hunter_assimilator, and braille_compiler (AST and Z3 Physics verification)
        - The prophylactic memory systems (episodic, ghost, learning, chained)
        - The proactive_healing_engine, autonomous_diagnostics, and immune_system loops.
        
        As the consensus mechanism, can you verify if these components are truly wired together according to the Grace Blueprint? What is your view on the stability and autonomy of the system now that these tests pass? Provide a concise but definitive response.
        '''
        print('Querying Consensus Engine...')
        result = await engine.evaluate_proposal(prompt, context='Phase 18 Integration Testing Verification')
        print('\n--- CONSENSUS RESPONSE ---')
        print(result.get('final_decision', 'No decision reached.'))
        print('\n--- REASONING ---')
        print(result.get('reasoning', 'No reasoning provided.'))
        if 'layer_results' in result:
            print('\n--- LAYER METRICS ---')
            for layer, data in result['layer_results'].items():
                if isinstance(data, dict):
                    print(f"{layer}: Confidence {data.get('confidence', 'N/A')}")
    except Exception as e:
        print(f'Error: {e}')

if __name__ == '__main__':
    asyncio.run(ask_consensus())
