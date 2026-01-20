#!/usr/bin/env bash

process_site() {
    DOMAIN="$1"
    DATA_DIR="./data/$DOMAIN"
    INPUT_FILE="$DATA_DIR/index.html"
    OUTPUT_FILE="$DATA_DIR/logo.json"

    if [ -f "$INPUT_FILE" ]; then
        ./tools/extract-logo.py "$DOMAIN" < "$INPUT_FILE" > "$OUTPUT_FILE" \
        && echo "Success: $DOMAIN" \
        || echo "Failed: $DOMAIN"
    else
        echo "Skipping: $DOMAIN (No index.html)"
    fi
}

export -f process_site

ls data | xargs -I {} -P 16 bash -c 'process_site "$@"' _ "{}"
