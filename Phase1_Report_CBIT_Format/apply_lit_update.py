"""Rebuild references.bib, lit_table1/2 and the verification CSV/JSON from Crossref-verified records.

Run once from this folder:  python apply_lit_update.py <scratch_lit_dir>
<scratch_lit_dir> holds verified_old.json and verified_new.json (Crossref + OpenAlex abstract fetch, 2026-10-29).
Edits source_tex/ in place (idempotent only on a fresh copy of the original files).
"""
import csv, json, os, re, sys

LIT = sys.argv[1]
SRC = "source_tex"
old = json.load(open(os.path.join(LIT, "verified_old.json"), encoding="utf-8"))
new = json.load(open(os.path.join(LIT, "verified_new.json"), encoding="utf-8"))

# new papers get keys L36..L45 in the order fetched
recs = {k: v for k, v in old.items() if k.startswith("L")}
for i, (k, v) in enumerate(sorted(new.items()), 36):
    v = dict(v); v["key"] = "L%02d" % i; recs[v["key"]] = v
keys = sorted(recs)

def initials(given):
    out = []
    for part in re.split(r"\s+", given.strip()):
        if not part: continue
        sub = [s for s in part.split("-") if s]
        out.append("-".join(s[0].upper() + "." for s in sub))
    return " ".join(out)

def split_name(full):
    toks = full.split()
    # Crossref gave "Given Family"; family may be multi-token only when the original had it, so keep last token
    return " ".join(toks[:-1]), toks[-1]

def ieee_authors(names, cap=6):
    fm = []
    for n in names:
        g, f = split_name(n); fm.append((initials(g) + " " + f).strip())
    if len(fm) > cap: return fm[0] + " et al."
    if len(fm) <= 2: return " and ".join(fm)
    return ", ".join(fm[:-1]) + ", and " + fm[-1]

def short_authors(names):
    fm = []
    for n in names:
        g, f = split_name(n); fm.append((initials(g) + " " + f).strip())
    if len(fm) == 1: return fm[0]
    if len(fm) == 2: return fm[0] + " and " + fm[1]
    return fm[0] + " et al."

def klass(j):
    if j.startswith("IEEE Transactions"): return "IEEE Trans."
    if "Selected Topics" in j: return "IEEE J-STARS"
    if "Letters" in j: return "IEEE GRSL"
    if "Magazine" in j: return "IEEE GRSM"
    return "IEEE conf."

qual = lambda r: klass(r["journal"]) == "IEEE Trans." and 2020 <= r["year"] <= 2026

# ---------- references.bib: keep F entries untouched, regenerate L entries
bib_old = open(os.path.join(SRC, "references.bib"), encoding="utf-8").read()
fblocks = [b for b in re.split(r"(?m)^(?=@)", bib_old) if re.match(r"@\w+\{F", b)]
def esc(s): return s.replace("&", "\\&")
lbl = []
for k in keys:
    r = recs[k]
    pg = r["page"] or ""
    ent = ["@article{%s," % k,
           " author={%s}," % esc(ieee_authors(r["authors"])),
           " title={{%s}}," % esc(r["title"]),
           " journal={%s}," % esc(r["journal"]),
           " year={%s}," % r["year"]]
    if r.get("vol"): ent.append(" volume={%s}," % r["vol"])
    if r.get("issue"): ent.append(" number={%s}," % r["issue"])
    if pg: ent.append(" pages={%s}," % pg)
    ent.append(" doi={%s}}" % r["doi"])
    lbl.append("\n".join(ent) + "\n")
open(os.path.join(SRC, "references.bib"), "w", encoding="utf-8").write("\n".join(lbl) + "\n" + "".join(fblocks))

# ---------- Table 1 rows
rows1 = []
for n, k in enumerate(keys, 1):
    r = recs[k]
    rows1.append("%d & %s, %d & %s & %s & %s & \\cite{%s} \\\\" % (n, short_authors(r["authors"]), r["year"], esc(r["title"]), esc(r["journal"]), klass(r["journal"]), k))
t1 = open(os.path.join(SRC, "lit_table1.tex"), encoding="utf-8").read()
head = t1.split("\\endfoot")[0] + "\\endfoot\n"
open(os.path.join(SRC, "lit_table1.tex"), "w", encoding="utf-8").write(head + "\n".join(rows1) + "\n\\end{longtable}\n\\end{landscape}\n")

