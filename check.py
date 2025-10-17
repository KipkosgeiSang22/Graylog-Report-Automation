import asyncio
import aiohttp
import pandas as pd
import re
import json
from datetime import datetime
import pytz

copyright = "© 2025 Joshua"

ENCODED_AUTH_STRING = '{your base64 authentication code}'
AUTH = f'Basic {ENCODED_AUTH_STRING}'

HEADERS = {
    'Authorization': AUTH,
    'X-Requested-By': 'export-script',
    'Accept': 'application/json'
}

MAX_ROWS = 500
MAX_SHEET_NAME_LENGTH = 31

REQUIRED_FIELDS = [
    "msg", "user_name", "timestamp", "utmaction", "src_country", 
    "SubjectUserName", "IpAddress", "user", "IP", "IPV4",
    "User", "ClientAddress",
    "AccountName", "TargetUserName",
    "username", "ImagePath", "ServiceName", "ParentImage",
    "OriginalFileName", "ParentUser", "Image", "src_ip",
    "PasswordLastSet", "Timestamp", "AccountName", "AccountExpires", "dst_ip",
    "url", "destination_host_name", "destination_host_ip"
]

def convert_utc_to_local(utc_timestamp, local_tz_str='Africa/Nairobi'):
    """Convert UTC timestamp to local timezone and format it."""
    try:
        utc_time = datetime.fromisoformat(utc_timestamp.replace("Z", "+00:00"))
        local_tz = pytz.timezone(local_tz_str)
        local_time = utc_time.astimezone(local_tz)
        return local_time.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        print(f"Error converting timestamp: {e}")
        return utc_timestamp  # Return original if there's an error

def correlate_events(messages):
    """Correlate events by grouping based on all fields and combining timestamps."""
    df = pd.DataFrame(messages)

    if 'Date & Time' not in df.columns:
        raise ValueError("Messages must contain 'Date & Time' column.")

    fields_to_check = df.columns[df.columns != 'Date & Time'].tolist()
    df['group_key'] = df[fields_to_check].astype(str).agg(' | '.join, axis=1)

    grouped = df.groupby('group_key', as_index=False).agg({
        'Date & Time': lambda x: ' - '.join(sorted(set(x.dropna().astype(str)))),  
        **{field: 'first' for field in fields_to_check}  
    })

    grouped = grouped.drop(columns=['group_key'])
    return grouped

def extract_host_and_ip(collector_node_id):
    """Extract destination host name and IP from collector_node_id."""
    if not collector_node_id:
        return None, None
    
    # Use regex to find the IP address in the collector_node_id
    ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', collector_node_id)
    ip_address = ip_match.group(0) if ip_match else None
    
    # Extract the host name by removing the IP address and surrounding whitespace
    host_name = re.sub(r'\s*-\s*\d+\.\d+\.\d+\.\d+', '', collector_node_id).strip()

    return host_name, ip_address

def sanitize_value(value):
    """Recursively sanitizes a value, list, or dictionary."""
    if isinstance(value, dict):
        return {k: sanitize_value(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [sanitize_value(v) for v in value]
    elif isinstance(value, str):
        cleaned_str = re.sub(r'[\x00-\x1F]', '', value)
        cleaned_str = re.sub(r'[^\x00-\x7F]+', '', cleaned_str)
        return cleaned_str
    else:
        return value

def sanitize_sheet_name(sheet_name):
    """Sanitize the sheet name to remove invalid characters for Excel."""
    invalid_chars = r'[\\/*?:"<>|]'
    sanitized_name = re.sub(invalid_chars, '', sheet_name)  
    return sanitized_name[:MAX_SHEET_NAME_LENGTH]  

async def fetch_data(session, base_url, query, range_value):
    """Fetch data for a specific query."""
    try:
        async with session.get(
            f"{base_url}/api/search/universal/relative",
            params={"query": query, "range": range_value, "limit": MAX_ROWS, "fields": "*"},
            headers=HEADERS,
            timeout=20
        ) as response:
            response.raise_for_status()
            return await response.json()
    except Exception as e:
        print(f"Failed to fetch data: {e}")
        return None

async def process_client(client_name, data):
    """Process a single client's queries sequentially."""
    print(f"Processing client: {client_name}")
    base_url = data['base_url'].rstrip('/')  
    queries = data["queries"]  

    range_value = data.get('range_value', '300')

    with pd.ExcelWriter(f"{client_name}.xlsx", engine='openpyxl') as writer:
        async with aiohttp.ClientSession() as session:
            for widget_title, query in queries.items():
                print(f"Processing query for widget: {widget_title}")

                safe_sheet_name = sanitize_sheet_name(widget_title)

                search = await fetch_data(session, base_url, query, range_value)

                if search is None or "messages" not in search:
                    print(f"No messages found for widget '{widget_title}'. Skipping this sheet.")
                    continue

                messages_raw = search.get("messages", [])
                messages = []
                for msg_item in messages_raw:
                    message_data = msg_item.get("message", {})
                    if 'timestamp' in message_data:
                        message_data['timestamp'] = convert_utc_to_local(message_data['timestamp'])
                    sanitized_message = sanitize_value(message_data)

                    # Extract host name and IP after sanitizing the message
                    destination_host_name, destination_host_ip = extract_host_and_ip(sanitized_message.get('collector_node_id'))

                    # Filter only the required fields
                    filtered_message = {field: sanitized_message.get(field) for field in REQUIRED_FIELDS if field in sanitized_message}
                    if 'timestamp' in filtered_message:
                        filtered_message['Date & Time'] = filtered_message.pop('timestamp')

                    if destination_host_name:
                        filtered_message["destination_host_name"] = destination_host_name
                    if destination_host_ip:
                        filtered_message["destination_host_ip"] = destination_host_ip
                        
                    if filtered_message:
                        messages.append(filtered_message)

                if not messages:
                    print(f"No messages found for widget '{widget_title}'. Skipping this sheet.")
                    continue

                correlated_messages = correlate_events(messages)

                if correlated_messages.empty:
                    print(f"No correlated messages found for widget '{widget_title}'. Skipping this sheet.")
                    continue

                df = pd.DataFrame(correlated_messages)
                df.to_excel(writer, sheet_name=safe_sheet_name, index=False)

    print(f"Export complete for client: {client_name}")
async def main():
    with open('config.json', 'r') as f:
        clients_data = json.load(f)

    time_range = clients_data.get('time_range', {})
    range_value = time_range.get('range', '300')  # fallback to 300 seconds if missing

    tasks = []
    for client_name, data in clients_data['clients'].items():
        data['range_value'] = range_value  # inject into each client's data
        tasks.append(process_client(client_name, data))

    await asyncio.gather(*tasks)
if __name__ == "__main__":
    asyncio.run(main())