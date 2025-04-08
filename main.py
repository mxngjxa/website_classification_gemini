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
from collections import defaultdict
import time
from datetime import datetime

def configure():
    load_dotenv()

def is_valid_website(url):
    """Check if the website responds successfully."""
    try:
        response = requests.get(url, timeout=10)
        return response.status_code == 200
    except requests.RequestException as e:
        return False, str(e)
    return True, None

def extract_text(url):
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
            return combined_text[:20000], None

        # Fallback: extract from the entire body
        if soup.body:
            text = soup.body.get_text(separator=' ', strip=True)
            return text[:20000], None
        return None, "No content found in page body"
    except requests.RequestException as e:
        return None, str(e)
    except Exception as e:
        return None, f"Text extraction error: {str(e)}"

# Create a global Gemini client to reuse
client = None

def initialize_client():
    global client
    if client is None:
        client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))
    return client

def classify_website(content, topic):
    """Uses the Gemini model to classify website content."""
    topic_dict = {
        'drugs': 'DRUGS: including illegal drugs, drug abuse, recreational and psychedelic drugs, and related topics.',
        'tobacco': 'TOBACCO: Include vaping and traditional tobacco products, including stores and advocacy.',
        'violence': 'WEAPONS: Cover BB guns, airsoft, and real firearms.'
    }

    if topic not in topic_dict:
        return 'u', f"Error: Topic '{topic}' is not defined in topic_dict"

    prompt = f"""
            You are a website content classifier that analyzes HTML/text content and determines if it's related to a specific topic.

            RULES:
            - Respond with EXACTLY ONE character:
            - "h" if the website IS related to the topic
            - "u" if the website is NOT related to the topic
            - Do not include any explanations, just the single character response
            - Analyze content in either English or Chinese languages
            - Consider page titles, headings, keywords, meta description, and body text

            TOPIC: {topic_dict.get(topic)}

            WEBSITE CONTENT:
            {content}
            """

    client = initialize_client()
    model = "gemini-2.0-flash-lite"
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
            if result and result[0] in ['h', 'u', 'i']:
                return result[0], None
    except Exception as e:
        return 'u', f"API error: {str(e)}"

    return 'u', "No valid response from API"

def process_url(url, topic):
    """Process a single URL and return the result, along with any error information."""
    error_info = None
    
    # Ensure the URL has a valid scheme
    parsed_url = urlparse(url)
    if not parsed_url.scheme:
        url = f"http://{url}"
    
    # Check if website is valid
    is_valid, validation_error = is_valid_website(url)
    if not is_valid:
        return url, 'i', {"stage": "validation", "error": validation_error, "url": url}
    
    # Extract text from website
    content, extraction_error = extract_text(url)
    if extraction_error:
        return url, 'i', {"stage": "extraction", "error": extraction_error, "url": url}
    
    if not content:
        return url, 'i', {"stage": "extraction", "error": "No content extracted", "url": url}
    
    # Classify the website
    label, classification_error = classify_website(content, topic)
    if classification_error:
        return url, label, {"stage": "classification", "error": classification_error, "url": url}
    
    return url, label, None