# ---------- Table 2: keep 1..35, append 36..45
extra = {
 "L36": ("Extracts roads from satellite imagery while keeping them connected, because pixel-based methods often fragment roads where buildings or trees occlude them.",
         "Connectivity attention network with strip convolutions and a connectivity attention module; the abstract reports state-of-the-art results on SpaceNet and DeepGlobe. Relevant to producing a connected base road layer.",
         "Benchmark imagery; connectivity of the output is not tested against a planning network and there is no rural Telangana evidence."),
 "L37": ("Builds a road network as a graph by predicting road nodes and the connectivity between them instead of skeletonising a segmentation mask.",
         "NodeConnect, trained jointly on nodes and a connectivity map; compared with segmentation methods on DeepGlobe and RoadTracer with pixel and topological precision and recall. Relevant to the topology of the road layer a planner needs.",
         "Topology is scored on benchmark data; the method does not link houses or facilities to the network."),
 "L38": ("Corrects broken road surfaces and inaccurate topology in road extraction from high-resolution imagery.",
         "Three stages: multi-branch road segmentation, energy-based connectivity refinement and topology correction into a vector network; improvements reported on several public datasets. Relevant to vector road graphs and gaps in them.",
         "Public benchmark data; whether corrected connections exist physically is not checked, and no route planning is done."),
 "L39": ("Extracts roads from satellite images together with partial, incomplete road maps (for example from OpenStreetMap) instead of from scratch.",
         "Two-branch Partial-to-Complete network with a gated self-attention module and a missing-part loss; IoU of 70.71\\% on SpaceNet and 75.52\\% on OSM data are reported. Close to the project situation of an incomplete TGRAC road layer.",
         "Completes road maps; it does not decide how houses should be connected, and rural Indian roads are not evaluated."),
 "L40": ("Learns improvement heuristics that approximate the Pareto front for multi-objective route planning problems such as logistics routing.",
         "Population-based deep reinforcement learning model (Pareto Improver); the abstract reports that it outperforms other state-of-the-art methods on several multi-objective routing problems. Shows that multi-objective routing is an active area.",
         "Vehicle-routing type problems with no terrain cost surface, shared infrastructure or uncertain targets."),
 "L41": ("Plans paths for intelligent vehicles in off-road terrain with several objectives, including terrain-related failure risk and weather.",
         "Actor-critic deep reinforcement learning on a traversability map with meteorology-driven heuristics; reported to beat standard DRL and non-DRL planners in efficiency and convergence stability. Relevant to terrain-aware multi-objective path cost.",
         "Plans one vehicle path; it does not plan a network over many targets, and it is not an infrastructure-planning method."),
 "L42": ("Plans an urban power distribution network by combining GIS data with a hybrid optimisation model.",
         "Extracts the street graph from GIS data, computes shortest paths between nodes, then uses Clark and Wright savings plus mixed-integer programming; reports that shortest-path distances cut investment by more than 30\\% compared with Euclidean or Manhattan distances in an urban Chinese case. Supports using path distances rather than straight lines in network planning.",
         "Urban power network, not rural roads; inputs are street data, not uncertain remote-sensing targets."),
 "L43": ("Improves generalisation of land-cover segmentation to unseen regions, sensors and seasons.",
         "Frequency-based optimal style mix (FOSMix) randomises image style in the frequency domain with a consistency regulariser. Relevant to the transfer question behind C3.",
         "Reports segmentation accuracy under domain shift, not the effect on a downstream plan."),
 "L44": ("Adapts segmentation models across domains for very-high-resolution remote-sensing images.",
         "Curriculum-style local-to-global adaptation using an entropy-based patch score and semantic- and entropy-level domain classifiers. Relevant to cross-village transfer of segmentation.",
         "Needs target-domain images and does not evaluate network planning."),
 "L45": ("Trains one segmentation model from a single source domain so that it works on unseen target domains.",
         "Category Consistency on Domain Randomization (CCDR) randomises texture and style and adds a consistency loss across source and generated domains. Relevant to the case where no labelled target village is available.",
         "Segmentation benchmark results only; downstream plan quality is not studied."),
}
t2 = open(os.path.join(SRC, "lit_table2.tex"), encoding="utf-8").read()
add = "".join("%d & %s & %s & %s \\\\\n" % (int(k[1:]), *extra[k]) for k in sorted(extra))
t2 = t2.replace("\\end{longtable}", add + "\\end{longtable}")
open(os.path.join(SRC, "lit_table2.tex"), "w", encoding="utf-8").write(t2)

# ---------- verification files
meta = []
for k in keys:
    r = recs[k]
    meta.append(dict(key=k, authors="; ".join(r["authors"]), title=r["title"], journal=r["journal"], year=r["year"], volume=r.get("vol") or "",
                     issue=r.get("issue") or "", pages=r.get("page") or "", doi=r["doi"], url="https://doi.org/" + r["doi"],
                     klass=klass(r["journal"]), qualifies=qual(r)))
json.dump(meta, open("lit_verified.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
with open("literature_verification.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f); w.writerow(["key", "authors", "title", "journal", "year", "volume", "issue", "pages_or_article_no", "doi", "url", "class", "counts_toward_30", "verification_source"])
    for m in meta:
        w.writerow([m["key"], m["authors"], m["title"], m["journal"], m["year"], m["volume"], m["issue"], m["pages"], m["doi"], m["url"], m["klass"], "YES" if m["qualifies"] else "NO", "Crossref DOI record, retrieved 2026-10-29"])
print("entries", len(meta), "qualifying", sum(m["qualifies"] for m in meta))
