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

def configure():
    load_dotenv()

def is_valid_website(url):
    """Check if the website responds successfully."""
    try:
        response = requests.get(url, timeout=10)
        return response.status_code == 200
    except requests.RequestException as e:
        #print(f"Error validating URL {url}: {e}")
        return False

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
            return combined_text[:20000]

        # Fallback: extract from the entire body
        if soup.body:
            text = soup.body.get_text(separator=' ', strip=True)
            return text[:20000]
    except requests.RequestException:
        return None
    return None

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
        print(f"Error: Topic '{topic}' is not defined in topic_dict.")
        return 'u'  # Default to 'unrelated'

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
                return result[0]
    except Exception as e:
        print(f"Error calling Gemini model: {e}")
        return 'u'  # Default to 'unrelated' in case of an error

    return 'u'

def process_url(url, topic):
    """Process a single URL and return the result."""
    # Ensure the URL has a valid scheme
    parsed_url = urlparse(url)
    if not parsed_url.scheme:
        url = f"http://{url}"
    
    if not is_valid_website(url):
        return url, 'i'
    else:
        content = extract_text(url)
        if content:
            label = classify_website(content, topic)
        else:
            label = 'i'
    return url, label

def process_file(input_file, max_workers=10):
    """
    Processes an input TXT file where each line is a URL.
    Uses ThreadPoolExecutor for parallel processing.
    """
    # Derive topic from the input file name
    topic = os.path.splitext(os.path.basename(input_file))[0]
    
    # Read URLs from file
    with open(input_file, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()]
    
    results = []
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
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"Error processing {url}: {e}")
                results.append((url, 'i'))
    
    # Write results to an output file
    output_file = os.path.splitext(input_file)[0] + "_labeled.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        for url, label in results:
            f.write(f"{url} {label}\n")
    print(f"Results written to {output_file}")

if __name__ == '__main__':
    configure()
    if len(sys.argv) < 2:
        print("Usage: python script.py <input_file.txt> [max_workers]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    max_workers = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    process_file(input_file, max_workers)
