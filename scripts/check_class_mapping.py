
import ast
import os
import re
import argparse

ROOT = r"D:\Telangana_Rural_Project"
SRC_ROOT = r"D:\new_MPS\remoteSensingWebApp"
PRED = os.path.join(
    ROOT, "Siddipet", "Damarakunta",
    "predictions", "tiled_v1", "pred_classes_full.tif"
)

SKIP = {
    ".git", ".venv", "venv", "env", "__pycache__",
    "site-packages", "node_modules", "checkpoints"
}

PATTERNS = re.compile(
    r"class_names|num_classes|ignore_index|"
    r"dataset|__getitem__|mask|label|"
    r"crossentropyloss|argmax|softmax|"
    r"read.*(png|mask)|imread|remap|label_map|"
    r"pred_classes|building_prob",
    re.IGNORECASE,
)


def py_files(root):
    for current, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP]
        for filename in files:
            if filename.endswith(".py"):
                yield os.path.join(current, filename)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--limit", type=int, default=250,
        help="Maximum relevant source lines to print"
    )
    args = parser.parse_args()

    if not os.path.isdir(SRC_ROOT):
        print("ERROR: Source folder not found:", SRC_ROOT)
        return

    files = list(py_files(SRC_ROOT))
    print(f"Scanned {len(files)} Python files.")
    print("\n=== CLASS DEFINITIONS ===")

    for path in files:
        try:
            source = open(path, encoding="utf-8", errors="replace").read()
            tree = ast.parse(source)
        except (OSError, SyntaxError):
            continue

        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue

            targets = (
                node.targets if isinstance(node, ast.Assign)
                else [node.target]
            )

            for target in targets:
                if not isinstance(target, ast.Name):
                    continue
                if target.id not in {
                    "CLASS_NAMES", "NUM_CLASSES", "IGNORE_INDEX",
                    "CLASS_MAP", "LABEL_MAP", "CLASSES"
                }:
                    continue
                try:
                    value = ast.literal_eval(node.value)
                except Exception:
                    value = "<dynamic expression; inspect source manually>"

                print(
                    f"{path}:{node.lineno}: "
                    f"{target.id} = {value}"
                )

    print("\n=== RELEVANT SOURCE LINES ===")
    print("Review surrounding lines for the complete data flow.")

    count = 0
    for path in files:
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except OSError:
            continue

        for number, line in enumerate(lines, 1):
            if PATTERNS.search(line) and not line.lstrip().startswith("#"):
                print(f"{path}:{number}: {line.rstrip()[:220]}")
                count += 1
                if count >= args.limit:
                    print("Output limit reached; narrow the search if needed.")
                    break
        if count >= args.limit:
            break

    print("\n=== INFERENCE MAPPING ===")
    infer_path = os.path.join(ROOT, "scripts", "run_tiled_inference.py")

    if os.path.isfile(infer_path):
        with open(infer_path, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        for number, line in enumerate(lines, 1):
            if re.search(
                r"argmax|softmax|building_prob|pred_classes",
                line, re.IGNORECASE
            ):
                print(f"{infer_path}:{number}: {line.rstrip()}")

        print(
            "\nInterpretation: argmax over logits[:, 1:] followed by +1 "
            "maps output channel 1 to saved ID 1, channel 2 to ID 2, etc."
        )
        print(
            "If building_prob uses softmax(logits)[:, 2], it refers to "
            "output channel 2. That is Building only if training targets "
            "used ID 2 for Building."
        )
    else:
        print("Inference script not found:", infer_path)

    print("\n=== PREDICTION FILE ===")
    if os.path.isfile(PRED):
        print("Found:", PRED)
        try:
            import rasterio
            import numpy as np

            with rasterio.open(PRED) as ds:
                print("Shape:", ds.width, "x", ds.height)
                print("CRS:", ds.crs)
                print("Raster nodata:", ds.nodata)
                values, counts = np.unique(ds.read(1), return_counts=True)
                print("Pixel counts by saved ID:")
                total = counts.sum()
                for value, count in zip(values, counts):
                    print(
                        f"  ID {int(value)}: {int(count):,} "
                        f"({100 * count / total:.3f}%)"
                    )
        except Exception as exc:
            print("Could not inspect raster:", exc)
    else:
        print("Prediction raster not found at:", PRED)

    print("\n=== VERDICT ===")
    print(
        "This scan is diagnostic, not proof of the training label mapping. "
        "Confirm the mask dataset's documented IDs and inspect the dataset "
        "loader's target conversion before treating any predicted ID as Building."
    )


if __name__ == "__main__":
    main()
