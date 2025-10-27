"""User interface functions - print helpers."""

import sys


def print_info(msg: str) -> None:
    """Print info message."""
    print(f"ℹ {msg}")


def print_success(msg: str) -> None:
    """Print success message."""
    print(f"✓ {msg}")


def print_error(msg: str) -> None:
    """Print error message."""
    print(f"✗ {msg}", file=sys.stderr)


def print_warning(msg: str) -> None:
    """Print warning message."""
    print(f"⚠ {msg}")


def preview_import(structure: dict) -> None:
    """Show what will be imported."""
    print("\n" + "=" * 60)
    print("PREVIEW - What will be imported:")
    print("=" * 60)

    if not structure:
        print("⚠ No directories with files found!")
        return

    for kb_name, data in structure.items():
        print(f"\n📦 Knowledge Base: {kb_name}")
        print(f"   Location: {data['path']}")
        print(f"   Files ({len(data['files'])}):")
        for f in data["files"]:
            size_kb = f.stat().st_size / 1024
            print(f"     • {f.name} ({size_kb:.1f} KB)")

    print("\n" + "=" * 60)
    print(f"Total: {len(structure)} knowledge bases, {sum(len(d['files']) for d in structure.values())} files")
    print("=" * 60)


def print_summary(results: dict) -> None:
    """Print final summary."""
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    success_count = sum(1 for r in results.values() if r.get("success"))
    skipped_count = sum(1 for r in results.values() if r.get("skipped"))
    file_count = sum(r.get("files", 0) for r in results.values() if not r.get("skipped"))

    for kb_name, result in results.items():
        if result.get("skipped"):
            print(f"⊘ {kb_name}: skipped (already exists)")
        elif result.get("success"):
            print(f"✓ {kb_name}: {result.get('files', 0)} files")
        else:
            print(f"✗ {kb_name}: failed")

    print("=" * 60)
    if skipped_count > 0:
        print(f"Imported: {success_count - skipped_count}/{len(results)} knowledge bases, {file_count} files")
        print(f"Skipped: {skipped_count} (already existed)")
    else:
        print(f"Imported: {success_count}/{len(results)} knowledge bases, {file_count} files")
    print("=" * 60)
