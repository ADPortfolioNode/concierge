import asyncio
import sys
import os
# ensure workspace root is on sys.path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from orchestration.sacred_timeline import SacredTimeline
from core.concurrency import AsyncConcurrencyManager
from memory.memory_store import MemoryStore

async def test():
    st = SacredTimeline(AsyncConcurrencyManager(max_agents=1), MemoryStore())
    # greetings should be handled directly
    res = await st.handle_user_input('hi')
    print('response to hi:', res)
    assert isinstance(res, dict) and res.get('status') == 'success'
    assert 'response' in res and 'Hello' in res['response']
    # should also hint at features like images or goals
    assert any(k in res['response'].lower() for k in ('image', 'audio', 'goal', 'file'))

    # non‑goal small talk should also yield a friendly chat-style reply
    res2 = await st.handle_user_input('how are you?')
    print('response to small talk:', res2)
    assert isinstance(res2, dict) and res2.get('status') == 'success'
    assert 'response' in res2 and isinstance(res2['response'], str)
    # asking about capabilities triggers hint text via hint logic
    res_hint = await st.handle_user_input('what can you do?')
    print('capabilities hint:', res_hint)
    assert 'response' in res_hint and 'image' in res_hint['response'].lower()

    # a longer, goal‑like sentence should not be treated as casual chat;
    # result will typically include a task_map or other metadata instead.
    res3 = await st.handle_user_input('please build a simple todo app for me')
    print('response to longer input:', res3)
    assert isinstance(res3, dict)
    # chat-only replies always include a top-level 'response' key
    assert 'response' not in res3

if __name__ == '__main__':
    asyncio.run(test())
