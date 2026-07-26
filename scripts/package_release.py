from pathlib import Path
import hashlib, zipfile
root=Path(__file__).resolve().parents[1]
out=root.parent/f"{root.name}-v0.1.0.zip"
exclude={".git",".venv","__pycache__",".pytest_cache",".mypy_cache",".ruff_cache","node_modules"}
with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
    for file in sorted(root.rglob("*")):
        if not file.is_file() or any(part in exclude for part in file.parts): continue
        z.write(file,file.relative_to(root.parent))
digest=hashlib.sha256(out.read_bytes()).hexdigest()
(out.with_suffix(out.suffix+".sha256")).write_text(f"{digest}  {out.name}\n",encoding="utf-8")
print(out);print(digest)
