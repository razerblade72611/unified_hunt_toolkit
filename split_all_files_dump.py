import os
import json

# Paths – adjust if needed
dump_path = r"C:\Users\davei\Downloads\Python\unified_hunt_toolkit_clean\_all_files_dump.txt"
root = r"C:\Users\davei\Downloads\Python\unified_hunt_toolkit_clean"
out_dir = os.path.join(root, "_llm_chunks")
index_path = os.path.join(out_dir, "index.jsonl")

# Make output folder
os.makedirs(out_dir, exist_ok=True)

# This is the header I suggested earlier: "# FILE: <path>"
HEADER_PREFIX = "# FILE: "
MAX_CHARS = 15000  # size of each chunk, tweak if you like

def safe_filename(path: str) -> str:
    """Turn a path like 'scripts/foo.py' into a safe filename."""
    repl = path.replace(":", "").replace("\\", "__").replace("/", "__")
    # Keep filenames from getting absurdly long
    if len(repl) > 150:
        base, ext = os.path.splitext(repl)
        repl = base[:140] + "__" + ext
    return repl

current_file = None
buffer = []

index_f = open(index_path, "w", encoding="utf-8")

def flush_current_file():
    """Write the buffered content for current_file into chunk files."""
    if current_file is None:
        return
    if not buffer:
        return

    content = "".join(buffer)
    if not content.strip():
        return

    safe = safe_filename(current_file)

    for part_idx, start in enumerate(range(0, len(content), MAX_CHARS), start=1):
        chunk = content[start:start + MAX_CHARS]
        chunk_name = f"{safe}__part{part_idx}.txt"
        chunk_path = os.path.join(out_dir, chunk_name)

        with open(chunk_path, "w", encoding="utf-8") as cf:
            cf.write(chunk)

        rec = {
            "source_path": current_file,   # original file path from the dump header
            "chunk_file": chunk_name,      # the chunk filename we just wrote
            "part": part_idx,              # part number of this file
        }
        index_f.write(json.dumps(rec) + "\n")

with open(dump_path, "r", encoding="utf-8", errors="ignore") as f:
    for line in f:
        if line.startswith(HEADER_PREFIX):
            # We hit a new file header: flush the previous one
            flush_current_file()

            # Start a new logical file
            current_file = line[len(HEADER_PREFIX):].strip()
            buffer = []
        else:
            if current_file is not None:
                buffer.append(line)

# Flush the final file
flush_current_file()
index_f.close()

print(f"Done. Chunks + index written under: {out_dir}")
