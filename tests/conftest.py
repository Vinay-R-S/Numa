"""Make the server package importable from the test suite.

Until NUMA-142 no test imported `src/` or `main.py` at all: every module under
`tests/` defined local copies of the logic it then asserted on, so a green run
said nothing about the application. This puts `server/` on the path so tests can
exercise the real code (PLAN 12.6).
"""
import os
import sys

SERVER_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server")

if SERVER_ROOT not in sys.path:
    sys.path.insert(0, SERVER_ROOT)

# The modules under test read these at import or call time. Set before any test
# imports them, and never to a real credential.
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-not-a-real-key")
os.environ.setdefault("TIMEZONE", "Asia/Kolkata")
