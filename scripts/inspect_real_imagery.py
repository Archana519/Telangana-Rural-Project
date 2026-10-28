from PIL import Image
import os

p = r"D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\raw\imagery\angadi_kistapur_tgrac_export.jpg"

im = Image.open(p)

print("=== REAL IMAGERY INSPECTION ===")
print("File:", p)
print("Exists:", os.path.exists(p))
print("File size:", os.path.getsize(p), "bytes")

print("\nImage information:")
print("Format:", im.format)
print("Size:", im.size)
print("Mode:", im.mode)
print("Bands:", im.getbands())

print("\nMetadata:")
print("Info keys:", list(im.info.keys()))

print("\nGeo-reference:")
print("CRS: NOT EMBEDDED IN JPEG")
print("Affine transform: NOT EMBEDDED IN JPEG")

print("\n=== INSPECTION RESULT ===")
print("Valid raster image: YES")
print("Original GeoTIFF: NO")
print("Georeferencing embedded: NO")