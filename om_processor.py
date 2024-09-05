import os
import io
import openai
import markdown
import time
import requests
from googleapiclient.discovery import build
from datetime import datetime, timezone
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from google.oauth2.service_account import Credentials
from PyPDF2 import PdfReader
from RealEstateExtraction import RealEstateExtraction

#//////////////////////////////////////////CONSTANTS\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\

#Drive
SHARED_DRIVE_ID = '0APHQBI6riR7qUk9PVA'
UNPROCESSED_FOLDER_ID = "1WCQJM7uNFe3yImoQW7ywwfd6jJQQDxTI"
PDF_W_MD_FOLDER_ID = "1WJsr5hhnWb-u0m5KG3AQy5EJ62UsmH9w"
PDFS_AND_MD_IN_SHEETS_FOLDER_ID = "1WEHtpgoxTHc2QrWrtJYZbdjLxDn3No8W"
PROBLEMATIC_DOCUMENTS_FOLDER_ID = "1-RuX8ry5BdplYDHj18oElyloMYZM-dj5"
SPREADSHEET_ID = "1aCsoLTBYxra3mtyGXvJoPnElOdkTOHH9pM5klz_HKU8"
SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = 'Resources/EsmeesServiceAccountKey.json'
CREDS = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
DRIVE_SERVICE = build('drive', 'v3', credentials=CREDS)
SHEETS_SERVICE = build('sheets', 'v4', credentials=CREDS)

#Marker
MARKER_API_KEY = "NpujIN2fzkNYZQYbCN2X-4QpQMe70dy7HKv_onCtM4I"
MARKER_URL = "https://www.datalab.to/api/v1/marker"

#OpenAI
OPENAI_API_KEY = "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"
openai.api_key = OPENAI_API_KEY

#Local
INSTRUCTIONS_FILE_PATH = 'Resources/instructions.txt'
ERROR_LOG_PATH = "Resources/errors.log"

#//////////////////////////////////////////HELPER FUNCTIONS\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\

def writeToErrorLog(error):
    errorLog = open(ERROR_LOG_PATH, "a")
    errorLog.write(f"ERROR: {error} \n")
    errorLog.write("TIME ERROR OCURRED (UTC): "+str(datetime.now(timezone.utc))+"\n\n")
    errorLog.close()

#Handles exceptions for each API Query
def runQuery(query_function, inputs, max_query_attempts=6, wait_interval=2, remaining_attempts=None):
    if remaining_attempts is None:
        remaining_attempts = max_query_attempts
    try:
        response = query_function(*inputs)
    except Exception as e:
        writeToErrorLog(e)
        if remaining_attempts <= 0:
            return False
        time.sleep(wait_interval)
        return runQuery(query_function, inputs, wait_interval=wait_interval*(2**(max_query_attempts-remaining_attempts)), waitremainingAttempts=remaining_attempts-1)
    return response

#WRAPPER FUNCTIONS FOR API QUERIES

def getFilesInFolderQuery(folder_id):
    query = f"'{folder_id}' in parents"
    results = DRIVE_SERVICE.files().list(q=query, includeItemsFromAllDrives=True, supportsAllDrives=True, corpora="drive", driveId=SHARED_DRIVE_ID).execute()
    return results.get('files', [])

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

def uploadFileQuery(file_path, folder_id):
    file_metadata = {'name': os.path.basename(file_path), 'parents': [folder_id]}
    media = MediaFileUpload(file_path, mimetype='application/octet-stream')
    uploaded_file = DRIVE_SERVICE.files().create(body=file_metadata, media_body=media, fields='id', supportsAllDrives=True).execute()
    return uploaded_file.get('id')

def moveObjectToFolderQuery(object_id, new_folder_id):
    file = DRIVE_SERVICE.files().get(fileId=object_id, fields="parents", supportsAllDrives=True).execute()
    previous_parents = ",".join(file.get("parents"))
    DRIVE_SERVICE.files().update(fileId=object_id, addParents=new_folder_id, removeParents=previous_parents, fields="id, parents", supportsAllDrives=True).execute()

def moveObjectToTrashQuery(object_id):
    DRIVE_SERVICE.files().update(fileId=object_id, body={'trashed': True}).execute()

def createFolderQuery(folder_name, parent_folder_id):
    folder_metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [parent_folder_id]}
    folder = DRIVE_SERVICE.files().create(body=folder_metadata, fields='id', supportsAllDrives=True).execute()
    return folder.get('id')

def getMarkdownFromPDFQuery(pdf_path):
    url = MARKER_URL
    headers = {"X-Api-Key": MARKER_API_KEY}
    form_data = {'file': ('document.pdf', open(pdf_path, 'rb'), 'application/pdf'), "langs": (None, "en"), "force_ocr": (None, False), "paginate": (None, False)}

    response = requests.post(url, files=form_data, headers=headers)
    data = response.json()

    return data.get("markdown", "")

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
    utcTimeStamp = datetime.now(timezone.utc).timestamp()
    result.update({"timeDataEntered": str(utcTimeStamp)})
    print()

