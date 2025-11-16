
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This project is a Python script that automatically fetches the latest academic paper abstracts from top Information Systems (IS) journals (MISQ, ISJ, and EJIS) via RSS feeds. It then uses the Google Gemini language model to generate a consolidated summary in Chinese for new publications from each journal. The final output is a markdown-formatted report.

## High-Level Architecture

The script operates in a sequential workflow, orchestrated by the `main()` function in `script.py`:

1.  **Configuration**: Key parameters like the Google API Key (loaded from an environment variable), the model name (`gemini-2.5-pro`), RSS feed URLs, and a memory file (`processed_is_links2.csv`) for tracking previously processed articles are defined.
2.  **Fetch Articles**: The `fetch_articles` function (in `script.py`) iterates through configured RSS feeds using `feedparser`, extracts article data (title, link, summary), and encapsulates it into `langchain_core.documents.Document` objects. It skips already processed links and incomplete entries.
3.  **Analyze Articles Individually**: The `analyze_articles_individually` function (in `script.py`) initializes the `ChatGoogleGenerativeAI` model. It processes each new article by sending its abstract to the Gemini model with a predefined prompt to extract the core research question, methodology, and key findings, presented in Chinese.
4.  **Save Report**: The `save_report` function (in `script.py`) compiles the generated summaries and analyses into a markdown report, which is then saved to `report.md`.

## Key Components

*   `script.py`: The main script containing the core logic for fetching, analyzing, and reporting.
*   `requirements.txt`: Lists Python dependencies: `feedparser`, `langchain-core`, `langchain-google-genai`, `langchain_classic`, `markdown`.
*   `processed_is_links2.csv`: A CSV file used to store and track previously processed article links.

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
This script is a standalone web scraper for MIS Quarterly (MISQ) articles. It uses `requests` and `BeautifulSoup` to fetch issue links, filter them by year, and then extract article titles, links, and abstracts directly from the MISQ website. This script is not currently integrated into the main `script.py` workflow.
