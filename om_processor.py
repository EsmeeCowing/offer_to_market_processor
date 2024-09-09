import os
import io
import openai
import time
import requests
import json
from googleapiclient.discovery import build
from datetime import datetime, timezone
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from google.oauth2.service_account import Credentials
from PyPDF2 import PdfReader
from RealEstateExtraction import RealEstateExtraction

#//////////////////////////////////////////CONSTANTS\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\

# Drive
SHARED_DRIVE_ID = '0APHQBI6riR7qUk9PVA'
UNPROCESSED_FOLDER_ID = "1WCQJM7uNFe3yImoQW7ywwfd6jJQQDxTI"
PDF_W_MD_FOLDER_ID = "1WJsr5hhnWb-u0m5KG3AQy5EJ62UsmH9w"
PDFS_AND_MD_IN_SHEETS_FOLDER_ID = "1WEHtpgoxTHc2QrWrtJYZbdjLxDn3No8W"
PROBLEMATIC_DOCUMENTS_FOLDER_ID = "1-RuX8ry5BdplYDHj18oElyloMYZM-dj5"
SPREADSHEET_ID = "1aCsoLTBYxra3mtyGXvJoPnElOdkTOHH9pM5klz_HKU8"
SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE_PATH = 'resources/authentication/esmeesServiceAccountKey.json'
CREDS = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE_PATH, scopes=SCOPES)
DRIVE_SERVICE = build('drive', 'v3', credentials=CREDS)
SHEETS_SERVICE = build('sheets', 'v4', credentials=CREDS)

# Marker
with open('resources/authentication/APIKeys.json', 'r') as apiKeys:
    MARKER_API_KEY = json.load(apiKeys)['marker']
MARKER_URL = "https://www.datalab.to/api/v1/marker"

# OpenAI
with open('resources/authentication/APIKeys.json', 'r') as apiKeys:
    OPENAI_API_KEY = json.load(apiKeys)['openai']
openai.api_key = OPENAI_API_KEY
BLANK_VALUES = ["NA", "NANANANANANA" -1] #Values ChatGPT has been instructed to return if it cannot find the information corresponding to a column in the spreadsheet in the pdf and markdown files. noinfo is a blank value because a zip code must be 5 digits and noinfo is . 
RESPONSE_FORMAT = RealEstateExtraction

# Local
INSTRUCTIONS_FILE_PATH = 'resources/instructions.txt'
ERROR_LOG_PATH = "resources/errors.log"

#//////////////////////////////////////////HELPER FUNCTIONS\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\

# Helper function for error logging
# Purpose: Writes an error message to the error log file.
# Arguments: error (the error message to be logged)
# Returns: None
def writeToErrorLog(error):
    with open(ERROR_LOG_PATH, "a") as errorLog:
        errorLog.write(f"ERROR: {error} \n")
        errorLog.write("TIME ERROR OCURRED (UTC): "+str(datetime.now(timezone.utc))+"\n\n")

# WRAPPER FUNCTIONS FOR API QUERIES

# Purpose: get a list of files in a google drive folder
# Arguments: folder_id (the id of the folder from which the function will get the list of files)
# Returns: the lisf files in the folder with folder_id
def getFilesInFolderQuery(folder_id):
    query = f"'{folder_id}' in parents"
    results = DRIVE_SERVICE.files().list(q=query, includeItemsFromAllDrives=True, supportsAllDrives=True, corpora="drive", driveId=SHARED_DRIVE_ID).execute()
    return results.get('files', [])

# Purpose: Downloads a file from Google Drive and saves it locally.
# Arguments: 
#   - file_id: The ID of the file to download.
#   - file_name: The name to use when saving the file locally.
# Returns: None
def downloadFileQuery(file_id, file_name):
    request = DRIVE_SERVICE.files().get_media(fileId=file_id)
    file = io.BytesIO()
    downloader = MediaIoBaseDownload(file, request)

    done = False
    while done is False:
        status, done = downloader.next_chunk()
    
    file.seek(0)
    with open(file_name, 'wb') as f:
        f.write(file.read())

# Purpose: Uploads a file to a specified folder in Google Drive.
# Arguments: 
#   - file_path: The path of the file to upload.
#   - folder_id: The ID of the folder to upload the file to.
# Returns: The uploaded file's metadata.
def uploadFileQuery(file_path, folder_id):
    file_metadata = {'name': os.path.basename(file_path), 'parents': [folder_id]}
    media = MediaFileUpload(file_path, mimetype='application/octet-stream')
    uploaded_file = DRIVE_SERVICE.files().create(body=file_metadata, media_body=media, fields='id', supportsAllDrives=True).execute()
    return uploaded_file

