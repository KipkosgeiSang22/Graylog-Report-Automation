import os
from dotenv import load_dotenv
import asyncio
import aiohttp
import pandas as pd
import re
import json
from datetime import datetime
import pytz
import ssl
from aiohttp import TCPConnector
from openpyxl.styles import Alignment, PatternFill, Border, Side
from concurrent.futures import ThreadPoolExecutor


copyright = "© 2025 Joshua"

ENCODED_AUTH_STRING = os.environ.get('GRAYLOG_AUTH_TOKEN')
if not ENCODED_AUTH_STRING:
    raise EnvironmentError("GRAYLOG_AUTH_TOKEN is not set. Check your .env file.")
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
    "SubjectUserName", "IpAddress", "user", "IP", "IPV4", "Ipaddress", "caller_computer_name","client",
    "User", "ClientAddress", "ClientName", "UserId", "ClientIP", "dvc", "ActivityTitle", "Action", "UserName",
    "AccountName", "TargetUserName", "remip", "srcip", "dstip", "ip_address", "users", "app", "commandline",
    "username", "ImagePath", "ServiceName", "ParentImage", "config", "configuration","CommandLine",
    "OriginalFileName", "ParentUser", "Image", "src_ip", "NewTargetUserName", "OldTargetUserName",
    "PasswordLastSet", "Timestamp", "AccountExpires", "dst_ip", "ui", "hdn", "hip", "p1", "p3", "rhost",
    "url", "destination_host", "destination_host_ip"
]

QUERY_FIELDS_TO_DROP = {
    "Successful RDP Logon (Different": ["AccountName", "IP"],
    "Interactive Logon - LogonType 2": ["IpAddress", "SubjectUserName", "IPV4", "IP"],
    "Successful Remote Interactive": ["SubjectUserName"],
    "Successful SSL VPN Successful Login (user, remip, msg , timestamp)": ["msg"],
    "Account Lockouts":["SubjectUserName"],
}


def convert_utc_to_local(utc_timestamp, local_tz_str='Africa/Nairobi'):
    """
    Converts a UTC timestamp string to local time, handling cases where 
    the API is inconsistent with TZ info.
    """
    try:
        # Replace Z/+00:00 just to standardize the input string for parsing.
        dt_obj = datetime.fromisoformat(utc_timestamp.replace("Z", "+00:00"))
        
        #  Ensure the time is aware. If it's naive, assume it's UTC.
        # This prevents the 'Not naive datetime' error while fixing the double shift.
        if dt_obj.tzinfo is None:
            # If the object is naive, explicitly set it to be UTC.
            utc_time = pytz.utc.localize(dt_obj)
        else:
            utc_time = dt_obj.astimezone(pytz.utc)
        
        # 3. Convert from the confirmed UTC time to the target local timezone.
        local_tz = pytz.timezone(local_tz_str)
        local_time = utc_time.astimezone(local_tz)
        
        return local_time.strftime('%Y-%m-%d %H:%M') 
        
    except Exception as e:
        print(f"Error converting UTC timestamp: {e}") 
        return utc_timestamp
