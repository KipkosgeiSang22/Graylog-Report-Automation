# 🛡️ Async Log Export and Correlation Script

This Python script automates the retrieval, sanitation, correlation, and export of log data from multiple clients via a Graylog-like REST API. It is built for security operations (SOC) and reporting, enabling the concurrent extraction of complex queries defined in configuration files and exporting the results into structured, formatted Excel reports.

## ✨ Features Overview

- **Asynchronous Data Retrieval**: Utilizes `asyncio` and `aiohttp` to perform high-speed, parallel log fetching across multiple API queries and client environments.
- **Event Correlation**: Groups identical log entries (based on non-timestamp fields) and merges their timestamps into a single representative range, drastically reducing data redundancy in reports.
- **Timezone Conversion**: Converts API-provided UTC timestamps to a user-defined local timezone (defaulting to Africa/Nairobi) for accurate reporting.
- **Robust Data Hygiene**: Implements strict sanitization to remove control characters, non-ASCII text, and filters logs to a standard set of required security-relevant fields (`REQUIRED_FIELDS`).
- **Formatted Excel Output**: Exports correlated data to a dedicated Excel file per client. Output includes custom styling, borders, and auto-sizing, and uses robust file handling to manage locking errors.
- **Threaded I/O Handling**: Uses a `ThreadPoolExecutor` to offload synchronous, blocking Excel writing operations from the main asyncio loop, maintaining high script responsiveness.

## ⚙️ Key Technologies

The project is built on Python's asynchronous ecosystem, enabling massive parallelism in I/O operations (network requests and file writes).

| Library       | Role in Project                                          | Description                                                                                     |
|---------------|---------------------------------------------------------|-------------------------------------------------------------------------------------------------|
| `asyncio`     | Event Loop Orchestration                                | Python's core library for concurrent code, managing and switching between tasks that are waiting for network I/O or other blocking operations. |
| `aiohttp`     | Asynchronous HTTP Requests                               | Performs non-blocking, concurrent GET requests to the API, allowing the script to fetch data from numerous sources simultaneously. |
| `pandas`      | Data Manipulation & Correlation                          | Used to transform raw JSON logs into structured DataFrames, perform `groupby()` aggregation for correlation, and manage the Excel export interface. |
| `openpyxl`    | Excel Writing Engine                                     | The backend utilized by `pandas.ExcelWriter` to apply detailed cell formatting, styling, and column configuration. |
| `pytz`        | Timezone Conversion                                      | Ensures accurate conversion of timestamps between UTC (from API) and the specified local timezone. |
| `re`          | Regular Expressions                                      | Used for tasks like extracting IP addresses from host strings and sanitizing values by removing invalid characters. |

## 🛠️ Setup and Execution

### Prerequisites

- Python 3.8+
- The required Python packages:
  
  ```bash
  pip install aiohttp pandas openpyxl pytz

## Configuration Files

The script relies on two JSON files for dynamic configuration:

### config.json
Defines the API base URL, search queries, and optional IP lookup tables for each client.

```json
{
    "clients": {
        "ClientA_Name": {
            "base_url": "https://graylog.example.com",
            "queries": {
                "Successful RDP Logon (Different": "action:rdp AND success:true",
                "Account Lockouts": "event_id:4740 AND result:locked"
            },
            "ip_lookup": {
                "host-server-01": "10.0.0.1" 
            }
        }
    }
}

time.json: Specifies the absolute time window and the local timezone.

json
{
    "time_range": {
        "from": "2025-01-01 00:00:00",
        "to": "2025-01-31 23:59:59",
        "timezone": "Africa/Nairobi"
    }
}

Authentication
The script uses HTTP Basic Authentication. The Base64-encoded credential string must be placed in the ENCODED_AUTH_STRING variable in the main script:

python
# In the Python script:
ENCODED_AUTH_STRING = 'UmVwb3J0Ok1QZHVzVHJQajFtRWFUUUV5YUtwdzlQUDZHTXJONA==' 
HEADERS = { 
    'Authorization': f'Basic {ENCODED_AUTH_STRING}', 
    # ... other headers
}

Run

Execution
Run the script from your terminal:

bash
python <script_filename>.py

Output: One Excel file (e.g., ClientA_Name.xlsx) will be generated for each client, containing a separate sheet for every query.

🧪 Core Logic & Functions
Data Pipeline Flow

## 🧪 Data Pipeline Flow

| Step       | Description                                                                                     |
|------------|-------------------------------------------------------------------------------------------------|
| Load       | `main()` reads `config.json` and `time.json`.                                                 |
| Convert    | Local time range is converted to UTC ISO format.                                              |
| Orchestrate| `asyncio.gather` launches multiple `process_client` coroutines concurrently.                   |
| Fetch (Async) | `fetch_data_batch` makes concurrent API calls for a client's queries.                      |
| Transform  | Logs are sanitized, fields are filtered to `REQUIRED_FIELDS`, and UTC timestamps are converted to local time via `convert_utc_to_local`. |
| Correlate (Pandas) | `correlate_events` groups and aggregates messages.                                   |
| Export (Threaded) | `write_to_excel` is offloaded to the `ThreadPoolExecutor` to perform the blocking file I/O operations without stopping the asynchronous processing of other clients. |

## 🔑 Critical Functions

| Function                             | Purpose                                                                                                                                       |
|--------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------|
| `convert_local_time_to_utc(...)`    | Converts the local time range defined in `time.json` into the standardized UTC format required by the API's absolute search endpoint.       |
| `correlate_events(messages)`         | Accepts a list of logs, generates a unique `group_key` for identical events, and returns a DataFrame where duplicate events are merged, and their timestamps are summarized. |
| `fetch_data_batch(...)`              | Performs batched asynchronous API requests using `aiohttp`'s `ClientSession`. Includes a retry mechanism (`fetch_with_retries`) for handling transient network errors. |
| `process_client(...)`                | The primary execution loop for a single client. It handles file opening (with retry logic), data fetching, transformation, and schedules the final Excel writing. |
| `write_to_excel(...)`                | Synchronous Excel writing function. It applies custom formatting (width, borders, fill) using `openpyxl` features and is designed to run within the `ThreadPoolExecutor`. |

