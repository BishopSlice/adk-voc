import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import os

# Inside a pre-commit hook, git exports GIT_INDEX_FILE and friends. Tests that run git in temp repos
# would write into the real commit's index, so clear them for the whole test session.
for k in [k for k in os.environ if k.startswith("GIT_")]:
    del os.environ[k]
