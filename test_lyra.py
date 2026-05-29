import sys

sys.path.insert(0, 'packages/lyra-cli/src')

# Check if English instruction is there
import inspect

from lyra_cli.interactive.session import Session

source = inspect.getsource(Session._build_system_prompt)
if "ALWAYS respond in English" in source:
    print("✅ English fix is in the code")
else:
    print("❌ English fix NOT in the code")
