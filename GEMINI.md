# Project Overview

This project is a Python script that automates the process of fetching and summarizing academic papers from the RSS feeds of two top Information Systems journals: MIS Quarterly (MISQ) and Information Systems Journal (ISJ). It uses the Google Gemini Pro model via the `langchain` library to generate concise academic summaries in Chinese.

The script is designed to be run periodically to stay updated on the latest research in the field. It maintains a local memory of processed links to avoid redundant processing.

## Key Technologies

*   **Python 3**
*   **Libraries:**
    *   `feedparser`: For robust RSS feed parsing.
    *   `langchain`: To interface with the Google Gemini language model.
    *   `langchain_google_genai`: For specific integration with Google's generative AI models.
    *   `markdown`: For creating the final report in Markdown format.

## Building and Running

### 1. Prerequisites

Before running the script, you need to have Python 3 installed and the required libraries. You can install them using pip:

```bash
pip install feedparser langchain langchain_google_genai markdown
```

### 2. Configuration

You **must** configure your Google API key in the `script.py` file.

1.  Open `script.py`.
2.  Find the line `GOOGLE_API_KEY = "YOUR_GOOGLE_API_KEY"`
3.  Replace `"YOUR_GOOGLE_API_KEY"` with your actual Google API key.

### 3. Running the Script

To run the script, simply execute it from your terminal:

```bash
python script.py
```

The script will then:
1.  Fetch new articles from the configured RSS feeds.
2.  Generate summaries for any new articles.
3.  Create a `report.md` file in the same directory with the summaries.
4.  Update the `processed_is_links2.csv` file in the `./colab_memory` directory.

## Development Conventions

*   **Modularity:** The script is organized into distinct functions for loading memory, fetching articles, summarizing, and updating files.
*   **Configuration:** Key parameters like the API key, file paths, and LLM settings are grouped together in a configuration section for easy modification.
*   **Error Handling:** The script includes basic error handling for file I/O and API calls.
*   **Comments:** The code is well-commented in both English and Chinese, explaining the purpose of different sections and functions.
