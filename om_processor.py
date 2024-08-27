import os
import io
import openai
import markdown
import time
import requests
from googleapiclient.discovery import build
from datetime import datetime
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from google.oauth2.service_account import Credentials
from PyPDF2 import PdfReader
from RealEstateExtraction import RealEstateExtraction

## CONSTANTS

#Drive
SHARED_DRIVE_ID = '0APHQBI6riR7qUk9PVA'
UNPROCESSED_FOLDER_ID = "1WCQJM7uNFe3yImoQW7ywwfd6jJQQDxTI"
PDF_W_MD_FOLDER_ID = "1WJsr5hhnWb-u0m5KG3AQy5EJ62UsmH9w"
PDFS_AND_MD_IN_SHEETS_FOLDER_ID = "1WEHtpgoxTHc2QrWrtJYZbdjLxDn3No8W"
SPREADSHEET_ID = "1aCsoLTBYxra3mtyGXvJoPnElOdkTOHH9pM5klz_HKU8"
SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = 'Resources/EsmeesServiceAccountKey.json'

#Marker
MARKER_API_KEY = "NpujIN2fzkNYZQYbCN2X-4QpQMe70dy7HKv_onCtM4I"
MARKER_URL = "https://www.datalab.to/api/v1/marker"

#OpenAI
OPENAI_API_KEY = "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"

#Local
INSTRUCTIONS_FILE = 'Resources/instructions.txt'  # Path to the instructions text file

# Initialize the Google Drive and Sheets API clients
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=creds)
sheets_service = build('sheets', 'v4', credentials=creds)

# Set up OpenAI API
openai.api_key = OPENAI_API_KEY

def get_files_in_folder(folder_id):
    """Fetch the list of files in a Google Drive folder, including shared drives."""
    query = f"'{folder_id}' in parents"
    results = drive_service.files().list(
        q=query,
        includeItemsFromAllDrives=True,
        supportsAllDrives=True,
        corpora="drive",
        driveId=SHARED_DRIVE_ID
    ).execute()
    return results.get('files', [])

def download_file(file_id, file_name):
    request = drive_service.files().get_media(fileId=file_id)
    file = io.BytesIO()
    downloader = MediaIoBaseDownload(file, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
        print(f"Download {int(status.progress() * 100)}%.")
    file.seek(0)
    with open(file_name, 'wb') as f:
        f.write(file.read())

def upload_file(file_path, folder_id):
    """Upload a file to a specific folder in a shared drive."""
    file_metadata = {'name': os.path.basename(file_path), 'parents': [folder_id]}
    media = MediaFileUpload(file_path, mimetype='application/octet-stream')
    uploaded_file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id',
        supportsAllDrives=True
    ).execute()
    return uploaded_file.get('id')

def move_object_to_folder(object_id, new_folder_id):
    """Move a file to a new folder in a Google Drive shared drive."""
    file = drive_service.files().get(fileId=object_id, fields="parents", supportsAllDrives=True).execute()
    previous_parents = ",".join(file.get("parents"))
    drive_service.files().update(
        fileId=object_id,
        addParents=new_folder_id,
        removeParents=previous_parents,
        fields="id, parents",
        supportsAllDrives=True
    ).execute()

def create_folder_in_drive(folder_name, parent_folder_id):
    """Create a new folder in Google Drive."""
    folder_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_folder_id]
    }
    folder = drive_service.files().create(body=folder_metadata, fields='id', supportsAllDrives=True).execute()
    return folder.get('id')

def get_markdown(pdf_path):
    url = MARKER_URL
    headers = {"X-Api-Key": MARKER_API_KEY}
    form_data = {
        'file': ('document.pdf', open(pdf_path, 'rb'), 'application/pdf'),
        "langs": (None, "en"),
        "force_ocr": (None, False),
        "paginate": (None, False)
    }
    response = requests.post(url, files=form_data, headers=headers)
    if response.status_code != 200:
        print(f"Error: Received status code {response.status_code}")
        print(response.text)
        return None

    data = response.json()
    if not data.get('success', False):
        print(f"Error: {data.get('error', 'Unknown error occurred')}")
        return None

    check_url = data["request_check_url"]
    max_polls = 300
    interval = 2

    for i in range(max_polls):
        time.sleep(interval)
        response = requests.get(check_url, headers=headers)
        data = response.json()

        if data["status"] == "complete":
            break
        elif data["status"] == "failed":
            print("Conversion failed.")
            return None

    if data.get("success", False):
        return data.get("markdown", "")
    else:
        print(f"Error: {data.get('error', 'Unknown error occurred')}")
        return None
    
