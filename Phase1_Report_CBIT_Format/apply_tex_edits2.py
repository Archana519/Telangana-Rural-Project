import sys
p = sys.argv[1]
L = open(p, encoding="utf-8").read().split("\n")
n0 = len(L)
def rep(n, a, b):
    assert a in L[n - 1], (n, a)
    L[n - 1] = L[n - 1].replace(a, b)
rep(339, "(presumed ESA WorldCover; to be confirmed)", "(ESA WorldCover 2021 v200 according to the project notes; the version is not stored in the raster)")
rep(219, "Presumed ESA WorldCover (\\url{https://esa-worldcover.org}); inferred from the file name, not documented",
    "ESA WorldCover (\\url{https://esa-worldcover.org}); the project notes record 2021 v200, not stored in the raster")
rep(219, "Source/version to be confirmed;", "Version not stored in the raster;")
assert len(L) == n0
open(p, "w", encoding="utf-8").write("\n".join(L))
print("ok")
