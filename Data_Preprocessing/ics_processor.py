import sys
import os

print("PYTHONPATH:", sys.path)
print("Current Working Directory:", os.getcwd())

import sys
if 'enum' in sys.modules:
    del sys.modules['enum']

# Now import your custom enum
from custom_calendar import IntEnum, global_enum


import csv
from icalendar import Calendar
import pandas as pd
from datetime import datetime
import os
import io
import logging
import calendar  # Import the built-in calendar module for standard functionality
from custom_calendar import Month, Day  # Import custom enums or classes from custom_calendar
#from custom_calendar import global_enum, IntEnum, Month, Day

# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

input_folder = 'input/'  # Folder for input HTML files
output_folder = 'processed/'  # Folder for output CSV files

def log_exception(step, e):
    logger.error(f"Error during {step}: {str(e)}", exc_info=True)

# Parse the ICS file and append events to a DataFrame
def parse_ics_to_df(s3, bucket_name, file_key, name, email):
    events = []

    try:
        logger.info(f"Downloading file from s3://{bucket_name}/{file_key}")

        # Download the .ics file from S3
        response = s3.get_object(Bucket=bucket_name, Key=file_key)
        ics_content = response['Body'].read().decode('utf-8')
        
        logger.info(f"Downloaded file size: {len(ics_content)} bytes")

        # Parse the .ics file
        calendar_data = Calendar.from_ical(ics_content)  # Avoid overwriting built-in calendar module

        # Extract events
        for component in calendar_data.walk():
            if component.name == "VEVENT":
                try:
                    event_name = component.get('summary', 'No Title')
                    start_date = component.get('dtstart').dt if component.get('dtstart') else None
                    end_date = component.get('dtend').dt if component.get('dtend') else None

                    # Convert timezone-aware dates to naive
                    if start_date and hasattr(start_date, 'tzinfo') and start_date.tzinfo is not None:
                        start_date = start_date.replace(tzinfo=None)
                    if end_date and hasattr(end_date, 'tzinfo') and end_date.tzinfo is not None:
                        end_date = end_date.replace(tzinfo=None)

                    description = component.get('description', 'No Description')
                    location = component.get('location', 'No Location')

                    # Use custom Month and Day enums if needed
                    # Example: Handling custom logic with enums
                    if start_date:
                        event_month = Month(start_date.month).name  # Custom Month enum
                    else:
                        event_month = 'Unknown'

                    events.append({
                        'Name': name,
                        'Email': email,
                        'Event Name': event_name,
                        'Start Date': start_date,
                        'End Date': end_date,
                        'Month': event_month,  # Include month from custom_calendar
                        'Description': description,
                        'Location': location
                    })
                except Exception as e:
                    log_exception("parsing event", e)
    except Exception as e:
        log_exception("reading file from S3", e)
        return pd.DataFrame()
    
    logger.info(f"Number of events processed: {len(events)}")

    return pd.DataFrame(events)

def save_df_to_s3(s3, df, bucket_name, output_key):
    try:
        # Log DataFrame content for debugging
        logger.info(f"Saving DataFrame to S3: {df.head()}")

        # Ensure dates are parsed
        df['Start Date'] = pd.to_datetime(df['Start Date'], errors='coerce')
        df['End Date'] = pd.to_datetime(df['End Date'], errors='coerce')

        # Save DataFrame to a buffer
        buffer = io.StringIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)

        # Log upload details
        logger.info(f"Uploading to s3://{bucket_name}/{output_key}")

        # Upload to S3
        s3.put_object(Bucket=bucket_name, Key=output_key, Body=buffer.getvalue())
        logger.info(f"CSV file successfully saved to s3://{bucket_name}/{output_key}")
    except Exception as e:
        log_exception("saving CSV to S3", e)

def process_ics(s3, bucket_name, file_key, name, email):
    logger.info("Starting the process_ics function")
    try:
        # Decode the file key
        logger.info(f"Received file key: {file_key}")
        import urllib.parse
        file_key = urllib.parse.unquote(file_key)
        logger.info(f"Decoded file key: {file_key}")

        # Generate the output key
        output_key = os.path.join(output_folder, os.path.basename(file_key).replace('.ics', '.csv'))
        logger.info(f"Output key generated: {output_key}")

        # Parse the ICS file and create a DataFrame
        preprocessed_data = parse_ics_to_df(s3, bucket_name, file_key, name, email)
        logger.info(f"DataFrame created with {preprocessed_data.shape[0]} rows")

        if not preprocessed_data.empty:
            # Save the DataFrame to S3
            save_df_to_s3(s3, preprocessed_data, bucket_name, output_key)
            logger.info(f"File successfully processed and uploaded to {output_key}")
        else:
            logger.info("No events found or an error occurred.")
    except Exception as e:
        log_exception("processing ICS file", e)
    
