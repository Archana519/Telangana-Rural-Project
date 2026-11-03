
from pathlib import Path
import hashlib

folder = Path(
    r"D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\ALL_OUTPUT_IMAGES"
)

seen = {}
duplicates = []

for file in sorted(folder.iterdir()):
    if not file.is_file():
        continue

    digest = hashlib.sha256(file.read_bytes()).hexdigest()

    if digest in seen:
        duplicates.append((file, seen[digest]))
    else:
        seen[digest] = file

print("\nIDENTICAL DUPLICATES FOUND:")
for duplicate, original in duplicates:
    print(f"{duplicate.name}  -> duplicate of {original.name}")

print(f"\nTotal duplicate files: {len(duplicates)}")

if duplicates:
    answer = input("Type YES to delete duplicate copies only: ")
    if answer.strip() == "YES":
        for duplicate, original in duplicates:
            duplicate.unlink()
        print(f"Deleted {len(duplicates)} duplicate files.")
    else:
        print("No files deleted.")
else:
    print("No identical duplicates found.")
