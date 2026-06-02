import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

print("Python executable:", sys.executable)
print("Working dir:", os.getcwd())

try:
    print("\nTrying to import torch...")
    import torch
    print("OK Torch imported successfully!")
    print("  Version:", torch.__version__)
    print("  Torch path:", torch.__file__)
except Exception as e:
    print("ERROR Torch import failed:", type(e).__name__, ":", str(e))
    import traceback
    traceback.print_exc()
