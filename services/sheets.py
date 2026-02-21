"""
Sheets Service
Handles Google Sheets interactions using gspread.
"""

import os
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

import re

# Build logic for authentication
# Assuming credentials.json is in the root backend folder
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

def extract_id_from_url(input_str: str) -> str:
    """Extracts the spreadsheet ID from a full Google Sheets URL or returns the ID if already one."""
    # Pattern for Google Sheets ID
    pattern = r'/spreadsheets/d/([a-zA-Z0-9-_]+)'
    match = re.search(pattern, input_str)
    if match:
        return match.group(1)
    # If no match but contains slash, might be some other URL format, 
    # but let's just return stripped input
    return input_str.strip()

import json

def get_client():
    """Authenticates and returns a gspread client."""
    # Priority 1: Environment variable (good for Railway)
    creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
    if creds_json:
        try:
            creds_dict = json.loads(creds_json)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
            return gspread.authorize(creds)
        except Exception as e:
            print(f"Error loading credentials from GOOGLE_SHEETS_CREDENTIALS: {e}")

    # Priority 2: Local file (good for localhost)
    creds_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'credentials.json')
    if os.path.exists(creds_file):
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_file, SCOPE)
        return gspread.authorize(creds)
    
    raise FileNotFoundError(
        "Credentials not found! Please set GOOGLE_SHEETS_CREDENTIALS environment variable "
        "or ensure credentials.json exists in the root directory."
    )

def create_project_sheet(project_name: str):
    """Creates a new Google Sheet for the project."""
    client = get_client()
    sh = client.create(project_name)
    sh.share(client.auth.service_account_email, perm_type='user', role='owner')
    # Or share with user's email if provided

    # Initialize headers
    worksheet = sh.get_worksheet(0)
    headers = ["Выбрать", "Title", "Link", "Keywords", "Description", "New Description", "Text"]
    worksheet.append_row(headers)

    # Return metadata
    return {
        "id": sh.id,
        "name": sh.title,
        "url": sh.url,
        "created_at": datetime.now().isoformat()
    }

def get_project_data(sheet_id: str):
    """Fetches all data from the project sheet."""
    client = get_client()
    sh = client.open_by_key(extract_id_from_url(sheet_id))
    worksheet = sh.get_worksheet(0)
    data = worksheet.get_all_records()
    return data

def add_rows(sheet_id: str, rows: list):
    """
    Appends new rows to the sheet.
    rows: list of dicts matching headers
    """
    client = get_client()
    sh = client.open_by_key(extract_id_from_url(sheet_id))
    worksheet = sh.get_worksheet(0)

    # Convert dicts to list of lists based on headers
    headers = worksheet.row_values(1)
    values = []
    for row in rows:
        row_values = [row.get(h, "") for h in headers]
        values.append(row_values)

    worksheet.append_rows(values)
    return len(values)

def update_row(sheet_id: str, row_index: int, updates: dict):
    """Updates specific cells in a row."""
    # row_index is 0-based index from data (so actual row is index + 2 because of header)
    client = get_client()
    sh = client.open_by_key(extract_id_from_url(sheet_id))
    worksheet = sh.get_worksheet(0)

    headers = worksheet.row_values(1)

    # We can use batch update or cell updates.
    # For now, simple cell updates might be slow but safe
    # Or construct a range update
    cells_to_update = []
    actual_row = row_index + 2

    for col_name, value in updates.items():
        if col_name in headers:
            col_idx = headers.index(col_name) + 1
            cells_to_update.append(gspread.Cell(actual_row, col_idx, value))

    if cells_to_update:
        worksheet.update_cells(cells_to_update)

    return True

def replace_project_data(sheet_id: str, new_data: list):
    """
    Replaces the entire sheet content with new_data.
    Safest for 'Save All' in a small project.
    """
    client = get_client()
    sh = client.open_by_key(extract_id_from_url(sheet_id))
    worksheet = sh.get_worksheet(0)

    # clear
    worksheet.clear()

    # Headers
    headers = ["Выбрать", "Title", "Link", "Keywords", "Description", "New Description", "Text"]
    worksheet.append_row(headers)

    # Rows
    # Ensure order matches headers
    values = []
    for row in new_data:
        # data_editor might return varied types, ensure string
        row_values = [str(row.get(h, "")) for h in headers]
        values.append(row_values)

    if values:
        worksheet.append_rows(values)

    return True
