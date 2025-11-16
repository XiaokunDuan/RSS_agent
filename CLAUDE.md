# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This project is a Python script that automatically fetches the latest academic paper abstracts from top Information Systems journals (MISQ & ISJ) via RSS feeds. It then uses the Google Gemini language model to generate a consolidated summary in Chinese for each journal's new publications.

## High-Level Architecture

The script operates in a sequential workflow:

1.  **Configuration**: Key parameters like the Google API Key, model name (`gemini-2.5-pro`), and RSS feed URLs are defined at the top of `script.py`.
2.  **Fetch Articles**: The `fetch_articles` function iterates through the RSS feeds using the `feedparser` library, extracts article data (title, link, summary), and encapsulates it into `langchain_core.documents.Document` objects.
3.  **Summarize Journals**: The `summarize_journals_batch` function groups the articles by journal. For each journal, it invokes the Google Gemini model via `langchain-google-genai` to create a single, synthesized summary of all new papers.
4.  **Save Report**: The final output, a markdown-formatted report, is saved to `report.md` by the `save_report` function.

The main execution is handled by the `main()` function, which orchestrates these steps.

## Common Commands

### 1. Setup

Before running the script, install the required Python packages:

```bash
pip install feedparser langchain-core langchain-google-genai langchain_classic markdown
```

**IMPORTANT**: The Google API key is loaded from an environment variable in `script.py`. Ensure it is set as an environment variable (e.g., `export GOOGLE_API_KEY='YourActualApiKeyHere'`) before running the script.

### 2. Running the Script

To execute the script and generate a new report:

```bash
python script.py
```

The script will print progress to the console and create/overwrite the `report.md` file with the latest summaries.

## Additional Scripts

### `scrape_misq.py`
This script is a standalone web scraper for MIS Quarterly (MISQ) articles. It uses `requests` and `BeautifulSoup` to fetch issue links, filter them by year, and then extract article titles, links, and abstracts directly from the MISQ website. It currently operates independently and is not integrated into the main `script.py` workflow, which obtains MISQ data via RSS feeds.
