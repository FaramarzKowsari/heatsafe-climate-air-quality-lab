from pathlib import Path
import re, sys
root=Path(__file__).resolve().parents[1]
patterns=[re.compile(r"ghp_[A-Za-z0-9]{20,}"),re.compile(r"sk-[A-Za-z0-9]{20,}"),re.compile(r"AIza[0-9A-Za-z_-]{20,}")]
hits=[]
for file in root.rglob("*"):
    if not file.is_file() or ".git" in file.parts or file.suffix in {".zip",".png",".jpg",".pyc"}: continue
    try: text=file.read_text(encoding="utf-8")
    except UnicodeDecodeError: continue
    for pattern in patterns:
        if pattern.search(text): hits.append(str(file.relative_to(root)))
if hits:
    print("Potential secrets:",*hits,sep="\n");sys.exit(1)
print("No common high-confidence secret patterns found.")
