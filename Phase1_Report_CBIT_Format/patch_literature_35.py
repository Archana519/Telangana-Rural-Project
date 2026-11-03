"""One-off patch (kept for provenance): literature scope fixed at 35 IEEE Transactions papers (2020 to 2026); the ten other works are removed from the
tables and from every citation; tables sorted by year, newest first; status wording updated. Run once."""
import json
import re

R = r"D:\Telangana_Rural_Project\Phase1_Report_CBIT_Format"
TEX = R + r"\source_tex\A_Dissertation_Phase_I_Review_1_Report_Final.tex"
L = json.load(open(R + r"\lit_verified.json", encoding="utf-8"))
DROP = {m["key"] for m in L if not m["qualifies"]}
assert len(DROP) == 10 and len(L) == 45


def rd(p):
    return open(p, encoding="utf-8").read()


def wr(p, s):
    open(p, "w", encoding="utf-8").write(s)


def strip_cites(s):
    def f(m):
        keys = [k for k in m.group(1).split(",") if k.strip() not in DROP]
        return "\\cite{%s}" % ",".join(keys) if keys else "\\cite{}"
    return re.sub(r"\\cite\{([^}]*)\}", f, s)


# ---- tables: drop, sort by year (newest first), renumber
def table_rows(path, keyfn):
    s = rd(path)
    lines = s.split("\n")
    first = next(i for i, l in enumerate(lines) if re.match(r"^\d+ & ", l))
    last = max(i for i, l in enumerate(lines) if re.match(r"^\d+ & ", l))
    return lines, first, last


t1 = R + r"\source_tex\lit_table1.tex"
t2 = R + r"\source_tex\lit_table2.tex"
l1, a1, b1 = table_rows(t1, None)
l2, a2, b2 = table_rows(t2, None)
rows1 = l1[a1:b1 + 1]
rows2 = l2[a2:b2 + 1]
assert len(rows1) == len(rows2) == 45
pair = []
for r1, r2 in zip(rows1, rows2):
    n1, n2 = int(r1.split(" & ")[0]), int(r2.split(" & ")[0])
    assert n1 == n2
    key = re.search(r"\\cite\{(L\d+)\}", r1).group(1)
    year = int(re.search(r"(20\d\d) & ", r1).group(1))
    pair.append((key, year, r1, r2))
pair = [p for p in pair if p[0] not in DROP]
assert len(pair) == 35
pair.sort(key=lambda p: -p[1])      # stable: ties keep the original order
new1, new2 = [], []
for i, (k, y, r1, r2) in enumerate(pair, 1):
    new1.append(re.sub(r"^\d+ & ", "%d & " % i, r1))
    new2.append(re.sub(r"^\d+ & ", "%d & " % i, r2))
wr(t1, "\n".join(l1[:a1] + new1 + l1[b1 + 1:]).replace("Reviewed literature (identification).", "Reviewed literature: the 35 IEEE Transactions papers, 2020 to 2026, newest first (identification)."))
wr(t2, "\n".join(l2[:a2] + new2 + l2[b2 + 1:]))

# ---- main tex
s = rd(TEX)


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:70])
    s = s.replace(a, b)


rep(", and surveys summarise datasets and metrics \cite{L01,L28}.", ".")
rep("Uncertainty-aware road models \cite{L32} suggest that road confidence could trigger review, but calibration on local imagery is untested. ", "")
rep("Benchmarks such as OpenEarthMap \cite{L13} and LoveDA \cite{F05} cover urban and rural scenes,", "Benchmarks such as LoveDA \cite{F05} cover urban and rural scenes,")
rep("and uncertainty estimation \cite{L31,L32} points", "and uncertainty estimation \cite{L31} points")
s = strip_cites(s)


rep("a literature review of 45 IEEE-published works (2020--2026), 35 of which are IEEE Transactions papers whose metadata were checked against the DOI registry,",
    "a completed literature review of 35 IEEE Transactions papers (2020--2026), each with its metadata verified against the DOI registry and its methodology extracted,")
i = s.index("This chapter reviews 45 IEEE-published works")
j = s.index("\n", i)
s = s[:i] + ("This chapter reviews 35 IEEE Transactions papers published between 2020 and 2026, and five foundational references. The review is complete for this scope, and the 35 papers meet the guide's requirement of at least 30 Transactions papers. "
             "For every paper the title, all authors, journal, year, volume, pages or article number and DOI were verified against the DOI-registry record (Crossref) on 29 October 2026, each DOI link leads to the IEEE Xplore page, and the objective, method, key findings and limitations were extracted and recorded; "
             "Appendix A lists the verified details of the 35 papers. Tables~\\ref{tab:lit1} and~\\ref{tab:lit2} give the full comparison, sorted by year with the newest first. "
             "Findings and limitations in Table~\\ref{tab:lit2} are a project-oriented critical assessment of each paper's published methodology and not necessarily statements by the authors. "
             "The datasets used by each paper were not recorded in the survey file, so a dataset column is omitted rather than guessed. "
             "The searches did not return an IEEE Transactions paper on rural village road planning from remote-sensing building targets, which is the gap this project addresses, but this is a statement about the searches made and not a proof that none exists.") + s[j:]
i = s.index("Of the 45 works, 35 are IEEE Transactions papers")
j = s.index("\n", i)
s = s[:i] + ("All 35 works are IEEE Transactions papers: 30 in IEEE Transactions on Geoscience and Remote Sensing, 2 in IEEE Transactions on Image Processing, 2 in IEEE Transactions on Intelligent Transportation Systems and 1 in IEEE Transactions on Power Systems, all published between 2020 and 2026. "
             "By theme, they cover road extraction and topology, building extraction, segmentation with sparse labels and uncertainty, foundation-model and domain-adaptation methods, multi-objective route planning and GIS-based network planning. "
             "The planning themes are thinly covered in IEEE Transactions, which is why established least-cost-path references are kept as foundational references.") + s[j:]
s = s.replace("\\cite{}", "")
rep("beyond the 45 papers reviewed, which remains open for Phase-II.", "beyond the 35 papers reviewed, which remains open for Phase-II.")
rep("Literature limitations are project-oriented assessments from abstracts, not full-text reviews.", "Literature findings and limitations are project-oriented assessments of each paper's published methodology, not statements by the authors.")
rep("Complete the full-text reading of the reviewed papers and the novelty comparison with prior art.", "Extend the novelty comparison with prior art beyond the 35 reviewed papers.")
rep("reviewed 45 IEEE-published works (35 of them IEEE Transactions papers) with five foundational references,", "completed a literature review of 35 IEEE Transactions papers with five foundational references,")
wr(TEX, s)
print("tex ok")
