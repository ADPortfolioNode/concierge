"""Run the system smoke test and print status.

This script runs the pytest system smoke test added under `tests/` and
returns an exit code 0 on success. It's a lightweight wrapper so CI or
the Concierge agent can call it directly.
"""
import sys
import pytest


def main():
    rc = pytest.main(["-q", "tests/test_system_smoke.py"]) 
    sys.exit(rc)


if __name__ == '__main__':
    main()