def pdf_to_markdown():
    files = get_files_in_folder(UNPROCESSED_FOLDER_ID)
    for file in files:
        pdf_file_id = file['id']
        pdf_file_name = file['name']
        local_pdf_path = pdf_file_name

        # Download the PDF file
        download_file(pdf_file_id, local_pdf_path)

        # Convert the PDF to Markdown
        markdown_content = get_markdown(local_pdf_path)
        if markdown_content:
            # Save the markdown content to a file
            markdown_file_name = os.path.splitext(pdf_file_name)[0] + ".md"
            with open(markdown_file_name, 'w') as md_file:
                md_file.write(markdown_content)
            
            #create a folder to house the markdown and pdf files in
            wrapper_folder_id = create_folder_in_drive(pdf_file_name[0:-4], PDF_W_MD_FOLDER_ID)

            # Upload the markdown file to the new location
            markdown_file_id = upload_file(markdown_file_name, wrapper_folder_id)

            # Move the original PDF file to the new location
            move_object_to_folder(pdf_file_id, wrapper_folder_id)

            # Clean up local files
            os.remove(local_pdf_path)
            os.remove(markdown_file_name)

            print(f"Processed {pdf_file_name} successfully!")

def extract_text_from_markdown(markdown_file_path):
    """Read and return the content of a markdown file."""
    with open(markdown_file_path, 'r') as f:
        text = f.read()
    return markdown.markdown(text)

def extract_text_from_instructions(file_path):
    """Load the instructions from a text file."""
    with open(file_path, 'r') as f:
        instructions = f.read()
    return instructions

def extract_text_from_pdf(file_path):
    text = ""
    with open(file_path, 'rb') as file:
            reader = PdfReader(file)
            for page in reader.pages:
                text += page.extract_text()
    return text

def process_folder(folder_id):
    files = get_files_in_folder(folder_id)
    pdf_file = None
    markdown_file = None

    for file in files:
        if file['mimeType'] == 'application/pdf':
            pdf_file = file
        elif file['mimeType'] == 'text/markdown':
            markdown_file = file

    if pdf_file and markdown_file:
        download_file(pdf_file['id'], pdf_file['name'])
        pdf_text = extract_text_from_pdf(pdf_file['name'])
        os.remove(pdf_file['name'])

        download_file(markdown_file['id'], markdown_file['name'])
        markdown_text = extract_text_from_markdown(markdown_file['name'])
        os.remove(markdown_file['name'])

        return pdf_text, markdown_text

    return None, None

def send_request_to_openai(pdf_text, markdown_text, instructions):
    """Send a request to the OpenAI API with the extracted PDF and Markdown text."""
    prompt = f"#INSTRUCTIONS\n\n{instructions}\n\n#PDF TEXT:\n\n{pdf_text}\n\n#MARKDOWN TEXT:\n\n{markdown_text}"

    response = openai.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ], 
        response_format=RealEstateExtraction
    )
    print("RESPONSE: "+str(response.choices[0].message.content))
    return eval(response.choices[0].message.content)

# replace all of places where chatgpt couldn't get data with empty strings and ensure that all entries are well-formed
def reformatResult(result):
    #reformating the entries
    for key in result:
        if (((key != "parkingSpaces") and (result[key] == 0)) or
            (result[key] in [-1, "NA", None])):
            result[key] = ""
        if (key == "postalCode"):
            digitList = result[key]
            result[key] = digitList["tenthousandsPlaceDigit"] + digitList["thousandsPlaceDigit"] + digitList["hundredsPlaceDigit"] + digitList["tensPlaceDigit"] + digitList["onesPlaceDigit"]
        if (key in ["propertyName", "owners", "city", "county", "tenants", "seller", "sellersBroker"]):
            wordsList = result[key].split(" ")
            for word in wordsList:
                word = word.capitalize()
            result[key] = " ".join(wordsList)

    #adding a time stamp in UTC 
    result.update({"timeDataEntered": str(datetime.utcnow())})

def insert_result_into_sheet(spreadsheet_id, result):
    """Insert the result into the first empty row of a Google Sheets spreadsheet."""
    sheet_name = "'Properties - From OMs'"  # Enclose the sheet name in single quotes
    range_name = "A:A"  # Specifying the range in the sheet

    # Get the current data in column A to find the first empty row
    data = sheets_service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=range_name
    ).execute()

    values = data.get('values', [])

    # The first empty row is the length of the data + 1
    first_empty_row = len(values) + 1

    reformatResult(result)

    #prepare body
    body = {'values': [list(result.values())]}

    # Insert data at the first empty row
    sheets_service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=str(first_empty_row)+":"+str(first_empty_row),
        valueInputOption="USER_ENTERED",
        body=body
    ).execute()

def pdf_and_md_to_sheets():
    instructions = extract_text_from_instructions(INSTRUCTIONS_FILE)  # Load the instructions from the text file
    folders = get_files_in_folder(PDF_W_MD_FOLDER_ID)

    for folder in folders:
        folder_id = folder['id']
        pdf_text, markdown_text = process_folder(folder_id)

        if pdf_text and markdown_text:
            result = send_request_to_openai(pdf_text, markdown_text, instructions)
            insert_result_into_sheet(SPREADSHEET_ID, result)
            move_object_to_folder(folder_id, PDFS_AND_MD_IN_SHEETS_FOLDER_ID)


def main():
   # pdf_to_markdown()
   pdf_and_md_to_sheets()

    

if __name__ == '__main__':
    main()