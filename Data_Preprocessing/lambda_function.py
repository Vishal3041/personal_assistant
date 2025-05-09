import sys
sys.path.insert(0, '/opt/python')


import csv
from icalendar import Calendar
import pandas as pd
from datetime import datetime
import os
import io
import logging
import calendar  # Import the built-in calendar module for standard functionality
from custom_calendar import Month, Day  # Import custom enums or classes from custom_calendar
from custom_calendar import global_enum, IntEnum, Month, Day

import boto3
import os
from datetime import datetime

# Instantiate an S3 client
s3 = boto3.client("s3")

# Define constants
PROCESSED_TAG_KEY = "Processed"
PROCESSED_TAG_VALUE = "True"

def lambda_handler(event, context):
    results = []

    # Iterate through the event records (files added to S3)
    for record in event.get("Records", []):
        bucket_name = record["s3"]["bucket"]["name"]
        s3_key = record["s3"]["object"]["key"]

        try:
            # Check if the file is already processed
            if is_file_processed(s3, bucket_name, s3_key):
                print(f"Skipping already processed file: {s3_key}")
                continue

            # Get the file details
            file_name = os.path.basename(s3_key)
            file_extension = os.path.splitext(file_name)[1].lower()

            # Process the file based on its extension
            if file_extension == ".html":
                from html_processor import process_html
                result = process_html(s3, bucket_name, s3_key)
            elif file_extension == ".json":
                from json_processor import process_json
                result = process_json(s3, bucket_name, s3_key)
            elif file_extension == ".ics":
                from ics_processor import process_ics
                result = process_ics(s3, bucket_name, s3_key, "abcd", "example@gmail.com")
            else:
                result = f"Unsupported file type: {file_extension}"

            # Mark the file as processed
            mark_file_as_processed(s3, bucket_name, s3_key)

            # Append the result
            results.append({
                "file": s3_key,
                "result": result
            })

        except Exception as e:
            print(f"Error processing file {s3_key}: {e}")
            results.append({
                "file": s3_key,
                "result": f"Error: {e}"
            })

    # Return results or a no-new-files message
    if not results:
        return {
            "statusCode": 200,
            "body": "No new files to process."
        }

    return {
        "statusCode": 200,
        "body": results
    }

def is_file_processed(s3, bucket_name, file_key):
    """Check if the file is already processed using S3 object tags."""
    try:
        response = s3.get_object_tagging(Bucket=bucket_name, Key=file_key)
        tags = {tag['Key']: tag['Value'] for tag in response.get('TagSet', [])}
        return tags.get(PROCESSED_TAG_KEY) == PROCESSED_TAG_VALUE
    except Exception as e:
        print(f"Error checking tags for file {file_key}: {e}")
        return False

def mark_file_as_processed(s3, bucket_name, file_key):
    """Mark the file as processed by adding a tag."""
    try:
        s3.put_object_tagging(
            Bucket=bucket_name,
            Key=file_key,
            Tagging={'TagSet': [{'Key': PROCESSED_TAG_KEY, 'Value': PROCESSED_TAG_VALUE}]}
        )
        print(f"File {file_key} marked as processed.")
    except Exception as e:
        print(f"Error marking file as processed: {e}")
