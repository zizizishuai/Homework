import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

print("=== Debug Info ===")
print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")
print()

try:
    print("Testing PyTorch import...")
    import torch
    print(f"OK PyTorch imported successfully! Version: {torch.__version__}")
    print(f"  Torch path: {torch.__file__}")
except Exception as e:
    print(f"ERROR PyTorch import failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print()
try:
    print("Testing train module import...")
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'digit_recognition'))
    from train import Trainer
    print("OK train module imported successfully!")
except Exception as e:
    print(f"ERROR train module import failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print()
try:
    print("Testing gui module import...")
    from digit_recognition.gui import MainWindow
    print("OK gui module imported successfully!")
except Exception as e:
    print(f"ERROR gui module import failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
