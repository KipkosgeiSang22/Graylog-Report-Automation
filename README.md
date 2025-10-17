📄 Technical Documentation: Async Log Export and Correlation Script
🧭 Overview
This Python script automates the retrieval, sanitization, correlation, and export of log data from multiple clients via Graylog's REST API. It reads queries from config.json, transforms and correlates log events, and exports structured Excel files—one per client.

⚙️ Key Technologies

 <img width="853" height="477" alt="image" src="https://github.com/user-attachments/assets/1993827f-e406-430b-a621-29040b7c0ae4" />




🌐 aiohttp – Asynchronous HTTP Requests
What it does:
- Sends non-blocking HTTP requests
- Allows parallel data fetching
- Works seamlessly with asyncio
Usage in script:
async with aiohttp.ClientSession() as session:
    async with session.get(...):
        return await response.json()


Real-World Analogy:
Think of aiohttp as a team of interns fetching logs. While they wait for responses, you continue working—no bottlenecks!


🔄 asyncio – Event Loop Orchestration
What it does:
- Manages concurrent tasks
- Prevents blocking during slow operations
- Coordinates async functions like a conductor
Usage in script:
await asyncio.gather(*tasks)


Real-World Analogy:
Like a SOC team working in parallel—firewall analysis, alert review, and report writing all happening concurrently.


📊 pandas – Data Manipulation & Export
Used for:
- Structuring logs with pd.DataFrame(messages)
- Grouping and correlating with groupby()
- Exporting to Excel via df.to_excel(...)

🖨️ openpyxl – Excel Writing Engine
Role:
- Handles sheet creation, formatting, and cell writing
Analogy:
If pandas is the author, openpyxl is the printer.


🌍 pytz – Timezone Conversion
Purpose:
- Converts UTC timestamps to local time (e.g., Africa/Nairobi)

🔍 re – Regular Expressions
Used for:
- re.search() to extract IPs
- re.sub() to clean sheet names and log values

🔐 Authentication
ENCODED_AUTH_STRING = '[your encoded password string]'
AUTH = f'Basic {ENCODED_AUTH_STRING}'
HEADERS = {
    'Authorization': AUTH,
    'X-Requested-By': 'export-script',
    'Accept': 'application/json'
}


- Uses Base64-encoded Basic Auth
- Includes metadata headers

📥 Input Configuration
Reads from config.json:
{
  "time_range": { "range": "300" },
  "clients": {
    "ClientA": {
      "base_url": "http://graylog.example.com",
      "queries": {
        "Login Events": "username:admin",
        "File Access": "action:file_open"
      }
    }
  }
}



🧠 Core Functions
|  |  | 
| convert_utc_to_local() |  | 
| correlate_events() |  | 
| extract_host_and_ip() |  | 
| sanitize_value() |  | 
| sanitize_sheet_name() |  | 
| fetch_data() |  | 
| process_client() |  | 
| main() | asyncio.gather | 



📤 Output
- One Excel file per client (e.g., ClientA.xlsx)
- Each sheet = one query/widget
- Columns include:
- Date & Time (correlated)
- Selected fields from REQUIRED_FIELDS
- destination_host_name, destination_host_ip

🧪 Error Handling
Gracefully skips:
- Widgets with no messages
- Empty correlation results
Logs errors during:
- Timestamp conversion
- API failures

🧼 Data Hygiene
- ASCII-only strings
- Removes control characters
- Sanitizes sheet names
- Filters relevant fields

🧠 Design Philosophy
- Modular, reusable functions
- Async architecture for scalability
- Clear separation of concerns:
Fetch → Sanitize → Transform → Export


Built for SOC automation, academic reporting, and portfolio-grade presentation.

🏁 Execution
Run the script:
python script_name.py


Ensure config.json is present and valid.

🔄 Real-Time Flow Summary
- ✅ Load config and prepare tasks
- ✅ For each client:
- Open Excel file
- For each query:
- Send async API request
- Sanitize and transform logs
- Correlate events
- Write to Excel sheet
- ✅ Repeat for all clients in parallel
- ✅ Close Excel files and finish


