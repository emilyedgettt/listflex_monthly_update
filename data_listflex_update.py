from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import os
import time
import datetime

# Load environment variables
load_dotenv("login.env")
LISTFLEX_USERNAME = os.getenv("LISTFLEX_USERNAME_DATA")
LISTFLEX_PASSWORD = os.getenv("LISTFLEX_PASSWORD_DATA")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

# Set up Google Sheets authentication
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("google_sheets_credentials.json", scope)
client = gspread.authorize(creds)



# Determine the correct worksheet dynamically
from datetime import datetime, timedelta

today = datetime.today()
# Move to the first day of next month by adding 32 days and resetting to day 1
first_day_next_month = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
next_month = first_day_next_month.strftime("%B").upper()

SHEET_NAME = f"{next_month} 25 NEW NEW"
print(f"Using worksheet for next month: {SHEET_NAME}")

# Open the worksheet
sheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet(SHEET_NAME)
all_data = sheet.get_all_values()
headers = [h.strip().lower() for h in all_data[0]]

# Define column names
status_col = "status"
list_name_col = "convoso list name"
list_id_col = "convoso"

# Convert headers to lowercase for reliable checking
headers_lower = [h.lower() for h in headers]

# Check if columns exist
if status_col not in headers or list_name_col not in headers or list_id_col not in headers:
    print("Column names don't match! Found headers:", headers)
    exit()

# Find column indexes
status_index = headers_lower.index(status_col)
list_name_index =  headers_lower.index(list_name_col)
list_id_index = headers_lower.index(list_id_col)

# Extract only "Active" rows
filtered_data = []
for row in all_data[1:]:
    status_value = row[status_index].strip().lower()
    list_name_value = row[list_name_index].strip()
    list_id_value = row[list_id_index].strip()

    if status_value == "active" and list_name_value and list_id_value:
        filtered_data.append({
            "Convoso List name" : list_name_value,
            "Convoso": list_id_value 
        })
print(f"Found {len(filtered_data)} active integrations to update.")



# Set up Selenium WebDriver
chrome_driver_path = "./chromedriver"
service = Service(chrome_driver_path)
options = webdriver.ChromeOptions()
driver = webdriver.Chrome(service=service, options=options)

# Log into Listflex
driver.get("https://data.listflex.com/lmadmin/login.php?r=plzlogin")
time.sleep(2)

driver.find_element(By.NAME, "username").send_keys(LISTFLEX_USERNAME)
driver.find_element(By.NAME, "password").send_keys(LISTFLEX_PASSWORD)
driver.find_element(By.TAG_NAME, "button").click()
time.sleep(5)  # Wait for login

# Navigate to API Integrations page
driver.get("https://data.listflex.com/lmadmin/client_integrations.php?client_id=420")
time.sleep(3)



# Debugging step: Print first entry to check key names
if filtered_data:
    print("First entry in filtered_data:", filtered_data[0].keys())

# Loop through all integrations from Google Sheets
for integration_data in filtered_data:
    integration_name = integration_data["Convoso List name"].strip()
    new_list_id = integration_data["Convoso"].strip()

    # Skip integrations that contain "WAVE"
    if "wave" in integration_name.lower():
        print(f"⚠ Skipping '{integration_name}' (WAVE integration).")
        continue

    print(f"\nSearching for integration: {integration_name} → New List ID: {new_list_id}")

    # Find all integration boxes on the page
    integration_boxes = driver.find_elements(By.CLASS_NAME, "statusbox")

    matching_edit_button = None

    for box in integration_boxes:
        try:
            # Get the integration name from the <h3> tag inside the box
            integration_title = box.find_element(By.TAG_NAME, "h3").text.strip()

            # Check if this is the correct integration (allowing slight variations)
            if integration_name.lower() in integration_title.lower():
                print(f"Found integration: {integration_title}")

                # Locate the "Edit" button inside this box
                matching_edit_button = box.find_element(By.CLASS_NAME, "btn_pencil")
                break  # Stop after finding the first match
        except:
            continue  # If anything fails, move to the next box

    # If no matching edit button is found, skip this integration
    if not matching_edit_button:
        print(f"Could not find 'Edit' button for '{integration_name}'. Skipping...")
        continue

    # Click the correct "Edit" button inside the correct integration box
    driver.execute_script("arguments[0].click();", matching_edit_button)  # Use JavaScript to force-click
    time.sleep(3)
    print(f"Clicked 'Edit' for {integration_name}")

    # Modify the "Post Variables" field
    post_variables_field = driver.find_element(By.ID, "post_vars")
    current_value = post_variables_field.get_attribute("value")

    # Ensure list_id is correctly updated
    if "list_id=" in current_value:
        updated_value = current_value.replace(
            f"list_id={current_value.split('list_id=')[1].split('&')[0]}",
            f"list_id={new_list_id}"
        )
    else:
        updated_value = current_value + f"&list_id={new_list_id}"

    post_variables_field.clear()
    post_variables_field.send_keys(updated_value)

    print(f"Updated '{integration_name}' to list_id={new_list_id}")

    # Click "Save Integration"
    save_button = driver.find_element(By.CLASS_NAME, "submit")
    driver.execute_script("arguments[0].click();", save_button)
    time.sleep(5)  # Wait for changes to apply

    print(f"Clicked 'Save Integration' for {integration_name}")

print("\nAll integrations updated successfully! Exiting script.")
driver.quit()