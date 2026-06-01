import sys
import os
print("=== Debug Info ===")
print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")
print()

try:
    print("Testing PyTorch import...")
    import torch
    print(f"✓ PyTorch imported successfully! Version: {torch.__version__}")
    print(f"  Torch path: {torch.__file__}")
except Exception as e:
    print(f"✗ PyTorch import failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print()
try:
    print("Testing train module import...")
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'digit_recognition'))
    from train import Trainer
    print("✓ train module imported successfully!")
except Exception as e:
    print(f"✗ train module import failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print()
try:
    print("Testing gui module import...")
    from digit_recognition.gui import MainWindow
    print("✓ gui module imported successfully!")
except Exception as e:
    print(f"✗ gui module import failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
