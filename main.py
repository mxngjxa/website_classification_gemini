# filepath: /Users/jacky/workspaces/deledao/cwcm/chinese_classifier_paralell/main.py

"""
This script processes a list of URLs, validates their accessibility, extracts text content,
and classifies the content based on a specified topic using the Gemini AI model.

Features:
- Validates website URLs for accessibility.
- Extracts text content from HTML pages.
- Classifies website content into predefined topics using the Gemini AI model.
- Logs errors encountered during processing.
- Supports parallel processing of URLs for improved performance.

Usage:
    python main.py <input_file.txt> [max_workers]

Arguments:
    input_file.txt: A text file where each line is a URL to process.
    max_workers: (Optional) The number of threads to use for parallel processing. Default is 10.

Dependencies:
    - requests
    - BeautifulSoup (from bs4)
    - dotenv
    - tqdm
    - concurrent.futures
    - Gemini AI SDK (google.genai)
"""

import os
import sys
import base64
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from openai import OpenAI
from google import genai
from google.genai import types
from dotenv import load_dotenv
from tqdm import tqdm
import concurrent.futures
from error_logger import ErrorLogger
from topics import topic_dict_small, topic_dict_medium, topic_dict_max


# Create a global Gemini client to reuse
client = None

def configure():
    load_dotenv()

def is_valid_website(url, error_logger=None):
    """Check if the website responds successfully."""
    try:
        response = requests.get(url, timeout=10)
        return response.status_code == 200
    except requests.RequestException as e:
        if error_logger:
            error_logger.log_error("connection", url, f"Connection error: {e}")
        return False

def extract_text(url, error_logger=None):
    """Extracts text content from a website."""
    try:
        response = requests.get(url, timeout=10)
        if not response.encoding:
            response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract text from common tags
        texts = []
        for tag in soup.find_all(['p', 'span', 'h1', 'h2', 'h3', 'h4']):
            texts.append(tag.get_text(separator=' ', strip=True))
        combined_text = ' '.join(texts)
        if combined_text:
            return combined_text[:40000]

        # Fallback: extract from the entire body
        if soup.body:
            text = soup.body.get_text(separator=' ', strip=True)
            return text[:40000]
    except requests.RequestException as e:
        if error_logger:
            error_logger.log_error("parsing", url, f"Content extraction error: {e}")
        return None
    except Exception as e:
        if error_logger:
            error_logger.log_error("parsing", url, f"HTML parsing error: {e}")
        return None
    return None

def initialize_client():
    global client
    if client is None:
        client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))
    return client

def classify_website(content, topic, url=None, error_logger=None):
    """Uses the Gemini model to classify website content."""

    topics_dict = topic_dict_medium

    if topic not in topics_dict:
        if error_logger and url:
            error_logger.log_error("configuration", url, f"Unknown topic: {topic}")
        return 'u'  # Default to 'unrelated'

    prompt = f"""
    You are a specialized content classifier analyzing website content for sensitive or restricted topics.

    CLASSIFICATION TASK:
    Determine if the website content relates to: {topics_dict.get(topic)}

    INSTRUCTIONS:
    - Analyze the entire content including titles, headings, links, text, and metadata
    - Pay special attention to both explicit mentions and implicit references
    - Consider both English and Chinese language content (including Simplified and Traditional Chinese)
    - Look for cultural-specific terms and euphemisms commonly used in Chinese websites
    - Evaluate images based on their descriptions or surrounding context if available

    RESPONSE FORMAT:
    Reply with EXACTLY ONE character:
    - "h" if the content IS related to the topic
    - "u" if the content is NOT related to the topic

    WEBSITE CONTENT:
    {content}
    """

    client = initialize_client()
    model = "gemini-2.0-flash"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        temperature=0.1,
        max_output_tokens=1,
        response_mime_type="text/plain",
    )

    try:
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            result = chunk.text.strip().lower()
            if result and result[0] in ['h', 'u', 'i', 'p']:
                return result[0]
    except Exception as e:
        if error_logger and url:
            error_logger.log_error("api", url, f"Gemini API error: {e}")
        return 'u'  # Default to 'unrelated' in case of an error

    return 'u'

def process_url(url, topic, error_logger=None):
    """Process a single URL and return the result."""
    # Ensure the URL has a valid scheme
    parsed_url = urlparse(url)
    if not parsed_url.scheme:
        url = f"http://{url}"
    
    try:
        if not is_valid_website(url, error_logger):
            return url, 'i'
        else:
            content = extract_text(url, error_logger)
            if content:
                label = classify_website(content, topic, url, error_logger)
            else:
                label = 'i'
        return url, label
    except Exception as e:
        if error_logger:
            error_logger.log_error("processing", url, f"Unexpected error: {e}")
        return url, 'i'

def process_file(input_file, max_workers=10):
    """
    Processes an input TXT file where each line is a URL.
    Uses ThreadPoolExecutor for parallel processing.
    """
    # Derive topic from the input file name
    topic = os.path.splitext(os.path.basename(input_file))[0]
    
    # Initialize error logger
    error_logger = ErrorLogger(input_file)
    
    # Read URLs from file
    with open(input_file, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()]
    
    results = []
    # Use a ThreadPoolExecutor for parallel processing
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks and create a mapping of futures to URLs
        future_to_url = {executor.submit(process_url, url, topic, error_logger): url for url in urls}
        
        # Process results as they complete
        for future in tqdm(
            concurrent.futures.as_completed(future_to_url),
            total=len(urls),
            desc="Processing URLs",
            unit="url"
        ):
            url = future_to_url[future]
            try:
                result = future.result(timeout=60)
                results.append(result)
            except concurrent.futures.TimeoutError:
                error_logger.log_error("timeout", url, "Task timed out")
                results.append((url, 'i'))
            except Exception as e:
                error_logger.log_error("executor", url, f"Task execution error: {e}")
                results.append((url, 'i'))
    
    # Write results to an output file
    output_file = os.path.splitext(input_file)[0] + "_labeled.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        for url, label in results:
            f.write(f"{url} {label}\n")
    print(f"Results written to {output_file}")
    
    # Write error summary
    error_logger.write_log()

if __name__ == '__main__':
    configure()
    if len(sys.argv) < 2:
        print("Usage: python script.py <input_file.txt> [max_workers]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    max_workers = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    process_file(input_file, max_workers)
