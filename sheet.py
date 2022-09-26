import os.path
import pickle
from typing import Optional

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource


class Sheet:
    # If modifying these scopes, delete the file token.pickle.
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    # The ID and range of a sample spreadsheet.
    sheet_id = '1G_WEIE6aw14JjvCnvpVhYuCI_gJPQciKN4oYcFDXjcc'
    header_offset = 3
    SECRETS_FILE = 'credentials.json'

    def __init__(self):
        self.sheet: Optional[Resource] = None

        creds = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.SECRETS_FILE, self.SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        self.sheet = build('sheets', 'v4', credentials=creds).spreadsheets()

    def get(self, cell: str) -> str:
        res = self.sheet.values().get(spreadsheetId=self.sheet_id, range=cell).execute()
        values = res.get("values", [])
        if not values:
            return ""

        return values[0][0]

    def get_floats(self, start: str, end: str) -> [float]:
        vals = self.gets(start, end)
        return [float(v.replace(",", ".")) for v in vals]

    def gets(self, start: str, end: str) -> [str]:
        res = self.sheet.values().get(
            spreadsheetId=self.sheet_id, range=f'{start}:{end}'
        ).execute()
        values = res.get("values", [])
        if not values:
            return []

        return [v[0] if v else "" for v in values]

    def write(self, cell, value):
        body = {"values": [[value]]}
        result = self.sheet.values().update(
            spreadsheetId=self.sheet_id, range=cell,
            valueInputOption='USER_ENTERED', body=body).execute()
        print('{0} cells updated.'.format(result.get('updatedCells')))


def example():
    """Shows basic usage of the Sheets API.
    Prints values from a sample spreadsheet.
    """
    sheet = Sheet()
    value = sheet.get('C9')

    if not value:
        print('No data found.')
    else:
        print(f'{value}')

    sheet.write("E27", "33 Саша пошли делать коктейль")
