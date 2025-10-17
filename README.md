Technical Documentation: Async Log Export and Correlation Script
Overview
This Python script automates the retrieval, sanitization, correlation, and export of log data from multiple clients via Graylog's REST API. It processes queries defined in a configuration file (config.json), transforms and correlates log events, and exports the results into structured Excel files—one per client.

⚙️ Key Technologies
Python 3.8+
aiohttp – Asynchronous HTTP requests (Non-blocking)
🌐 What Is aiohttp?
The aiohttp Python library allows you to make HTTP requests asynchronously—meaning the code can send and receive data from web servers without blocking other tasks. It’s like the async version of requests, built to work with asyncio.

With aiohttp, you can:

Fire off all requests at once
Let the event loop manage them
Process responses as they arrive
🚀 Result: Faster, non-blocking, parallel data fetching.

In the script, this is used as follows:

python

Run

async with aiohttp.ClientSession() as session:
    async with session.get(...):
        return await response.json()
This does three things:

Opens a reusable session for efficient HTTP calls.
Sends a GET request to Graylog’s API.
Awaits the response without freezing the rest of the script.
🧪 Real-World Analogy
Think of aiohttp as a team of interns:

You give each intern a task (fetch logs from a server).
They wait for the server to respond.
Meanwhile, you’re free to do other work.
As each intern returns, you handle their results.
No bottlenecks. No idle waiting. Just smooth, concurrent execution.

3. asyncio – Event Loop Orchestration
asyncio is Python’s built-in library for writing asynchronous code—code that can handle many tasks at once without waiting for each one to finish before starting the next.

🔄 What Is an Event Loop?
Think of the event loop as a smart traffic controller:

It watches over all your asynchronous tasks.
It decides which task to run next.
It pauses tasks that are waiting (e.g., for network responses).
It resumes them when the wait is over.
🧩 What Does “Event Loop Orchestration” Mean?
It means asyncio is coordinating all your async tasks—like a conductor leading an orchestra:

🎻 One task is fetching logs from Client A.
🎺 Another is processing Client B’s queries.
🥁 A third is writing Excel sheets for Client C.
In the script, asyncio is used for orchestration:

python

Run

await asyncio.gather(*tasks)
This line tells the event loop: “Run all these client tasks at the same time. Don’t wait for one to finish before starting the next.”

🧪 Real-World Analogy
Imagine you’re managing a SOC team:

One analyst is checking firewall logs.
Another is reviewing Snort alerts.
A third is writing the incident report.
You don’t make them wait for each other—you let them work in parallel. That’s exactly what asyncio does for the script.

4. pandas – Data Manipulation and Excel Export
In the script, it is used to:

pd.DataFrame(messages) to turn raw logs into a structured table.
Group and correlate events using groupby() and aggregation.
Export to Excel with df.to_excel(writer, sheet_name=..., index=False).
5. openpyxl – Excel Writing Engine
It handles the actual file creation, sheet formatting, and cell writing.
🧪 Analogy: If pandas is the author of your report, openpyxl is the printer that produces the final document.

6. pytz – Timezone Conversion
pytz helps convert timestamps between time zones accurately.
Logs often come in UTC.
7. re – Regular Expressions for Parsing
re is Python’s pattern-matching tool. It helps you extract or clean specific pieces of text using flexible search patterns.

🔧 In my script, I have used it in the following ways:

re.search() to extract IP addresses from strings.
re.sub() to clean out unwanted characters from sheet names and log values.
🔐 Authentication
python

Run

ENCODED_AUTH_STRING = '[ your encoded password string]'
AUTH = f'Basic {ENCODED_AUTH_STRING}'
HEADERS = {
    'Authorization': AUTH,
    'X-Requested-By': 'export-script',
    'Accept': 'application/json'
}
Uses a Base64-encoded Basic Auth string. Headers include authorization and request metadata.

📥 Input Configuration
Reads from config.json with the following structure:

json

{
    "time_range": {
        "range": "300"
    },
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
convert_utc_to_local(utc_timestamp, local_tz_str): Converts ISO-formatted UTC timestamps to local time (default: Africa/Nairobi).
correlate_events(messages): Groups identical log entries (excluding timestamp) and merges their timestamps into a single range.
extract_host_and_ip(collector_node_id): Parses collector_node_id to extract destination host name and IP address using regex.
sanitize_value(value): Recursively removes control characters and non-ASCII characters.
sanitize_sheet_name(sheet_name): Cleans Excel sheet names by removing invalid characters and truncating to 31 characters.
fetch_data(session, base_url, query, range_value): Performs async GET request to Graylog's API.
process_client(client_name, data): Main processing pipeline for each client.
main(): Orchestrates the entire workflow.
📤 Output
One Excel file per client: ClientA.xlsx
Each sheet corresponds to a widget/query.
Columns include:
Date & Time (correlated timestamps)
Selected fields from REQUIRED_FIELDS
destination_host_name, destination_host_ip (if extracted)
🧪 Error Handling
Gracefully skips widgets with:

Missing messages
Empty correlation results
Logs errors during:
Timestamp conversion
API fetch failures
🧼 Data Hygiene
Ensures clean, ASCII-only strings.
Removes control characters.
Sanitizes sheet names for Excel compatibility.
Filters only relevant fields for export.
🧠 Design Philosophy
Modular and reusable functions.
Async architecture for scalability.
Clear separation of concerns: Fetch → Sanitize → Transform → Export.
Designed for SOC automation, academic reporting, and portfolio-grade presentation.
🏁 Execution
Run the script via:

bash

python script_name.py
Ensure config.json is present and valid.

Real-Time Flow Summary
Here’s how it plays out when you run the script:

✅ Load config and prepare tasks.
✅ For each client:
Open Excel file.
For each query:
Send async API request.
Sanitize and transform logs.
Correlate events.
Write to Excel sheet.
✅ Repeat for all clients in parallel.
✅ Close Excel files and finish.
