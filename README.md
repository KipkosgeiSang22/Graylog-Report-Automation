🛡️ Technical Documentation: Asynchronous Log Export and Correlation Script🧭 OverviewThis Python script automates the retrieval, sanitization, correlation, and export of high-volume log data from multiple client environments via Graylog's REST API. It leverages concurrency to create specialized, formatted Excel reports for SOC analysis and reporting.⚙️ Installation & Setup (Prerequisites)To run this script successfully, you must have Python 3.7+ and the following dependencies.1. DependenciesInstall all required libraries using pip:Bashpip install aiohttp pandas openpyxl pytz requests
2. File StructureEnsure your project directory contains the main script and the critical configuration file:/project_root
├── your_main_script_name.py  # The executable Python code
└── config.json               # Required for client connections and queries
🔐 Configuration & AuthenticationThe script is built to handle multiple Graylog environments securely.A. Generating the API TokenThe script uses HTTP Basic Authentication which requires a Base64-encoded string derived from a Graylog API Token (not your password).Generate Token: In Graylog, create an API Token for a user (username).Encode: Encode the string username:API_TOKEN into Base64. This result is the ENCODED_AUTH_STRING.Python# Authentication details set in the script's constants:
ENCODED_AUTH_STRING = 'UmVwb3J0Ok1QZHVzVHJQajFtRWFUUUV5YUtwdzlQUDZHTXJONA==' # Example
AUTH = f'Basic {ENCODED_AUTH_STRING}'

HEADERS = {
    'Authorization': AUTH,
    # ... other headers
}
B. Defining Clients and Queries (config.json)The config.json must specify the URL, authentication details, and the specific Graylog Query Language (GIMME) searches to run.JSON{
  "clients": {
    "ClientA_Finance": {
      "base_url": "https://graylog.clientA.com:12900/api",
      "ip_lookup": {},
      "queries": {
        "Login Events (RDP)": "EventID:4624 AND service:TerminalServices",
        "Credential Dumping Check": "Category:\"Process Create\" AND \"ntdsutil.exe\""
      }
    },
    "ClientB_HR": {
      "base_url": "https://graylog.clientB.com/api",
      "queries": { ... }
    }
  }
}
💻 Technical Component Breakdown1. Asynchronous ArchitectureComponentRoleWhy It MattersaiohttpAsynchronous HTTP RequestsSends requests to multiple client APIs concurrently, eliminating network I/O bottlenecks.asyncioEvent Loop OrchestrationManages all concurrent tasks and coordinates the workflow (like a conductor).ThreadPoolExecutorConcurrencyManages a pool of threads to safely offload synchronous, blocking tasks (like heavy Excel I/O) from the main async loop.2. Data Transformation Toolspandas: Used for structuring raw log arrays (pd.DataFrame(messages)), data grouping (groupby()), and final export.openpyxl: The printing engine; handles sheet creation and specialized Excel formatting (cell colors, border, column widths) that standard Pandas export cannot do.pytz: Converts all received UTC timestamps to the configured local timezone (e.g., Africa/Nairobi) for accurate display and reporting.🧩 Data Processing Deep Dive1. Data Correlation (correlate_events)This is the script's intelligence layer, designed to reduce event noise for SOC analysts:Mechanism: Logs are grouped based on the concatenated string values of all fields listed in the REQUIRED_FIELDS array, excluding the timestamp.Result: Duplicate or sequential logs originating from the same system, user, and action are condensed into one row. The final Date & Time column consolidates the start, middle, and end timestamps of the correlated event sequence.2. Data Hygiene and FilteringFeatureCode LogicSOC BenefitSanitizationsanitize_value()Ensures data is clean (ASCII-only), removing control characters (\x00-\x1F) that corrupt downstream systems like Excel.Field FilteringUses the static REQUIRED_FIELDS array.Guarantees that the output spreadsheet is structured and only contains metadata relevant for triage and reporting.📤 Output and ExecutionOutput: One fully formatted Excel file is generated per client, with each worksheet corresponding to a single query (e.g., "Login Events").Columns: Include all required metadata, the correlated Date & Time field, and normalized host/IP information.🏁 ExecutionRun the script from your Python environment:Bashpython your_main_script_name.py
Ensure that the config.json file is present in the execution directory.