def process_file(input_file, max_workers=10):
    """
    Processes an input TXT file where each line is a URL.
    Uses ThreadPoolExecutor for parallel processing and collects error information.
    """
    # Derive topic from the input file name
    topic = os.path.splitext(os.path.basename(input_file))[0]
    
    # Read URLs from file
    with open(input_file, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()]
    
    results = []
    all_errors = []
    start_time = time.time()
    
    # Use a ThreadPoolExecutor for parallel processing
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks and create a mapping of futures to URLs
        future_to_url = {executor.submit(process_url, url, topic): url for url in urls}
        
        # Process results as they complete
        for future in tqdm(
            concurrent.futures.as_completed(future_to_url), 
            total=len(urls), 
            desc="Processing URLs"
        ):
            url = future_to_url[future]
            try:
                url, label, error_info = future.result()
                results.append((url, label))
                if error_info:
                    all_errors.append(error_info)
            except Exception as e:
                results.append((url, 'i'))
                all_errors.append({
                    "stage": "processing", 
                    "error": str(e), 
                    "url": url
                })
    
    # Calculate processing statistics
    end_time = time.time()
    processing_time = end_time - start_time
    urls_processed = len(urls)
    error_count = len(all_errors)
    success_rate = ((urls_processed - error_count) / urls_processed) * 100 if urls_processed > 0 else 0
    
    # Write results to an output file
    output_file = os.path.splitext(input_file)[0] + "_labeled.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        for url, label in results:
            f.write(f"{url} {label}\n")
    
    # Generate and write error summary
    error_log_file = os.path.splitext(input_file)[0] + "_error_messages.log"
    write_error_summary(error_log_file, all_errors, {
        "processing_time": processing_time,
        "urls_processed": urls_processed,
        "error_count": error_count,
        "success_rate": success_rate,
        "max_workers": max_workers
    })
    
    print(f"Results written to {output_file}")
    print(f"Error summary written to {error_log_file}")
    print(f"Processing completed in {processing_time:.2f} seconds with {success_rate:.2f}% success rate")

def write_error_summary(error_log_file, all_errors, stats):
    """Generate a comprehensive error summary and write it to a log file."""
    # Group errors by type and stage
    errors_by_stage = defaultdict(list)
    error_types_count = defaultdict(int)
    
    for error in all_errors:
        stage = error.get("stage", "unknown")
        errors_by_stage[stage].append(error)
        
        # Extract the first part of the error message for grouping similar errors
        error_msg = error.get("error", "unknown error")
        error_type = error_msg.split(":")[0] if ":" in error_msg else error_msg
        error_types_count[f"{stage} - {error_type}"] += 1
    
    # Write the error summary to file
    with open(error_log_file, 'w', encoding='utf-8') as f:
        # Write header with timestamp and summary statistics
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"=== ERROR SUMMARY REPORT ===\n")
        f.write(f"Generated: {timestamp}\n\n")
        
        # Write processing statistics
        f.write("--- PROCESSING STATISTICS ---\n")
        f.write(f"Total URLs processed: {stats['urls_processed']}\n")
        f.write(f"Total errors encountered: {stats['error_count']}\n")
        f.write(f"Success rate: {stats['success_rate']:.2f}%\n")
        f.write(f"Processing time: {stats['processing_time']:.2f} seconds\n")
        f.write(f"Parallel workers: {stats['max_workers']}\n\n")
        
        # Write error type summary (grouped by frequency)
        f.write("--- ERROR TYPE SUMMARY ---\n")
        for error_type, count in sorted(error_types_count.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / stats['error_count']) * 100 if stats['error_count'] > 0 else 0
            f.write(f"{error_type}: {count} occurrences ({percentage:.2f}%)\n")
        f.write("\n")
        
        # Write detailed errors by processing stage
        f.write("--- DETAILED ERRORS BY STAGE ---\n")
        for stage, errors in errors_by_stage.items():
            f.write(f"\n== {stage.upper()} STAGE ERRORS ({len(errors)} errors) ==\n")
            for i, error in enumerate(errors[:20], 1):  # Limit to first 20 errors per stage
                f.write(f"{i}. URL: {error.get('url', 'unknown')}\n")
                f.write(f"   Error: {error.get('error', 'unknown error')}\n")
            
            # If there are more errors, just note the count
            if len(errors) > 20:
                f.write(f"... and {len(errors) - 20} more errors in this stage\n")
        
        # Write individual error details in a log format
        f.write("\n\n--- FULL ERROR LOG ---\n")
        for i, error in enumerate(all_errors, 1):
            f.write(f"ERROR #{i}\n")
            f.write(f"URL: {error.get('url', 'unknown')}\n")
            f.write(f"Stage: {error.get('stage', 'unknown')}\n")
            f.write(f"Error: {error.get('error', 'unknown error')}\n")
            f.write("-" * 50 + "\n")

if __name__ == '__main__':
    configure()
    if len(sys.argv) < 2:
        print("Usage: python script.py <input_file.txt> [max_workers]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    max_workers = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    process_file(input_file, max_workers)
