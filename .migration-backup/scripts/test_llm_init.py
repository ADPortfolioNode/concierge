import sys
from pathlib import Path

# Ensure repo root is on sys.path for local imports
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.llm_tool import LLMTool


def main():
    t = LLMTool()
    print('model=', t.model)
    print('snapshot=', t._env_snapshot)


if __name__ == '__main__':
    main()