def get_first_empty_spreadsheet_row_function(spreadsheet_id):
    data = SHEETS_SERVICE.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range="A:A").execute()
    values = data.get('values', [])
    return len(values)+1

def write_list_to_spreadsheet_row_function(spreadsheet_id, row, data):
    #prepare body
    body = {'values': [list(data.values())]}

    #insert data
    SHEETS_SERVICE.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=str(row)+":"+str(row),
        valueInputOption="USER_ENTERED",
        body=body
    ).execute()

def askChatGPTQuestionFunction(question, responseFormat):
    return openai.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": question}
        ], 
        response_format=responseFormat
    )
def pdf_to_md():
    files = runQuery(getFilesInFolderQuery, [UNPROCESSED_FOLDER_ID])
    if files == False:
        writeToErrorLog("Query to get files in unprocessed pdf folder failed")
    else:
        for file in files:
            pdf_file_id = file['id']
            pdf_file_name = file['name']
            local_pdf_path = pdf_file_name

            if (file["mimeType"] != "application/pdf"):
                writeToErrorLog(f"File {pdf_file_name} in unprocessed pdf folder is not a pdf")

                if runQuery(moveObjectToFolderQuery, [pdf_file_id, PROBLEMATIC_DOCUMENTS_FOLDER_ID]) == False:
                    writeToErrorLog(f"Could not move file {pdf_file_name} from unprocessed pdf folder to problematic documents folder")
            else:        
                # Download the PDF file
                if runQuery(downloadFileQuery, [pdf_file_id, local_pdf_path]) == False:
                    writeToErrorLog(f"Could not download pdf file {pdf_file_name}")

                    if runQuery(moveObjectToFolderQuery, [pdf_file_id, PROBLEMATIC_DOCUMENTS_FOLDER_ID]) == False:
                        writeToErrorLog(f"Could not move file {pdf_file_name} in unprocessed pdf folder to problematic documents folder")
                else:
                    # Convert the PDF to Markdown
                    markdown_content = runQuery(getMarkdownFromPDFQuery, [local_pdf_path])
                    if markdown_content == False:
                        writeToErrorLog(f"API could not convert pdf file {pdf_file_name} to markdown")

                        if runQuery(moveObjectToFolderQuery, [pdf_file_id, PROBLEMATIC_DOCUMENTS_FOLDER_ID])==False:
                            writeToErrorLog(f"Could not move pdf {pdf_file_name} from unprocessed pdf folder to problematic documents folder")
                    else:
                        # Save the markdown content to a file
                        markdown_file_name = os.path.splitext(pdf_file_name)[0] + ".md"
                        with open(markdown_file_name, 'w') as md_file:
                            md_file.write(markdown_content)
                        #create a folder to house the markdown and pdf files in
                        wrapper_folder_name = pdf_file_name[0:-4]
                        wrapper_folder_id = runQuery(createFolderQuery, [wrapper_folder_name, PDF_W_MD_FOLDER_ID])
                        if wrapper_folder_id == False:
                            writeToErrorLog(f"Could not create folder in pdfs with markdown files folder to contain {pdf_file_name} and {markdown_file_name}")
                            if runQuery(moveObjectToFolderQuery, [file['id'], PROBLEMATIC_DOCUMENTS_FOLDER_ID]) == False:
                                writeToErrorLog(f"Could not move pdf {pdf_file_name} from unprocessed pdf folder to problematic documents folder")
                        else:
                            # Upload the markdown file to the new location
                            markdown_file_id = runQuery(uploadFileQuery, [markdown_file_name, wrapper_folder_id])
                            if markdown_file_id == False:
                                writeToErrorLog(f"Could not upload {markdown_file_name} to wrapper folder in pdf with markdown folder")
                                if runQuery(moveObjectToTrashQuery, [wrapper_folder_id]) == False:
                                        writeToErrorLog(f"Could not delete folder {wrapper_folder_name}")
                            else:
                                # Move the original PDF file to the new location
                                if runQuery(moveObjectToFolderQuery, [pdf_file_id, wrapper_folder_id]) == False:
                                    writeToErrorLog(f"Could not move pdf {pdf_file_name} from unprocessed pdf folder to wrapper folder in pdf with markdown folder")
                                    if runQuery(moveObjectToTrashQuery, [wrapper_folder_id]) == False:
                                        writeToErrorLog(f"Could not delete folder {wrapper_folder_name}")
                                    if runQuery(moveObjectToFolderQuery, [file['id'], PROBLEMATIC_DOCUMENTS_FOLDER_ID]) == False:
                                        writeToErrorLog(f"Could not move pdf {pdf_file_name} from unprocessed pdf folder to problematic documents folder")
                        # Clean up md file if it was sucessfully downloaded
                        os.remove(markdown_file_name)
                    # Clean up pdf file if it was sucessfully downloaded
                    os.remove(local_pdf_path)

