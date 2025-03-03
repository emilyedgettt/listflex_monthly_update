from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import os
import time
import datetime
from datetime import datetime, timedelta

# Load environment variables
load_dotenv("login.env")
LISTFLEX_USERNAME = os.getenv("LISTFLEX_USERNAME_MON")
LISTFLEX_PASSWORD = os.getenv("LISTFLEX_PASSWORD_MON")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

# Set up Google Sheets authentication
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("google_sheets_credentials.json", scope)
client = gspread.authorize(creds)



# Determine the correct worksheet dynamically
today = datetime.today()
first_day_next_month = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
next_month = first_day_next_month.strftime("%B").upper()

SHEET_NAME = "MARCH 25 - OG"
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
if status_col not in headers_lower or list_name_col not in headers_lower or list_id_col not in headers_lower:
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
driver.get("https://monumental.listflex.com/lmadmin/login.php?r=plzlogin")
time.sleep(2)

driver.find_element(By.NAME, "username").send_keys(LISTFLEX_USERNAME)
driver.find_element(By.NAME, "password").send_keys(LISTFLEX_PASSWORD)
driver.find_element(By.TAG_NAME, "button").click()
time.sleep(5)  # Wait for login

# Navigate to API Integrations page
driver.get("https://monumental.listflex.com/lmadmin/client_integrations.php?client_id=420")
time.sleep(3)



# Group integrations by list_id so we can update all matches
integrations_by_list_id = {}
for integration_data in filtered_data:
    integration_name = integration_data["Convoso List name"].strip()
    new_list_id = integration_data["Convoso"].strip()

    # Skip integrations that contain "WAVE"
    if "wave" in integration_name.lower():
        print(f"Skipping '{integration_name}' (WAVE integration).")
        continue
    if new_list_id in integrations_by_list_id:
        integrations_by_list_id[new_list_id].append(integration_name)
    else:
        integrations_by_list_id[new_list_id] = [integration_name]


# Track successfully updated integrations
    updated_integrations = []

# Loop through each integration and update it
for integration_data in filtered_data:
    integration_name = integration_data["Convoso List name"].strip()
    new_list_id = integration_data["Convoso"].strip()

    # Skip integrations that contain "WAVE"
    if "wave" in integration_name.lower():
        print(f"Skipping '{integration_name}' (WAVE integration).")
        continue

    print(f"\nSearching for integration: {integration_name} → New List ID: {new_list_id}")

    # Reload integrations page before searching again
    driver.get("https://monumental.listflex.com/lmadmin/client_integrations.php?client_id=420")
    time.sleep(5)

    # Find all integration boxes on the page
    integration_boxes = driver.find_elements(By.CLASS_NAME, "statusbox")
    found_integrations = []

    for box in integration_boxes:
        try:
            integration_title = box.find_element(By.TAG_NAME, "h3").text.strip()
            if integration_name.lower() in integration_title.lower():
                found_integrations.append((integration_title, box.find_element(By.CLASS_NAME)))
        except:
            continue

    if not found_integrations:
        print(f"Could not find 'Edit' button for '{integration_name}'. Skipping...")
        continue

    # Process each found integration
    for integration_title, edit_button in found_integrations:
        try:
            # Scroll into view before clicking
            driver.execute_script("arguments[0].scrollIntoView();", edit_button)
            time.sleep(1)
    
            # Click "Edit" button
            driver.execute_script("arguments[0].click();", edit_button)
            time.sleep(3)
            print(f"Editing integration: {integration_name}")

            # Modify the "Post Variables" field
            post_variables_field = driver.find_element(By.ID, "post_vars")
            current_value = post_variables_field.get_attribute("value")

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
            time.sleep(5)

            print(f"Clicked 'Save Integration' for {integration_name}")

            # Mark as updated
            updated_integrations.append(integration_name)

        except Exception as e:
            print(f"Error updating integration '{integration_title}': {e}")
            continue

# Confirm which integrations were updated
if updated_integrations:
    print(f"\n Successfully updated integrations: {updated_integrations}")
else:
    print(f"No integrations updated.")

# Exit script
print("\nAll integrations updated successfully! Exiting script.")
driver.quit()