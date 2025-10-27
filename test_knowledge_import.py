#!/usr/bin/env python3
"""Basic unit tests for KB Automation.

Run with: python3 test_knowledge_import.py
"""

import sys
from pathlib import Path

# Test imports
print("Testing imports...")
try:
    from knowledge_import.config import MAX_RETRIES, PROCESSING_TIMEOUT_SECONDS
    from knowledge_import.scanner import scan_directory
    from knowledge_import.session import validate_api_key, validate_url

    print("✓ All imports successful")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# Test validate_url
print("\nTesting validate_url...")
tests_passed = 0
tests_failed = 0

# Valid URLs
try:
    validate_url("http://localhost:8080")
    validate_url("https://example.com")
    validate_url("http://192.168.1.1:3000")
    tests_passed += 3
    print("✓ Valid URLs accepted")
except ValueError as e:
    print(f"✗ Valid URL rejected: {e}")
    tests_failed += 1

# Invalid URLs
invalid_urls = [
    "",
    "not-a-url",
    "ftp://invalid.com",
    "localhost:8080",  # Missing scheme
]

for url in invalid_urls:
    try:
        validate_url(url)
        print(f"✗ Invalid URL accepted: {url}")
        tests_failed += 1
    except ValueError:
        tests_passed += 1

print(f"✓ Invalid URLs rejected ({len(invalid_urls)} tests)")

# Test validate_api_key
print("\nTesting validate_api_key...")

# Valid API keys
try:
    validate_api_key("sk-abc123456789")
    validate_api_key("sk-f3e55f53a89e834f385aa77a807fe60c")
    tests_passed += 2
    print("✓ Valid API keys accepted")
except ValueError as e:
    print(f"✗ Valid API key rejected: {e}")
    tests_failed += 1

# Invalid API keys
invalid_keys = [
    "",
    "abc123",  # Doesn't start with sk-
    "sk-",  # Too short
    "sk-12345",  # Too short
]

for key in invalid_keys:
    try:
        validate_api_key(key)
        print(f"✗ Invalid API key accepted: {key}")
        tests_failed += 1
    except ValueError:
        tests_passed += 1

print(f"✓ Invalid API keys rejected ({len(invalid_keys)} tests)")

# Test scan_directory with example data
print("\nTesting scan_directory...")
try:
    examples_dir = Path("examples/documents")
    if examples_dir.exists():
        structure = scan_directory(examples_dir)
        if len(structure) == 2:  # Should find 'a' and 'b'
            print(f"✓ Found {len(structure)} knowledge bases")
            tests_passed += 1
        else:
            print(f"✗ Expected 2 KBs, found {len(structure)}")
            tests_failed += 1
    else:
        print("⚠ Example directory not found, skipping scan test")
except Exception as e:
    print(f"✗ Scan failed: {e}")
    tests_failed += 1

# Test scan_directory with invalid path
try:
    scan_directory(Path("/nonexistent/path"))
    print("✗ Invalid directory accepted")
    tests_failed += 1
except ValueError:
    print("✓ Invalid directory rejected")
    tests_passed += 1

# Test configuration constants
print("\nTesting configuration...")
if MAX_RETRIES > 0 and PROCESSING_TIMEOUT_SECONDS > 0:
    print("✓ Configuration constants are valid")
    tests_passed += 1
else:
    print("✗ Configuration constants are invalid")
    tests_failed += 1

# Summary
print("\n" + "=" * 50)
print("TEST SUMMARY")
print("=" * 50)
print(f"Passed: {tests_passed}")
print(f"Failed: {tests_failed}")
print("=" * 50)

if tests_failed == 0:
    print("✓ All tests passed!")
    sys.exit(0)
else:
    print(f"✗ {tests_failed} test(s) failed")
    sys.exit(1)