def pdf_and_md_to_sheets():
    instructions = extract_text_from_instructions(INSTRUCTIONS_FILE_PATH)  # Load the instructions from the text file
    folders = runQuery(getFilesInFolderQuery, [PDF_W_MD_FOLDER_ID])
    if folders == False:
        writeToErrorLog("Unable to get contents of pdf with md folder using  API")
    else:
        for folder in folders:
            folderName = folder['name']

            if folder['mimeType'] != 'application/vnd.google-apps.folder':
                writeToErrorLog(f"An element of the pdf with md folder {folderName} is not a folder")
                if runQuery(moveObjectToFolderQuery, folder['id'], PROBLEMATIC_DOCUMENTS_FOLDER_ID) == False:
                    writeToErrorLog(f"Could not move non-folder element {folder_name} of pdf w md folder to problematic documents folder")
            else:
                files = runQuery(getFilesInFolderQuery, [folder['id']])
                if files == False:
                    writeToErrorLog(f"Could not get list of files in folder {folderName}")
                    if runQuery(moveObjectToFolderQuery, folder['id'], PROBLEMATIC_DOCUMENTS_FOLDER_ID) == False:
                        writeToErrorLog(f"Could not move folder we could not get list of files for {folderName} to problematic documents folder")
                else:
                    pdf_file = False
                    markdown_file = False

                    for file in files:
                        if file['mimeType'] == 'application/pdf':
                            pdf_file = file
                        elif file['mimeType'] == 'text/markdown':
                            markdown_file = file

                    if (pdf_file == False) or (markdown_file == False):
                        writeToErrorLog(f"Element of pdf with md folder {folderName} did not contain both a pdf and a md file")
                        if runQuery(moveObjectToFolderQuery, [folder['id'], PROBLEMATIC_DOCUMENTS_FOLDER_ID]) == False:
                            writeToErrorLog(f"Could not move folder that did not contain both a pdf and a md file {folderName} to problematic documents folder")
                    else:
                        pdf_file_name = pdf_file['name']
                        markdown_file_name = markdown_file['name']

                        if (runQuery(downloadFileQuery, [pdf_file['id'], pdf_file_name]) == False): 
                            writeToErrorLog(f"Could not download both pdf file {pdf_file_name}")
                            if runQuery(moveObjectToFolderQuery, [file['id'], PROBLEMATIC_DOCUMENTS_FOLDER_ID]) == False:
                                writeToErrorLog(f"Could not move folder {folderName} to problematic documents folder")
                        elif runQuery(downloadFileQuery, [markdown_file['id'], markdown_file_name]) == False:
                            if runQuery(moveObjectToFolderQuery, [files['id'], PROBLEMATIC_DOCUMENTS_FOLDER_ID]) == False:
                                writeToErrorLog(f"Could not move folder {folderName} to problematic documents folder")
                        else:
                            pdf_text = extract_text_from_pdf(pdf_file_name)
                            os.remove(pdf_file['name'])

                            markdown_text = extract_text_from_markdown(markdown_file_name)
                            os.remove(markdown_file_name)

                            prompt = f"#INSTRUCTIONS\n\n{instructions}\n\n#PDF TEXT:\n\n{pdf_text}\n\n#MARKDOWN TEXT:\n\n{markdown_text}"

                            response = runQuery(askChatGPTQuestionFunction, [prompt, RealEstateExtraction])
                            if response == False:
                                writeToErrorLog(f"Could not get real estate data from OpenAI for pdf {pdf_file_name} and md {markdown_file_name}")
                                if runQuery(moveObjectToFolderQuery, [files['id'], PROBLEMATIC_DOCUMENTS_FOLDER_ID]) == False:
                                    writeToErrorLog(f"Could not move folder {folderName} to problematic documents folder")
                            else:
                                realEstateData = eval(response.choices[0].message.content)
                                reformatResult(realEstateData)

                                first_empty_row = runQuery(get_first_empty_spreadsheet_row_function, [SPREADSHEET_ID])
                                if first_empty_row == False:
                                    writeToErrorLog(f"Could not get first empty row in spreadsheet")
                                elif runQuery(write_list_to_spreadsheet_row_function, [SPREADSHEET_ID, first_empty_row, realEstateData]) == False: 
                                    writeToErrorLog(f"Could not write real estate data to spreadsheet")
                                else: 
                                    if runQuery(moveObjectToFolderQuery, [folder['id'], PDFS_AND_MD_IN_SHEETS_FOLDER_ID]) == False:
                                        writeToErrorLog(f"Could not move {folderName} to pdfs and md in sheets folder")


def main():
   pdf_to_md()
   pdf_and_md_to_sheets()

    

if __name__ == '__main__':
    main()