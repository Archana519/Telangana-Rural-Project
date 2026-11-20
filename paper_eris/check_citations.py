"""Every \\cite key must exist in references.bib; every bib entry must be cited; every entry must have a DOI or URL."""
import re, sys
from pathlib import Path
H = Path(__file__).resolve().parent
tex = (H / "main.tex").read_text(); bib = (H / "references.bib").read_text()
cited = {k.strip() for m in re.findall(r"\\cite\{([^}]*)\}", tex) for k in m.split(",")}
ents = {}
for m in re.finditer(r"@(\w+)\{([^,]+),(.*?)\n\}", bib, re.S): ents[m.group(2)] = m.group(3)
bad = 0
for k in sorted(cited - set(ents)): print("CITED BUT NOT IN BIB", k); bad += 1
for k in sorted(set(ents) - cited): print("IN BIB BUT NOT CITED", k); bad += 1
for k, b in ents.items():
    if not re.search(r"\bdoi\s*=|\burl\s*=|\bpublisher\s*=", b): print("NO DOI/URL", k); bad += 1
print(len(cited), "cited,", len(ents), "bib entries,", bad, "problems"); sys.exit(1 if bad else 0)
