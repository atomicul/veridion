#!/usr/bin/env bash

OUTPUT_DIR="./data/$1"

mkdir -p "$OUTPUT_DIR"

curl -o- -sL >"$OUTPUT_DIR/index.html" -m 120 "$1" \
&& echo "Success $1" \
|| {
    echo "Failed $1"
    rm -rf "$OUTPUT_DIR"
    exit 1
}
