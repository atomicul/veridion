#!/usr/bin/env bash

cat websites.txt | xargs -I {} -P 16 ./tools/download-html.sh "{}"
