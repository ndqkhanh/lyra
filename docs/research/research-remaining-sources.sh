#!/bin/bash
# Research remaining sources systematically

LEDGER="source-ledger.md"
FINDINGS="findings.md"
LOG="research-log.md"

# Get all todo sources
grep "| todo |" "$LEDGER" | while IFS='|' read -r num url section status rest; do
    url=$(echo "$url" | xargs)
    section=$(echo "$section" | xargs)
    
    echo "Processing: $url"
    
    # Skip if already processed
    if grep -q "$url" "$FINDINGS" 2>/dev/null; then
        echo "  Already in findings, skipping"
        continue
    fi
    
    # Try to fetch
    if [[ "$url" == *"arxiv.org"* ]]; then
        echo "  ArXiv paper - would fetch abstract"
    elif [[ "$url" == *"openreview.net"* ]]; then
        echo "  OpenReview paper - would fetch PDF"
    elif [[ "$url" == *"github.com"* ]]; then
        echo "  GitHub repo - would clone/analyze"
    else
        echo "  Documentation - would fetch"
    fi
done

echo "Total todo sources found:"
grep -c "| todo |" "$LEDGER"
