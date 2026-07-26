from pathlib import Path
import re, sys
root=Path(__file__).resolve().parents[1]
missing=[]
pat=re.compile(r"\[[^\]]+\]\((?!https?://|mailto:|#)([^)]+)\)")
for file in root.rglob("*.md"):
    text=file.read_text(encoding="utf-8")
    for link in pat.findall(text):
        target=(file.parent/link.split("#",1)[0]).resolve()
        if link and not target.exists(): missing.append((file.relative_to(root),link))
if missing:
    for item in missing: print("MISSING",*item)
    sys.exit(1)
print("All relative Markdown links resolve.")