# Purpose: Moves an object (file or folder) to a new folder in Google Drive.
# Arguments: 
#   - object_id: The ID of the object to move.
#   - new_folder_id: The ID of the folder to move the object to.
# Returns: None
def moveObjectToFolderQuery(object_id, new_folder_id):
    file = DRIVE_SERVICE.files().get(fileId=object_id, fields="parents", supportsAllDrives=True).execute()
    previous_parents = ",".join(file.get("parents"))
    DRIVE_SERVICE.files().update(fileId=object_id, addParents=new_folder_id, removeParents=previous_parents, fields="id, parents", supportsAllDrives=True).execute()

# Purpose: Moves an object (file or folder) to the trash in Google Drive.
# Arguments: 
#   - object_id: The ID of the object to move to the trash.
# Returns: None
def moveObjectToTrashQuery(object_id):
    DRIVE_SERVICE.files().update(fileId=object_id, body={'trashed': True}).execute()

# Purpose: Creates a new folder in a specified parent folder in Google Drive.
# Arguments: 
#   - folder_name: The name of the new folder.
#   - parent_folder_id: The ID of the parent folder.
# Returns: The created folder's metadata.
def createFolderQuery(folder_name, parent_folder_id):
    folder_metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [parent_folder_id]}
    folder = DRIVE_SERVICE.files().create(body=folder_metadata, fields='id', supportsAllDrives=True).execute()
    return folder

# Purpose: Converts a PDF to markdown using the Marker API.
# Arguments: 
#   - pdf_path: The path of the PDF file to convert.
# Returns: The markdown content extracted from the PDF.
def getMarkdownFromPDFQuery(pdf_path):
    url = MARKER_URL
    headers = {"X-Api-Key": MARKER_API_KEY}
    form_data = {'file': ('document.pdf', open(pdf_path, 'rb'), 'application/pdf'), "langs": (None, "en"), "force_ocr": (None, False), "paginate": (None, False)}

    response = requests.post(url, files=form_data, headers=headers)
    data = response.json()

    return data.get("markdown", "")

# Purpose: Retrieves the first empty row in a Google Sheets spreadsheet.
# Arguments: 
#   - spreadsheet_id: The ID of the spreadsheet to check.
# Returns: The index of the first empty row.
def getFirstEmptySpreadsheetRowQuery(spreadsheet_id):
    data = SHEETS_SERVICE.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range="A:A").execute() # I made the range A:A here because column A will likely always have values in it if there is data in the row. If this turns out not to be true in the future, then this should probably be changed.
    values = data.get('values', [])
    return len(values)+1

# Purpose: Writes a list of data to a specified row in a Google Sheets spreadsheet.
# Arguments: 
#   - spreadsheet_id: The ID of the spreadsheet.
#   - row: The row number to write data to.
#   - data: The data to write to the row (as a list).
# Returns: None
def writeListToSpreadsheetRowQuery(spreadsheet_id, row, data):
    body = {'values': [list(data.values())]}
    SHEETS_SERVICE.spreadsheets().values().update(spreadsheetId=spreadsheet_id, range=f"{str(row)}:{str(row)}", valueInputOption="USER_ENTERED", body=body ).execute()

