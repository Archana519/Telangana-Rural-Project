"""Build manuscript.docx from main.tex with pandoc (named, non-anonymous version). Run: python paper_eris/build_docx.py"""
import re, subprocess
from pathlib import Path
H = Path(__file__).resolve().parent
t = (H / "main.tex").read_text(encoding="utf-8")
t = t.replace("\\newif\\ifanon", "").replace("\\ifdefined\\ANON\\anontrue\\fi", "")
t = re.sub(r"\\ifanon.*?\\else(.*?)\\fi", r"\1", t, flags=re.S)
t = t.replace("\\newif\\anon", "").replace("\\ifdefined\\ANON\\anontrue\\fi", "").replace("\\newif\\ifanon", "")
AUTH = [("Ramakrishna Kolikipogu", "krkrishna.cse@gmail.com"), ("Pendyala Archana", "pendyalaarchanareddy98@gmail.com")]
ablock = " \\and ".join(f"{n}\\\\ Department of Information Technology\\\\ Chaitanya Bharathi Institute of Technology (A)\\\\ Hyderabad, India\\\\ {e}" for n, e in AUTH)
title = re.search(r"\{\\Large\\bfseries (.*?)\\par\}", t, re.S).group(1).strip()
t = re.sub(r"\\begin\{center\}(.*?)\\end\{center\}", lambda m: "\\title{" + title + "}\\author{" + ablock + "}\\date{}\\maketitle", t, count=1, flags=re.S)
tmp = H / "_docx_src.tex"; tmp.write_text(t, encoding="utf-8")
subprocess.run(["pandoc", str(tmp.name), "--citeproc", "--bibliography=references.bib", "--number-sections", "-o", "manuscript.docx"], cwd=H, check=True)
tmp.unlink()
