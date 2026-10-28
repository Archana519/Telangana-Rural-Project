from PIL import Image
import numpy as np

p = r"D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\study_area\tgrac_layer3_actual.jpg"

im = Image.open(p).convert("RGB")
arr = np.array(im)

gray = np.mean(arr, axis=2)

print("=== TGRAC IMAGE DIAGNOSTIC ===")
print("File:", p)
print("Size:", im.size)
print("Mode:", im.mode)

print("\nPixel statistics:")
print("Minimum:", arr.min(axis=(0, 1)))
print("Maximum:", arr.max(axis=(0, 1)))
print("Mean RGB:", tuple(round(x, 2) for x in arr.mean(axis=(0, 1))))
print("Std RGB:", tuple(round(x, 2) for x in arr.std(axis=(0, 1))))

print("\nBrightness:")
print("Mean:", round(gray.mean(), 2))
print("Std:", round(gray.std(), 2))

print("\nUnique colors:")
print("Approx. unique RGB colors:", len(np.unique(arr.reshape(-1, 3), axis=0)))

print("\n=== RESULT ===")
if gray.std() > 20 and len(np.unique(arr.reshape(-1, 3), axis=0)) > 1000:
    print("IMAGE HAS SUBSTANTIAL VISUAL DETAIL/VARIATION")
else:
    print("IMAGE MAY BE LOW-DETAIL OR MOSTLY UNIFORM")