# Purpose: Sends a query to the GPT-4o API and returns a response in a specified format.
# Arguments: 
#   - question: The query string to send.
#   - responseFormat: The format in which the response should be returned. This should be defined as a class.
# Returns: The API response.
def chatGPT4oQuery(question, responseFormat):
    return openai.beta.chat.completions.parse(model="gpt-4o-2024-08-06", messages=[{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": question}], response_format=responseFormat)

# WAPPER FUNCTION FOR THE FUNCTIONS ABOVE THAT HANDLES EXCEPTIONS

# Purpose: Executes a query function and retries in case of failure, with error handling.
# Arguments: 
#   - query_function: The function to be executed.
#   - inputs: A list of inputs to pass to the query function.
#   - error_message: The message to log in case of failure.
#   - max_query_attempts: Maximum number of retry attempts (default is 6).
#   - wait_interval: Time (in seconds) to first wait between retry attempts (default is 2). runQuery will back off exponentially as it retries.
#   - remaining_attempts: The number of remaining retries (None for initial call).
#   - put_object_in_problematic_documents_if_fails: Whether to move an object (file or folder) to the Problematic Documents folder if the query fails (default is False). This is a feature specifically for queries that involve files.
#   - object: The object to move in case of failure (default is False).
# Returns: The query function's response or False in case of failure.
def runQuery(query_function, inputs, error_message, max_query_attempts=6, wait_interval=2, remaining_attempts=None, put_object_in_problematic_documents_if_fails=False, object=False):
    if remaining_attempts is None:
        remaining_attempts = max_query_attempts
    try:
        response = query_function(*inputs)
    except Exception as e:
        writeToErrorLog(e)
        if remaining_attempts <= 0:
            writeToErrorLog(error_message)
            if put_object_in_problematic_documents_if_fails:
                if object == False:
                    writeToErrorLog("tried to move an object to the Problematic Documents folder in runQuery but caller did not provide the object to move")
                else:
                    runQuery(moveObjectToFolderQuery, [object['id'], PROBLEMATIC_DOCUMENTS_FOLDER_ID], f"Could not move {object['name']} to Problematic Documents folder")
            return False
        time.sleep(wait_interval)
        return runQuery(query_function, inputs, error_message, wait_interval=wait_interval*(2**(max_query_attempts-remaining_attempts)), remaining_attempts=remaining_attempts-1)
    return response

# PRIMARY TWO FUNCTIONS

# Purpose: Converts unprocessed PDFs to markdown and uploads the pdf and markdown files to the PDFs With Markdown Files folder in google drive. The pdf and markdown files are packaged together in a folder with the same name as the pdf.
def createMDsFromPDFs():
    # The first chunk of code fetches all files in the "Unprocessed PDFs" folder (UNPROCESSED_FOLDER_ID). Each file is checked to ensure it is a PDF (via MIME type). If the file is not a PDF, it is logged as an error and moved to the "Problematic Documents" folder (PROBLEMATIC_DOCUMENTS_FOLDER_ID). The function then returns, skipping further processing for that file.
    unprocessed_pdfs = runQuery(getFilesInFolderQuery, [UNPROCESSED_FOLDER_ID], "Query to get files in Unprocessed PDFs folder failed")
    if unprocessed_pdfs != False:
        for unprocessed_pdf in unprocessed_pdfs:
            if (unprocessed_pdf["mimeType"] != "application/pdf"):
                writeToErrorLog(f"File {unprocessed_pdf['name']} in Unprocessed PDFs folder is not a pdf")
                runQuery(moveObjectToFolderQuery, [unprocessed_pdf['id'], PROBLEMATIC_DOCUMENTS_FOLDER_ID], f"Could not move file {unprocessed_pdf['name']} from Unprocessed PDFs folder to Problematic Documents folder")
                return
      
            # This chunk of code first attempts to download the PDF. If successful, it then calls the Marker API to convert the PDF to markdown format. The markdown content is saved to a .md file locally. The file is named after the original PDF by removing the .pdf extension and using the first character ([0:-4][0]) for the filename.
            if runQuery(downloadFileQuery, [unprocessed_pdf['id'], unprocessed_pdf['name']], f"Could not download pdf file {unprocessed_pdf['name']}", put_object_in_problematic_documents_if_fails=True, object=unprocessed_pdf) != False: #In this project, a file's path and name will always be equivalent because I plan to load each file directly into the om_processor folder.
                markdown_content = runQuery(getMarkdownFromPDFQuery, [unprocessed_pdf['name']], f"API could not convert pdf file {unprocessed_pdf['name']} to markdown", put_object_in_problematic_documents_if_fails=True, object=unprocessed_pdf)
                if markdown_content != False:
                    with open(f"{unprocessed_pdf['name'][0:-4]}.md", 'w') as markdown_file:
                        markdown_file.write(markdown_content)

                    # Once the markdown file is created, this chunk creates a new folder (named after the PDF) in the "PDFs with Markdown Files" folder. It then uploads both the markdown file and the PDF into this new folder. If either the markdown upload or the PDF move fails, the wrapper folder is deleted. Finally, both the local markdown and PDF files are removed from the system to free up storage.
                    wrapper_folder = runQuery(createFolderQuery, [unprocessed_pdf['name'][0:-4], PDF_W_MD_FOLDER_ID], f"Could not create folder in PDFs With Markdown Files folder to contain {unprocessed_pdf['name']} and its corresponding markdown file", put_object_in_problematic_documents_if_fails=True, object=unprocessed_pdf)
                    if  wrapper_folder!= False:
                        markdown_file = runQuery(uploadFileQuery, [f"{unprocessed_pdf['name'][0:-4]}.md", wrapper_folder['id']], f"Could not upload markdown file for {unprocessed_pdf['name']} to wrapper folder in PDFs With Markdown Files folder", put_object_in_problematic_documents_if_fails=True, object=unprocessed_pdf)
                        if markdown_file != False:
                            if runQuery(moveObjectToFolderQuery, [unprocessed_pdf['id'], wrapper_folder['id']], f"Could not move pdf {unprocessed_pdf['name']} from Unprocessed PDFs folder to wrapper folder in PDFs With Markdown Files folder", put_object_in_problematic_documents_if_fails=True, object=unprocessed_pdf) == False:
                                runQuery(moveObjectToTrashQuery, [wrapper_folder['id']], f"Could not delete folder {wrapper_folder['name']}")
                    os.remove(f"{unprocessed_pdf['name'][0:-4]}.md")
                os.remove(unprocessed_pdf['name'])

# Purpose: Takes the pdf and markdown files, extracts real estate data from them, and then uploads that data to a google spreadsheet
def pdf_and_md_to_sheets():
    # This chunk reads instructions from a text file containing instructions for ChatGPT on how to extract data from pdf and markdown file pairs and retrieves the list of folders in the"PDFs with Markdown Files folder. It iterates through each folder to ensure they are indeed folders (by checking MIME type). If any item is not a folder, it is logged and moved to the Problematic Documents folder.
    with open(INSTRUCTIONS_FILE_PATH, 'r') as f:
        instructions = f.read()
    pdf_and_md_pair_folders = runQuery(getFilesInFolderQuery, [PDF_W_MD_FOLDER_ID], "Unable to get contents of pdf and md pair folder using API")
    if pdf_and_md_pair_folders != False:
        for pdf_and_md_pair_folder in pdf_and_md_pair_folders:
            if pdf_and_md_pair_folder['mimeType'] != 'application/vnd.google-apps.folder':
                writeToErrorLog(f"An element of the PDFs With Markdown Files folder {pdf_and_md_pair_folder['name']} is not a folder")
                if runQuery(moveObjectToFolderQuery, pdf_and_md_pair_folder['id'], PROBLEMATIC_DOCUMENTS_FOLDER_ID) == False:
                    writeToErrorLog(f"Could not move non-folder element {pdf_and_md_pair_folder['name']} of PDFs With Markdown Files folder to Problematic Documents folder")
                break
            print("looking at folder: "+pdf_and_md_pair_folder['name'])
            # This block retrieves the contents of each folder. It looks for both the PDF and the corresponding markdown file within the folder. If either is missing, the folder is flagged as problematic. The code distinguishes between the PDF and markdown file by their MIME types.
            pdf_and_md_pair_folder_contents = runQuery(getFilesInFolderQuery, [pdf_and_md_pair_folder['id']], f"Could not get contents of folder {pdf_and_md_pair_folder['name']}", put_object_in_problematic_documents_if_fails=True, object=pdf_and_md_pair_folder)
            if pdf_and_md_pair_folder_contents != False:
                pdf_file = False
                markdown_file = False
                for file in pdf_and_md_pair_folder_contents:
                    if file['mimeType'] == 'application/pdf':
                        pdf_file = file
                    elif file['mimeType'] == 'text/markdown':
                        markdown_file = file
                if (pdf_file == False) or (markdown_file == False):
                    writeToErrorLog(f"Element of PDFs With Markdown Files folder {pdf_and_md_pair_folder['name']} did not contain both a pdf and a md file")
                    runQuery(moveObjectToFolderQuery, [pdf_and_md_pair_folder['id'], PROBLEMATIC_DOCUMENTS_FOLDER_ID], f"Could not move folder {pdf_and_md_pair_folder['name']} to Problematic Documents folder")
                    break
                print("downloading: "+pdf_file['name']+" and "+ markdown_file['name'])
                # In this chunk, the PDF and markdown files are downloaded and processed. The PDF text is extracted using the PdfReader, and the markdown file is read as plain text. After extraction, both files are deleted from the local system.
                if (runQuery(downloadFileQuery, [pdf_file['id'], pdf_file['name']], f"Could not download pdf file {pdf_file['name']} from PDFs With Markdown Files folder", put_object_in_problematic_documents_if_fails=True, object=pdf_and_md_pair_folder) != False): 
                    if runQuery(downloadFileQuery, [markdown_file['id'], markdown_file['name']], f"Could not download markdown file {markdown_file['name']} from PDFs With Markdown Files folder", put_object_in_problematic_documents_if_fails=True, object=pdf_and_md_pair_folder) != False:
                        pdf_text = ""
                        with open(pdf_file['name'], 'rb') as file:
                                reader = PdfReader(file)
                                for page in reader.pages:
                                    pdf_text += page.extract_text()
                        os.remove(pdf_file['name'])
                        with open(markdown_file['name'], 'r') as f:
                            markdown_text = f.read()
                        os.remove(markdown_file['name'])
                        print("querying openai api...")
                        # This chunk formats a prompt with the instructions, extracted PDF text, and markdown content. The prompt is then sent to GPT-4o via an API call (chatGPT4oQuery) to extract real estate data. The response is evaluated (converted from a string to a Python dictionary), which contains the extracted data.
                        prompt = f"#INSTRUCTIONS\n\n{instructions}\n\n#PDF TEXT:\n\n{pdf_text}\n\n#MARKDOWN TEXT:\n\n{markdown_text}"
                        response = runQuery(chatGPT4oQuery, [prompt, RESPONSE_FORMAT], f"Could not get real estate data from OpenAI for pdf {pdf_file['name']} and md {markdown_file['name']}", put_object_in_problematic_documents_if_fails=True, object=pdf_and_md_pair_folder)
                        if response != False:
                            real_estate_data = eval(response.choices[0].message.content)
                            print("formatting openai's response")
                            # This chunk reformats the extracted real estate data for spreadsheet insertion. It converts fields like postal codes from individual digits into a complete code and capitalizes names like property names and owners. It also replaces any missing or invalid values with blank strings (""). Finally, a timestamp is added to track when the data was entered. The time stamp is in UTC.
                            for key in real_estate_data:
                                if (((key != "parking_spaces") and (real_estate_data[key] == 0)) or (real_estate_data[key] in BLANK_VALUES)):
                                    real_estate_data[key] = ""
                                if (key == "postal_code"):
                                    print("postal code: "+str(real_estate_data[key].values()))
                                    digit_list = [*real_estate_data[key]]
                                    postal_code = "".join(digit_list)
                                    for blank_value in BLANK_VALUES: #I use parcel.contains("NA") instead of parcel == "NA" because 
                                        if blank_value in postal_code:
                                            postal_code = ""
                                    real_estate_data[key] = postal_code
                                if (key == "parcel"):
                                    print("parcel: "+str(real_estate_data[key]))
                                    parcel = "".join([e['value'] for e in real_estate_data[key]])
                                    if "NA" in parcel: #I use parcel.contains("NA") instead of parcel == "NA" because of the way the RealEstateData response format is structured
                                        parcel = ""
                                    real_estate_data[key] = parcel
                                if (key in ["property_name", "owners", "city", "county", "tenants", "seller", "sellers_broker"]):
                                    words_list = real_estate_data[key].split(" ")
                                    for word in words_list:
                                        word = word.capitalize()
                                    real_estate_data[key] = " ".join(words_list)

                            real_estate_data.update({"timeDataEntered": str(datetime.now(timezone.utc).timestamp())})
                            print("entering data")
                            # This chunk finds the first empty row in a Google Sheets spreadsheet using getFirstEmptySpreadsheetRowQuery, ensuring data isn't overwritten. If the row is found, the extracted real estate data is written into that row using writeListToSpreadsheetRowQuery. If that operation succeeds, then the folder containing the pdf and markdown file is moved to the PDFs Entered Into Spreadsheet folder. All 3 operations are wrapped in runQuery, which handles retries and error logging in case of failure, ensuring that problematic documents are flagged and moved if necessary.
                            first_empty_row = runQuery(getFirstEmptySpreadsheetRowQuery, [SPREADSHEET_ID], f"Could not get first empty row in spreadsheet")
                            if first_empty_row != False:
                                if runQuery(writeListToSpreadsheetRowQuery, [SPREADSHEET_ID, first_empty_row, real_estate_data], f"Could not write real estate data to spreadsheet", put_object_in_problematic_documents_if_fails=True, object=pdf_and_md_pair_folder) != False:
                                    runQuery(moveObjectToFolderQuery, [pdf_and_md_pair_folder['id'], PDFS_AND_MD_IN_SHEETS_FOLDER_ID],  f"Could not move pdf and markdown pair folder into PDFs Entered Into Spreadsheet Folder after data was written to the spreadsheet", put_object_in_problematic_documents_if_fails=True, object=pdf_and_md_pair_folder)



def main():
   #The code run in main is split into two separate functions so that half of the program can be run at a time for debugging purposes
   createMDsFromPDFs()
   pdf_and_md_to_sheets()

    

if __name__ == '__main__':
    main()