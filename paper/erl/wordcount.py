"""Approximate ERL word count: main text only (excludes title, abstract, tables, figures, captions, equations, citations, acknowledgements, back matter, references)."""
import re, pathlib
t = pathlib.Path(__file__).with_name("main.tex").read_text()
body = t.split("\\begin{document}")[1].split("\\maketitle")[1].split("\\ack")[0]
b = re.sub(r"(?m)^\s*%.*$", "", body)
b = re.sub(r"\\begin\{(figure|table)\}.*?\\end\{\1\}", " ", b, flags=re.S)
b = re.sub(r"\\begin\{equation\}.*?\\end\{equation\}", " ", b, flags=re.S)
b = re.sub(r"\\cite\{[^}]*\}|\\(label|ref)\{[^}]*\}", " ", b)
b = re.sub(r"\\(section|subsection|paragraph)\*?\{([^}]*)\}", r" \2 ", b)
b = re.sub(r"\\(emph|textsc|textbf|texttt|textit)\{([^}]*)\}", r"\2", b)
b = re.sub(r"\$[^$]*\$", " M ", b)
b = b.replace("\\%", "%").replace("{,}", "").replace("~", " ")
b = re.sub(r"\\[a-zA-Z]+", "", b).replace("{", "").replace("}", "")
a = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", t, re.S).group(1)
a = re.sub(r"\$[^$]*\$", " M ", a).replace("\\%", "%").replace("{,}", "").replace("~", " ")
a = re.sub(r"\\[a-zA-Z]+", "", a).replace("{", "").replace("}", "")
print("main-text words:", len(b.split()), "(ERL Letters limit 4000, excluding title, abstract, figures, tables, captions, references)")
print("abstract words:", len(a.split()))