def convert_local_time_to_utc(local_time_str, local_tz_str):
    """Converts a local time string to a standardized UTC ISO string."""
    try:
        local_tz = pytz.timezone(local_tz_str)
        

        if 'T' in local_time_str and '.' in local_time_str:
             format_str = "%Y-%m-%dT%H:%M:%S.%f"
        elif 'T' in local_time_str:
             format_str = "%Y-%m-%dT%H:%M:%S"
        elif ' ' in local_time_str:
             format_str = "%Y-%m-%d %H:%M:%S"
        else:

            format_str = "%Y-%m-%d %H:%M:%S" 
            
        naive_dt = datetime.strptime(local_time_str, format_str)
        
        # 1. Localize the naive time using the specified local timezone
        local_dt = local_tz.localize(naive_dt)
        
        # 2. Convert to UTC
        utc_dt = local_dt.astimezone(pytz.utc)
        
        # Return ISO format, ensuring millisecond precision
        return utc_dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    except Exception as e:
         print(f"Error converting local time: {e}")
         return datetime.now(pytz.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def correlate_events(messages):
    df = pd.DataFrame(messages)
    if 'Date & Time' not in df.columns:
        raise ValueError("Messages must contain 'Date & Time' column.")

    fields_to_check = df.columns[df.columns != 'Date & Time'].tolist()
    df['group_key'] = df[fields_to_check].astype(str).agg(' | '.join, axis=1)

    grouped = df.groupby('group_key', as_index=False).agg({
        'Date & Time': lambda x: sorted(set(x.dropna().astype(str))),
        **{field: 'first' for field in fields_to_check}
    })

    def format_timestamps(x):
        if not x:
            return None
        if len(x) <= 3:
            return ' '.join(x)
        mid_index = len(x) // 2
        return f"{x[0]} {x[mid_index]} {x[-1]}"

    grouped['Date & Time'] = grouped['Date & Time'].apply(format_timestamps)
    return grouped.drop(columns=['group_key'])

def extract_host_and_ip(collector_node_id, ip_lookup):
    if not collector_node_id:
        return None, None
    
    ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', collector_node_id)
    ip_address = ip_match.group(0) if ip_match else None
    host_name = re.sub(r'\s*-\s*\d+\.\d+\.\d+\.\d+', '', collector_node_id).strip()

    if not ip_address and host_name in ip_lookup:
        ip_address = ip_lookup[host_name]

    return host_name, ip_address

def sanitize_value(value):
    if isinstance(value, dict):
        return {k: sanitize_value(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [sanitize_value(v) for v in value]
    elif isinstance(value, str):
        cleaned_str = re.sub(r'[\x00-\x1F]', '', value)
        cleaned_str = re.sub(r'[^\x00-\x7F]+', '', cleaned_str)
        return cleaned_str.strip()
    else:
        return value

def sanitize_sheet_name(sheet_name):
    # Invalid characters in Excel sheet names
    invalid_chars = r'[\\/*?:"<>|:\[\]]'
    sanitized_name = re.sub(invalid_chars, '', sheet_name)
    return sanitized_name[:MAX_SHEET_NAME_LENGTH] # Limit length

def write_to_excel(writer, sheet_name, df):
    if df.empty:
        print(f"Skipping empty DataFrame for sheet: {sheet_name}")
        return # Skip writing if the DataFrame is empty

    df.to_excel(writer, sheet_name=sheet_name, index=False)
    worksheet = writer.sheets[sheet_name]

    fixed_width = 20
    thin_border = Border(left=Side(style='thin'),
                         right=Side(style='thin'),
                         top=Side(style='thin'),
                         bottom=Side(style='thin'))

    for col in worksheet.columns:
        column = col[0].column_letter  
        worksheet.column_dimensions[column].width = fixed_width
        
        for cell in col:
            cell.alignment = Alignment(wrap_text=True)
            cell.border = thin_border  

    fill = PatternFill(start_color='9BC2E6', end_color='9BC2E6', fill_type='solid')
    for cell in worksheet[1]:
        cell.fill = fill

async def fetch_with_retries(session, url, params, headers, retries=3, delay=2):
    for attempt in range(retries):
        try:
            async with session.get(url, params=params, headers=headers, timeout=900) as response:
                response.raise_for_status() # Raise HTTPError for bad responses
                return await response.json() # Return the response JSON

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            if attempt < retries - 1:  # If this isn't the last attempt, wait and retry
                await asyncio.sleep(delay)
                continue  # Retry the request
            else:
                # Raise exception if max retries exceeded
                return {"error": str(e)}

async def fetch_data_batch(session, base_url, queries, start_time, end_time):
    try:
        tasks = []
        for query in queries:
            url = f"{base_url}/api/search/universal/absolute"
            params = {
                "query": query,
                "from": start_time,
                "to": end_time,
                "limit": MAX_ROWS,
                "fields": "*"
            }
            tasks.append(fetch_with_retries(session, url, params, HEADERS))

        # Await responses for all queries in the batch
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        results = []
        for response in responses:
            if isinstance(response, Exception):
                results.append({"error": str(response)})
            else:
                results.append(response)  # Already JSON if fetched successfully

        return results

    except Exception as e:
        print(f"Failed to fetch data for batch: {e}")
        return [{"error": str(e)}]

async def process_client(client_name, data, executor):
    print(f"Processing client: {client_name}")
    base_url = data['base_url'].rstrip('/')
    queries = data["queries"]
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    
    # --- NEW: Safe File Handling Logic ---
    base_filename = f"{client_name}.xlsx"
    filename = base_filename
    writer = None
    max_attempts = 5

    for i in range(max_attempts):
        try:
            # Attempt to create the ExcelWriter with the current filename
            writer = pd.ExcelWriter(filename, engine='openpyxl', mode="w")
            #print(f"Successfully opened file for writing: {filename}")
            break  # Success! Exit the loop

        except (PermissionError, IOError) as e:
            if i < max_attempts - 1:
                # File is locked or permission denied. Generate a new filename.
                print(f"Warning: File '{filename}' is locked/inaccessible ({e}). Retrying with alternate name.")
                filename = f"{client_name}({i + 1}).xlsx"
                await asyncio.sleep(1) # Wait briefly before next attempt
            else:
                # Max attempts failed, log and skip this client
                print(f"ERROR: Failed to open file after {max_attempts} attempts. Skipping client {client_name}.")
                return # Crucially, exit the coroutine if writer can't be created

    # If the loop finished without successfully creating a writer, exit
    if writer is None:
        return 
    # We now proceed with the successful 'writer' object using a try/finally
    try:
        error_messages = []
        found_event = False

        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        connector = TCPConnector(ssl=ssl_context)

        async with aiohttp.ClientSession(connector=connector) as session:
            batch_size = 7
            query_items = list(queries.items())
            query_batches = [query_items[i:i + batch_size] for i in range(0, len(query_items), batch_size)]

            for batch in query_batches:
                batch_queries = [q for _, q in batch]
                responses = await fetch_data_batch(session, base_url, batch_queries, start_time, end_time)

                for response, (query_name, _) in zip(responses, batch):
                    sheet_name = sanitize_sheet_name(query_name)

                    if "error" in response:
                        error_messages.append({"Widget": query_name, "Error": response["error"]})
                        continue

                    messages_raw = response.get("messages", [])
                    if not messages_raw:
                        print(f"No messages found for widget: {query_name}")
                        continue

                    found_event = True
                    messages = []
                    for msg_item in messages_raw:
                        message_data = msg_item.get("message", {})
                        if 'timestamp' in message_data:
                            message_data['timestamp'] = convert_utc_to_local(message_data['timestamp'])

                        sanitized_message = sanitize_value(message_data)
                        filtered_message = {field: sanitized_message.get(field) for field in REQUIRED_FIELDS if field in sanitized_message}

                        if 'timestamp' in filtered_message:
                            filtered_message['Date & Time'] = filtered_message.pop('timestamp')

                        # APPLY FIELD DROPPING LOGIC
                        if sheet_name in QUERY_FIELDS_TO_DROP:
                            fields_to_drop = QUERY_FIELDS_TO_DROP[sheet_name]
                            for field in fields_to_drop:
                                filtered_message.pop(field, None)
                        
                        # Process destination host and IP
                        destination_host_name, destination_host_ip = extract_host_and_ip(
                            sanitized_message.get('collector_node_id'), data.get('ip_lookup', {})
                        )
                        
                        if destination_host_name:
                            filtered_message["destination_host"] = destination_host_name
                        if destination_host_ip:
                            filtered_message["destination_host_ip"] = destination_host_ip

                        if filtered_message:
                            messages.append(filtered_message)

                    if not messages:
                        continue

                    correlated_messages = correlate_events(messages)

                    if correlated_messages.empty:
                        continue
                    
                    # Offload Excel write to thread pool
                    await asyncio.get_event_loop().run_in_executor(
                        executor, write_to_excel, writer, sheet_name, pd.DataFrame(correlated_messages)
                    )

        # Handle error messages
        if error_messages:
            error_df = pd.DataFrame(error_messages)
            await asyncio.get_event_loop().run_in_executor(executor, write_to_excel, writer, 'Error Log', error_df)

        # If no events were found for any queries, create a "No Information" sheet
        if not found_event:
            no_info_df = pd.DataFrame({"Message": ["No information was found."]})
            await asyncio.get_event_loop().run_in_executor(executor, write_to_excel, writer, 'No Information', no_info_df)

    finally:
        if writer is not None:

            await asyncio.get_event_loop().run_in_executor(executor, writer.close)
            
    print(f"Export complete for client: {client_name}")


async def main():
    with open('config.json', 'r') as f:
        clients_data = json.load(f)
    with open('time.json', 'r') as t:
        time = json.load(t)

    time_range = time.get('time_range', {})
    start_time_local = time_range.get('from')
    end_time_local = time_range.get('to')
    local_tz_str = time_range.get('timezone', 'UTC')

    start_time_utc = convert_local_time_to_utc(start_time_local, local_tz_str)
    end_time_utc = convert_local_time_to_utc(end_time_local, local_tz_str)

    tasks = []
    # Maximum 10 threads working on Excel I/O tasks
    with ThreadPoolExecutor(max_workers=10) as executor: 
        for client_name, data in clients_data['clients'].items():
            env_key = data.get('base_url_env')
            base_url = os.environ.get(env_key)
            if not base_url:
                raise EnvironmentError(f"'{env_key}' is not set in .env for client '{client_name}'.")
            data['base_url'] = base_url
            data['start_time'] = start_time_utc
            data['end_time'] = end_time_utc
            tasks.append(process_client(client_name, data, executor))

        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
