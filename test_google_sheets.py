import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import os

# ✅ Load environment variables
load_dotenv("login.env")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

# ✅ Authenticate with Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("google_sheets_credentials.json", scope)
client = gspread.authorize(creds)

# ✅ Open the correct worksheet (update manually for testing)
SHEET_NAME = "MARCH 25 NEW NEW"
sheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet(SHEET_NAME)

# ✅ Get ALL rows from Google Sheets
all_data = sheet.get_all_values()  # This retrieves all rows

# ✅ Extract headers from the first row (make them lowercase for consistency)
headers = [h.strip().lower() for h in all_data[0]]  # Removes extra spaces & forces lowercase

# ✅ Define the correct column keys (must match Google Sheet headers EXACTLY)
status_col = "status"
list_name_col = "convoso list name"
list_id_col = "convoso"

# ✅ Check if columns actually exist in the headers
if status_col not in headers or list_name_col not in headers or list_id_col not in headers:
    print("❌ Column names don't match! Found headers:", headers)
    exit()

# ✅ Find index positions for each column
status_index = headers.index(status_col)
list_name_index = headers.index(list_name_col)
list_id_index = headers.index(list_id_col)

# ✅ Extract only relevant rows
filtered_data = []
for row in all_data[1:]:  # Skip header row
    status_value = row[status_index].strip().lower()  # Normalize "Status"
    list_name_value = row[list_name_index].strip()
    list_id_value = row[list_id_index].strip()

    # ✅ Only keep rows where "Status" == "Active" (case insensitive) AND both values exist
    if status_value == "active" and list_name_value and list_id_value:
        filtered_data.append({
            "Convoso List name": list_name_value,
            "Convoso": list_id_value
        })

# ✅ Print the cleaned data
print(filtered_data)