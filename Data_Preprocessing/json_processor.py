import json
import boto3
from urllib.parse import urlparse
from datetime import datetime
from collections import defaultdict
import io

bucket_name = '298a'  # Replace with your S3 bucket name
input_folder = 'input/'  # Folder for input HTML files
output_folder = 'processed/'  # Folder for output CSV files

# Function to save JSON data to S3
def save_json_to_s3(s3, bucket_name, file_key, data):
    json_content = json.dumps(data, ensure_ascii=False, indent=4)
    s3.put_object(Bucket=bucket_name, Key=file_key, Body=json_content)
    print(f"Processed JSON saved to S3: {file_key}")

# Preprocessing function
def process_json(s3, bucket_name, file_key):
    response = s3.get_object(Bucket=bucket_name, Key=file_key)
    json_content = response['Body'].read().decode('utf-8')
    data = json.loads(json_content)
    # Extract browser history
    browser_history = data.get("Browser History", [])
    
    # Preprocess the data
    processed_data = []
    for entry in browser_history:
        title = entry.get("title", "").strip()
        url = entry.get("url", "").strip()
        time_usec = entry.get("time_usec", 0)
        
        # Convert microseconds to datetime
        timestamp = datetime.utcfromtimestamp(time_usec / 1e6).strftime('%Y-%m-%d %H:%M:%S')
        
        # Extract domain from URL
        domain = urlparse(url).netloc
        
        # Append processed data
        processed_data.append({
            "Title": title,
            "URL": url,
            "Timestamp": timestamp,
            "Domain": domain
        })
    
    # Remove duplicates based on Title and URL
    unique_data = {frozenset(item.items()): item for item in processed_data}.values()

    output_key = file_key.replace(input_folder, output_folder)

    # Save processed data to S3
    save_json_to_s3(s3, bucket_name, output_key, processed_data)
    return list(unique_data)