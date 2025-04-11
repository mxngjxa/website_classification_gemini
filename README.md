<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" class="logo" width="120"/>

# Website Content Classification System

## Overview

This system processes URLs to validate accessibility, extract content, and classify the content based on specified topics using the Gemini AI model. It's designed for efficient categorization of websites, particularly for sensitive topics like drugs, tobacco, and violence, with support for both English and Chinese content.

## Features

- **URL Validation**: Checks if websites are accessible before processing
- **Content Extraction**: Extracts relevant text content from HTML pages
- **AI-Powered Classification**: Uses Google's Gemini AI to categorize content
- **Parallel Processing**: Efficiently handles large batches of URLs simultaneously
- **Comprehensive Error Handling**: Logs and categorizes different types of errors
- **Multi-language Support**: Works with both English and Chinese content


## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/website-classifier.git
cd website-classifier

# Create and activate a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate

# Install dependencies
pip install requests beautifulsoup4 python-dotenv tqdm google-generativeai openai
```


## Configuration

Create a `.env` file in the project root directory with your API keys:

```
GOOGLE_API_KEY=your_gemini_api_key_here
```


## Usage

```bash
python main.py &lt;input_file.txt&gt; [max_workers]
```


### Arguments

- `input_file.txt`: A text file where each line is a URL to process. The filename (without extension) determines the classification topic.
- `max_workers` (Optional): The number of parallel threads to use. Default is 10.


### Input File Format

Each line in the input file should contain a single URL:

```
https://example.com
https://anotherwebsite.org
example.net
```


### Output

The script generates two output files:

1. `{topic}_labeled.txt`: Contains each URL with its classification label
    - `p`: Related to the specified topic
    - `u`: Unrelated to the topic
    - `i`: Inaccessible or error occurred
2. `{topic}_error_messages.log`: Detailed error report for troubleshooting

## Classification Topics

The system supports the following topics (derived from the input filename):

- `drugs`: Content related to illegal drugs, drug abuse, recreational/psychedelic drugs
- `tobacco`: Content about vaping, traditional tobacco products, stores, and advocacy
- `violence`: Content covering BB guns, airsoft, and real firearms


## Error Logging System

The system includes a robust error logging mechanism that:

- Categorizes errors by type (connection, parsing, API, etc.)
- Groups similar errors to reduce redundancy
- Provides a summary of error occurrences and affected URLs
- Creates detailed log files for troubleshooting


## License

[Specify your license information here]

---

# Error Logger Module

## Overview

`ErrorLogger` is a utility class for collecting, categorizing, and summarizing errors during processing operations. It's designed to help with debugging and quality assurance by providing structured error reporting.

## Features

- **Error Categorization**: Organizes errors by type (e.g., connection, API, parsing)
- **URL Tracking**: Links errors to the specific URLs where they occurred
- **Error Summarization**: Generates formatted reports with error counts and details
- **Redundancy Management**: Groups similar errors to avoid repetitive reporting
- **Timestamp Recording**: Includes processing date and time in reports


## Usage

```python
from error_logger import ErrorLogger

# Initialize with base filename (used to generate the log filename)
logger = ErrorLogger("my_process_file.txt")

# Log errors by type
logger.log_error("connection", "https://example.com", "Connection timeout after 10s")
logger.log_error("parsing", "https://broken-site.org", "Invalid HTML structure")

# Multiple errors of the same type
logger.log_error("api", "https://api-site.com", "Rate limit exceeded")
logger.log_error("api", "https://another-api.com", "Rate limit exceeded")

# Write the error summary to a file
logger.write_log()  # Creates my_process_file_error_messages.log
```


## Methods

### `__init__(base_filename)`

Initializes the error logger with a base filename for the log file.

### `log_error(error_type, url, error_message)`

Records an error with its type, affected URL, and description.

### `get_summary()`

Generates a formatted report of all logged errors, grouped by type.

### `write_log()`

Writes the error summary to a log file named after the base filename.

## Output Format

The generated log file contains:

- A timestamp header
- Total error count
- Sections for each error type
- Grouped similar errors with affected URLs
- For errors affecting many URLs, a sample is shown with a count of remaining occurrences


## Integration

This module is designed to work seamlessly with web scraping, API interaction, and data processing pipelines where multiple points of failure may exist.

<div>⁂</div>

[^1]: https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/60588710/46ff63cc-8806-4422-b4fa-6fdf54e5a27b/paste.txt

