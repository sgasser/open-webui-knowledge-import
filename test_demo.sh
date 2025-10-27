#!/bin/bash
# Demo script showing how kb_automation.py would work

echo "=================================="
echo "KB Automation Demo"
echo "=================================="
echo

echo "What the script would do:"
echo

echo "1. Authenticate with Open WebUI"
echo "   URL: http://172.18.0.5:8080"
echo "   Using API Key: sk-xxxxx"
echo

echo "2. Scan directory: examples/documents/"
echo "   Found subdirectories:"
ls -1 examples/documents/
echo

echo "3. Processing subdirectory: a"
echo "   Files found:"
ls examples/documents/a/
echo "   - Create knowledge base 'a'"
echo "   - Upload sample1.txt (ID: file-001)"
echo "   - Upload sample2.md (ID: file-002)"
echo "   - Add 2 files to KB 'a'"
echo

echo "4. Processing subdirectory: b"
echo "   Files found:"
ls examples/documents/b/
echo "   - Create knowledge base 'b'"
echo "   - Upload document1.txt (ID: file-003)"
echo "   - Upload document2.md (ID: file-004)"
echo "   - Add 2 files to KB 'b'"
echo

echo "============================================================"
echo "SUMMARY"
echo "============================================================"
echo "a: 2/2 files uploaded"
echo "b: 2/2 files uploaded"
echo "============================================================"
echo

echo "To run for real:"
echo "  1. Get API key from Open WebUI (Settings → Account → API Key)"
echo "  2. Run: python kb_automation.py --base-url http://172.18.0.5:8080 --api-key sk-YOUR-KEY --documents-dir examples/documents"
