import os
import sys
import torch

PROJECT_ROOT = r"D:\Telangana_Rural_Project"

MODEL_PROJECT = r"D:\new_MPS\remoteSensingWebApp"

MODEL_FILE = os.path.join(
    MODEL_PROJECT,
    "project",
    "model.py"
)

CHECKPOINT_FILE = os.path.join(
    MODEL_PROJECT,
    "checkpoints",
    "best_model.pth"
)

print("=" * 80)
print("PHASE 25 - STEP 11J")
print("VERIFY STRONGDINOV2SEG MODEL")
print("=" * 80)

print("\nMODEL PROJECT")
print("-" * 80)
print("Project:", MODEL_PROJECT)
print("Model file:", MODEL_FILE)
print("Checkpoint:", CHECKPOINT_FILE)

if not os.path.isfile(MODEL_FILE):
    print("\n[ERROR] model.py not found.")
    raise SystemExit(1)

if not os.path.isfile(CHECKPOINT_FILE):
    print("\n[ERROR] best_model.pth not found.")
    raise SystemExit(1)

print("\nFILES")
print("-" * 80)
print("model.py exists:", os.path.isfile(MODEL_FILE))
print("checkpoint exists:", os.path.isfile(CHECKPOINT_FILE))
print(
    "checkpoint size:",
    round(os.path.getsize(CHECKPOINT_FILE) / (1024 * 1024), 2),
    "MB"
)

print("\nPYTORCH")
print("-" * 80)
print("PyTorch version:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())

print("\nCHECKPOINT INSPECTION")
print("-" * 80)

checkpoint = torch.load(
    CHECKPOINT_FILE,
    map_location="cpu",
    weights_only=False
)

print("Checkpoint type:", type(checkpoint).__name__)

if isinstance(checkpoint, dict):

    print("Checkpoint keys:")
    for key in checkpoint.keys():
        print(" ", key)

    if "epoch" in checkpoint:
        print("Epoch:", checkpoint["epoch"])

    if "mIoU" in checkpoint:
        print("mIoU:", checkpoint["mIoU"])

    if "mDice" in checkpoint:
        print("mDice:", checkpoint["mDice"])

    if "state_dict" in checkpoint:
        state_dict = checkpoint["state_dict"]
    elif "model_state_dict" in checkpoint:
        state_dict = checkpoint["model_state_dict"]
    else:
        # Some checkpoints directly contain the state dictionary
        state_dict = checkpoint

    if isinstance(state_dict, dict):
        print("\nState dictionary parameters:", len(state_dict))

        print("\nFirst 10 parameter names:")
        for name in list(state_dict.keys())[:10]:
            print(" ", name)

else:
    print("\n[WARNING] Checkpoint is not a dictionary.")
    state_dict = None

print("\nMODEL FILE CHECK")
print("-" * 80)

with open(MODEL_FILE, "r", encoding="utf-8") as f:
    model_text = f.read()

checks = {
    "DINOv2 reference": "dinov2" in model_text.lower(),
    "NUM_CLASSES = 8": "NUM_CLASSES = 8" in model_text,
    "FPN reference": "FPN" in model_text,
    "ASPP reference": "ASPP" in model_text,
    "Residual decoder reference": "Residual" in model_text,
}

for name, result in checks.items():
    print(f"{name}: {'YES' if result else 'NO'}")

print("\n" + "=" * 80)

if (
    os.path.isfile(MODEL_FILE)
    and os.path.isfile(CHECKPOINT_FILE)
    and state_dict is not None
):
    print("STATUS: MODEL AND CHECKPOINT FOUND.")
    print("NEXT: VERIFY INFERENCE SCRIPT CONFIGURATION.")
else:
    print("STATUS: MODEL VERIFICATION REQUIRES INSPECTION.")

print("=" * 80)

print("\nPHASE 25 STEP 11J COMPLETED.")