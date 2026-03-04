import csv
import os
from datetime import datetime
from typing import Optional, List, Dict

# Constants for file paths
DATA_DIR = "monitor_data"
CHANNELS_FILE = os.path.join(DATA_DIR, "channels.csv")
PROCESSED_MESSAGES_FILE = os.path.join(DATA_DIR, "processed_messages.csv")
NOTIFICATIONS_FILE = os.path.join(DATA_DIR, "notifications.csv")

def initialize_storage():
    """
    Ensure the data directory and CSV files exist with proper headers.
    """
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        
    _init_csv(CHANNELS_FILE, ["channel_id", "last_checked_timestamp"])
    _init_csv(PROCESSED_MESSAGES_FILE, ["message_ts", "channel_id", "processed_at"])
    _init_csv(NOTIFICATIONS_FILE, ["type", "content", "sent_at"])

def _init_csv(filepath: str, headers: List[str]):
    """Helper to initialize a CSV with headers if it doesn't exist."""
    if not os.path.exists(filepath):
        with open(filepath, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)

def get_last_checked(channel_id: str) -> float:
    """
    Retrieve the last checked timestamp for a given channel.
    Returns 0.0 if not found.
    """
    try:
        with open(CHANNELS_FILE, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["channel_id"] == channel_id:
                    return float(row["last_checked_timestamp"])
    except (FileNotFoundError, ValueError):
        return 0.0
    return 0.0

def update_last_checked(channel_id: str, timestamp: float):
    """
    Update or insert the last checked timestamp for a channel.
    """
    rows = []
    updated = False
    
    # Read existing data
    if os.path.exists(CHANNELS_FILE):
        with open(CHANNELS_FILE, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or ["channel_id", "last_checked_timestamp"]
            for row in reader:
                if row["channel_id"] == channel_id:
                    row["last_checked_timestamp"] = str(timestamp)
                    updated = True
                rows.append(row)
    else:
        fieldnames = ["channel_id", "last_checked_timestamp"]
        
    # Append new record if not found
    if not updated:
        rows.append({"channel_id": channel_id, "last_checked_timestamp": str(timestamp)})
        
    # Write back all data
    with open(CHANNELS_FILE, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def is_message_processed(message_ts: str) -> bool:
    """
    Check if a message has already been processed.
    """
    if not os.path.exists(PROCESSED_MESSAGES_FILE):
        return False
        
    try:
        with open(PROCESSED_MESSAGES_FILE, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["message_ts"] == message_ts:
                    return True
    except FileNotFoundError:
        return False
    return False

def mark_message_processed(message_ts: str, channel_id: str):
    """
    Mark a message as processed. Avoids duplicate entries.
    """
    if is_message_processed(message_ts):
        return

    with open(PROCESSED_MESSAGES_FILE, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["message_ts", "channel_id", "processed_at"])
        # If file is empty (just created but header missing somehow), write header
        if f.tell() == 0:
            writer.writeheader()
            
        writer.writerow({
            "message_ts": message_ts,
            "channel_id": channel_id,
            "processed_at": datetime.utcnow().isoformat()
        })

def log_notification(notif_type: str, content: str):
    """
    Log a notification to the CSV file.
    """
    with open(NOTIFICATIONS_FILE, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["type", "content", "sent_at"])
        if f.tell() == 0:
            writer.writeheader()
            
        writer.writerow({
            "type": notif_type,
            "content": content,
            "sent_at": datetime.utcnow().isoformat()
        })
