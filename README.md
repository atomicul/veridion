# Logo Clustering Pipeline Report

## Overview

This pipeline downloads website homepages, extracts logo candidates using heuristics, and clusters visually similar logos using perceptual hashing.

## Pipeline Stages

### Stage 1: Download HTML (`1-download-html.sh`)

Downloads homepage HTML for each domain in `websites.txt`.

| Metric | Count |
|--------|-------|
| Input domains | 4,384 |
| Successfully downloaded | 3,267 |
| Failed downloads | 1,117 (25.5%) |

### Stage 2: Extract Logo Candidates (`2-extract-logo.sh`)

Parses HTML to find and score logo candidates. Each candidate receives a score based on multiple signals.
This was the first big problem of the take-home. How to tell a logo from a website?
For simplicity, and because most commercial websites are SEO optimized, I deliberately did not support
client-side rendered websites. I came up with a list of heuristics to identify the logo solely by the html
document.

**Scoring Heuristics:**

| Signal | Score |
|--------|-------|
| Schema.org Organization logo | +60 |
| Image linked to homepage | +50 |
| Keyword match (logo/brand/identity) | +20 |
| Filename contains domain name | +20 |
| Located in header | +10 |
| Alt text contains "logo" | +10 |
| Favicon/touch icon | +10 |
| OpenGraph image | +5 |
| Located in footer | -30 |
| Negative keywords (partner/client/sponsor) | -50 |

**Extraction Results:**

| Metric | Count |
|--------|-------|
| Sites processed | 3,267 |
| Sites with logo candidates | 2,821 |
| Sites with no candidates | 446 |

### Stage 3: Download Logos (`3-download-logos.sh`)

Downloads the top-scoring logo for each site if score >= 50.

**Score Distribution:**

| Score Range | Count |
|-------------|-------|
| 90+ | 994 |
| 70-89 | 410 |
| 50-69 | 745 |
| 30-49 | 305 (filtered out) |
| <30 | 367 (filtered out) |

| Metric | Count |
|--------|-------|
| Logos passing threshold (>=50) | 2,149 |
| Logos below threshold | 672 |
| Logos successfully downloaded | 2,052 |

### Stage 4: Cluster Logos (`4-cluster-logos.py`)

Clusters logos using perceptual hashing (phash) without ML. Two logos are grouped if their Hamming distance is <= 8 (out of 64 bits).

This was the second big problem of the assesment. You asked if this could be done
without ML, but that depends on what the scope of the problem is. Given the
context you provided in the problem statement, I thought the goal was to cluster
websites (or their underlying company), by the logo in order to figure out how
the logo speaks for the companys' values. With this particular goal in mind,
I thought the answer is that it cannot be done without ML, so the first thing
I did was to run the HDBSCAN algorithm, but the results were disappointing, so
I scratched that idea.

Another thing I noticed from the input data was that many of the websites belong
to the same company, but under different TLDs. So I thought a simpler take for
the objective would be to just identify identical images. Of course this isn't
trivial either, since you have to deal with different scaling and aspect ratios,
etc. But it is a solved problem.

Just as [this](https://www.hackerfactor.com/blog/index.php?/archives/432-Looks-Like-It.html)
article says: dhash works great and phash works even better.

**Results:**

| Metric | Count |
|--------|-------|
| Logos successfully hashed | 2,023 |
| Multi-logo clusters | 218 |
| Singleton logos | 502 |
| Largest cluster | 219 logos |

### Stage 5: Visualize (`5-visualize-clusters.py`)

Just a web page to view the results.
