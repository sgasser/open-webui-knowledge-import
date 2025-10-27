#!/usr/bin/env python3
"""Open WebUI Knowledge Import - Bulk import documents into knowledge bases.

Usage:
    # Import all subdirectories from a folder
    ./knowledge_import.py /path/to/documents

    # Import a single directory as a knowledge base
    ./knowledge_import.py /path/to/documents/sales

    # Dry run (preview only)
    ./knowledge_import.py --dry-run /path/to/documents

    # With API key from environment
    export OPENWEBUI_API_KEY=sk-xxx
    ./knowledge_import.py /path/to/documents
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Optional: Load .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from knowledge_import import __version__
from knowledge_import.api import (
    add_files_to_kb,
    create_kb,
    get_existing_kb,
    upload_files_concurrent,
)
from knowledge_import.scanner import scan_directory
from knowledge_import.session import create_session, health_check
from knowledge_import.ui import (
    preview_import,
    print_error,
    print_info,
    print_success,
    print_summary,
    print_warning,
)


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


logger = logging.getLogger(__name__)


def import_knowledge_bases(structure: dict, base_url: str, api_key: str) -> dict:
    """Import all knowledge bases.

    Args:
        structure: Dict mapping KB names to their paths and files
        base_url: Open WebUI base URL
        api_key: Open WebUI API key

    Returns:
        Dict with results for each KB

    Raises:
        ValueError: If inputs are invalid
        ConnectionError: If operations fail
    """
    logger.info(f"Starting import of {len(structure)} knowledge bases")
    results = {}

    # Progress callback for file uploads
    def progress(msg: str) -> None:
        print(msg, end=" ", flush=True)

    with create_session(base_url, api_key) as session:
        for kb_name, data in structure.items():
            print(f"\n📦 Processing: {kb_name}")
            logger.info(f"Processing knowledge base: {kb_name}")

            try:
                # Check if KB already exists
                kb_id = get_existing_kb(session, base_url, kb_name)
                if kb_id:
                    print_warning(f"Knowledge base already exists (ID: {kb_id}), skipping")
                    results[kb_name] = {"success": True, "files": 0, "skipped": True}
                    continue

                # Create KB
                kb_id = create_kb(session, base_url, kb_name)
                print_success("Created knowledge base")

                # Upload files concurrently
                upload_results = upload_files_concurrent(
                    session, base_url, data["files"], progress_callback=progress
                )

                # Collect successful uploads
                file_ids = [r["file_id"] for r in upload_results if r["success"] and r["file_id"]]
                failed_count = sum(1 for r in upload_results if not r["success"])

                if failed_count > 0:
                    print_warning(f"{failed_count} file(s) failed to upload")

                # Add to KB
                if file_ids:
                    print(f"  📎 Adding {len(file_ids)} files to KB...", end=" ", flush=True)
                    try:
                        add_files_to_kb(session, base_url, kb_id, file_ids)
                        print("✓")
                        results[kb_name] = {
                            "success": True,
                            "files": len(file_ids),
                            "failed": failed_count
                        }
                    except (ValueError, ConnectionError) as e:
                        print("✗")
                        print_error(f"Failed to add files to KB: {e}")
                        results[kb_name] = {"success": False, "files": 0}
                else:
                    print_warning("No files uploaded successfully")
                    results[kb_name] = {"success": False, "files": 0, "failed": failed_count}

            except (ValueError, ConnectionError) as e:
                print_error(f"Failed to create KB: {e}")
                results[kb_name] = {"success": False}

    logger.info("Import completed")
    return results


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Production-ready knowledge base automation for Open WebUI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import all subdirectories
  %(prog)s /path/to/documents

  # Import single directory
  %(prog)s /path/to/documents/sales

  # Preview before importing
  %(prog)s --dry-run /path/to/documents

  # Specify file types
  %(prog)s --extensions .pdf,.txt /path/to/documents

  # Enable verbose logging
  %(prog)s --verbose /path/to/documents

Environment:
  OPENWEBUI_URL       Base URL (default: http://localhost:8080)
  OPENWEBUI_API_KEY   API key (required if not using --api-key)
        """
    )

    parser.add_argument("directory", help="Directory to import")
    parser.add_argument("--base-url", default=os.getenv("OPENWEBUI_URL", "http://localhost:8080"))
    parser.add_argument("--api-key", default=os.getenv("OPENWEBUI_API_KEY"))
    parser.add_argument("--extensions", help="File extensions (e.g., .pdf,.txt)")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, don't import")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)
    logger.info(f"KB Automation v{__version__} starting")

    try:
        # Check if .env file exists
        env_file = Path(__file__).parent / ".env"
        if not env_file.exists() and not args.api_key and not os.getenv("OPENWEBUI_API_KEY"):
            print_warning("No .env file found and no API key provided")
            print_info("For production use, create a .env file:")
            print_info("  cp .env.example .env")
            print_info("  # Edit .env with your configuration")
            print_info("\nOr set environment variables:")
            print_info("  export OPENWEBUI_API_KEY=sk-your-key")
            print_info("  export OPENWEBUI_URL=http://localhost:8080\n")

        # Validate directory
        directory = Path(args.directory).resolve()
        if not directory.exists():
            print_error(f"Directory not found: {directory}")
            return 1

        logger.debug(f"Working directory: {directory}")

        # Parse extensions
        extensions = None
        if args.extensions:
            extensions = [f".{ext.strip().lstrip('.')}" for ext in args.extensions.split(",")]
            logger.debug(f"Filtering extensions: {extensions}")

        # Scan directory
        print_info(f"Scanning: {directory}")
        structure = scan_directory(directory, extensions)

        if not structure:
            print_error("No directories with files found!")
            return 1

        # Preview
        preview_import(structure)

        # Dry run?
        if args.dry_run:
            print("\n💡 This was a dry run. Use without --dry-run to import.")
            logger.info("Dry run completed")
            return 0

        # Validate API key
        if not args.api_key:
            print_error("API key required! Set OPENWEBUI_API_KEY or use --api-key")
            return 1

        # Health check
        print_info("Performing health check...")
        try:
            health_check(args.base_url, args.api_key)
            print_success("Health check passed\n")
        except ValueError as e:
            print_error(f"Configuration error: {e}")
            return 1
        except ConnectionError as e:
            print_error(f"Health check failed: {e}")
            print_error("Is Open WebUI running and accessible?")
            return 1

        # Confirm (only in interactive mode)
        if sys.stdin.isatty():
            print("⚠ Press Enter to continue, Ctrl+C to cancel...", end=" ")
            try:
                input()
            except KeyboardInterrupt:
                print("\n✗ Cancelled")
                logger.info("Import cancelled by user")
                return 1
            except EOFError:
                print("\n✗ Cancelled (no input available)")
                logger.info("Import cancelled - no input available")
                return 1
        else:
            # Non-interactive mode - auto-proceed
            logger.info("Non-interactive mode detected - auto-proceeding")

        # Import
        results = import_knowledge_bases(structure, args.base_url, args.api_key)

        # Summary
        print_summary(results)

        # Return error if any failed
        failed = sum(1 for r in results.values() if not r.get("success"))
        if failed > 0:
            logger.warning(f"Import completed with {failed} failures")
            return 1
        else:
            logger.info("Import completed successfully")
            return 0

    except KeyboardInterrupt:
        print("\n✗ Interrupted")
        logger.warning("Program interrupted by user")
        return 1
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        logger.critical(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
