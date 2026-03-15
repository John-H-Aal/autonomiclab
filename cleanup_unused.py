#!/usr/bin/env python3
"""
Move unused files in autonomiclab to to_be_deleted/.
Based on static import analysis of main_window.py as entry point.

Run from project root:  python cleanup_unused.py
Add --dry-run to preview without moving anything.
"""

import ast
import sys
import shutil
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent  # adjust if script is placed elsewhere
PACKAGE_ROOT = PROJECT_ROOT / "autonomiclab"
DEST_DIR     = PROJECT_ROOT / "to_be_deleted"

ENTRY_POINTS = [
    PACKAGE_ROOT / "gui" / "main_window.py",
]

# Files known to be used indirectly (resources, configs, data files)
# that static analysis won't catch
WHITELIST = {
    "autonomiclab/__init__.py",
    "autonomiclab/__main__.py",        # python -m autonomiclab entry point
    "autonomiclab/config/__init__.py",
    "autonomiclab/config/fonts.yaml",   # loaded by font_loader at runtime
    "autonomiclab/core/__init__.py",
    "autonomiclab/gui/__init__.py",
    "autonomiclab/models/__init__.py",
    "autonomiclab/plotting/__init__.py",
    "autonomiclab/utils/__init__.py",
    "autonomiclab/analysis/__init__.py",
    "autonomiclab/resources/__init__.py",
}

# ── Static import walker ───────────────────────────────────────────────────────

def collect_imports(filepath: Path, visited: set[Path], package_root: Path) -> set[Path]:
    """Recursively collect all local .py files reachable from filepath via imports."""
    if filepath in visited or not filepath.exists():
        return visited
    visited.add(filepath)

    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8"))
    except SyntaxError as e:
        print(f"  [WARN] Syntax error in {filepath}: {e}")
        return visited

    for node in ast.walk(tree):
        module_parts = None

        if isinstance(node, ast.Import):
            for alias in node.names:
                module_parts = alias.name.split(".")
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                base = node.module.split(".")
                level = node.level  # relative import dots
                if level:
                    # relative import: resolve against current package
                    anchor = filepath.parent
                    for _ in range(level - 1):
                        anchor = anchor.parent
                    module_parts = list(anchor.relative_to(package_root.parent).parts) + base
                else:
                    module_parts = base

        if not module_parts:
            continue

        # Try to resolve to a file inside the package
        candidate = package_root.parent
        for part in module_parts:
            candidate = candidate / part

        # Could be a package (dir) or module (file)
        for path in [candidate.with_suffix(".py"), candidate / "__init__.py"]:
            if path.exists() and package_root in path.parents:
                collect_imports(path, visited, package_root)

    return visited


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    dry_run = "--dry-run" in sys.argv

    if dry_run:
        print("=== DRY RUN — nothing will be moved ===\n")

    # Collect all reachable files
    reachable: set[Path] = set()
    for entry in ENTRY_POINTS:
        collect_imports(entry, reachable, PACKAGE_ROOT)

    # All .py files in package
    all_py = set(PACKAGE_ROOT.rglob("*.py"))

    # Determine unused
    unused = all_py - reachable

    # Filter out whitelisted paths
    def in_whitelist(p: Path) -> bool:
        try:
            rel = p.relative_to(PROJECT_ROOT).as_posix()
        except ValueError:
            return False
        return rel in WHITELIST

    to_move = [p for p in sorted(unused) if not in_whitelist(p)]

    if not to_move:
        print("✓ No unused files found.")
        return

    print(f"{'Would move' if dry_run else 'Moving'} {len(to_move)} file(s):\n")

    for src in to_move:
        rel = src.relative_to(PROJECT_ROOT)
        dst = DEST_DIR / rel
        print(f"  {rel}")
        if not dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))

    if not dry_run:
        print(f"\n✓ Done. Files moved to: {DEST_DIR}")
        print("  Review and delete the folder when satisfied.")
    else:
        print(f"\nRun without --dry-run to perform the move.")


if __name__ == "__main__":
    main()