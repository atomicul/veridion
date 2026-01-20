#!/usr/bin/env bash

MIN_SCORE=${1:-50}
DATA_DIR="./data"
CSV_FILE="$DATA_DIR/staged-logos.csv"
JOBS=16
DOWNLOAD_LIST=$(mktemp)

trap 'rm -f "$DOWNLOAD_LIST"' EXIT

if [ ! -d "$DATA_DIR" ]; then
    echo "Error: '$DATA_DIR' directory not found."
    exit 1
fi

echo "domain,local_path" > "$CSV_FILE"

count_cached=0
count_queued=0

while IFS=$'\t' read -r json_path url; do
    if [[ -z "$url" ]]; then continue; fi

    site_dir=$(dirname "$json_path")
    domain=$(basename "$site_dir")

    clean_url="${url%%\?*}"
    filename=$(basename "$clean_url")
    ext="img"
    
    if [[ "$filename" == *.* ]]; then
        candidate_ext="${filename##*.}"
        if [ ${#candidate_ext} -le 4 ]; then
            ext="$candidate_ext"
        fi
    fi

    local_filename="staged_logo.$ext"
    local_path="$site_dir/$local_filename"

    if [ -f "$local_path" ]; then
        echo "$domain,$local_path" >> "$CSV_FILE"
        ((count_cached++))
    else
        echo -e "$url\t$local_path\t$domain" >> "$DOWNLOAD_LIST"
        ((count_queued++))
    fi

done < <(find "$DATA_DIR" -name "logo.json" -exec jq -r "input_filename + \"\t\" + (.[0] | select(.score >= $MIN_SCORE) | .url // empty)" {} +)

echo "Found $count_cached cached logos."
echo "Queuing $count_queued logos for download..."

if [ "$count_queued" -gt 0 ]; then
    download_worker() {
        IFS=$'\t' read -r url target_path domain <<< "$1"

        if [[ -z "$url" || -z "$target_path" ]]; then return; fi

        if curl -sL -f -m 10 -A "Mozilla/5.0" "$url" -o "$target_path"; then
            echo "$domain,$target_path"
        else
            rm -f "$target_path"
        fi
    }
    export -f download_worker

    xargs -P "$JOBS" -L 1 -I {} bash -c 'download_worker "$1"' _ "{}" < "$DOWNLOAD_LIST" >> "$CSV_FILE"
fi

echo "Done. Manifest saved to $CSV_FILE"
