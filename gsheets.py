from apiclient import discovery
from httplib2 import Http
from oauth2client import file, client, tools
from settings import Settings

class GSheets():
   
    def __init__(self):
        """Initialize the spreadsheet"""

        #self.gsheets is used in all of the update statements throughout
        self.gsheets = self.connect()


    def connect(self):
        """Authorize access and connect to google sheets.
           If this is your first time running on the machine, you may be prompted to authorize via a web prompt
           client_secrect is downloaded from authorizing the google sheets development API.  You also will need
           enable the sheets api to accessing your files"""
        self.tSettings = Settings()
        self.SCOPES = 'https://www.googleapis.com/auth/spreadsheets'
        self.store = file.Storage('storage.json')
        self.creds = self.store.get()

        if not self.creds or self.creds.invalid:
            self.flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
            self.flow = client.flow_from_clientsecrets('client_secret.json',self.SCOPES)
            self.creds = tools.run_flow(self.flow, self.store, self.flags)

        self.SHEETS = discovery.build('sheets', 'v4', http = self.creds.authorize(Http()))

        return self.SHEETS

    def getSheetIdByTitle(self,spreadSheetId, sheetTitle):

        self.res = self.gsheets.spreadsheets().get(spreadsheetId = spreadSheetId).execute()

        for self.sheetinfo in self.res['sheets']:
            if sheetTitle == self.sheetinfo['properties']['title']:
                self.sheetId = self.sheetinfo['properties']['sheetId']
                break
            else:
                self.sheetId = None
        return self.sheetId



    def createSheet(self, spreadSheetId, sheetTitle):

        self.data = {
         "requests": [{
            "addSheet": {
               "properties": {
                   "title": sheetTitle,
                   "gridProperties": {
                     "rowCount": self.tSettings.BULK_INSERT_ROW_COUNT,
                     "columnCount": self.tSettings.SHEET_NUM_COLS
                   }
               }
            }
         },

        ],
        }

        try:
            self.res = self.gsheets.spreadsheets().batchUpdate(spreadsheetId = spreadSheetId, body = self.data).execute()
        except:
            print("Problem creating sheet {}, it may already exist".format(sheetTitle))

    def insertHeader(self, SHEETS, **header):
        self.sheetId = getSheetIdByTitle(tSettings.SHEET)
        #sheetId = getSheetIdByTitle(sheetTitle)
        #keeping this seperate from inserted values, even though I can pull this from the database, because
        #I might want to change the data type for fields
        #insertOneRecord(sheetId,"LOCATION_ID", "WEATHER_READING_TIME", "TEMPERATURE", "HUMIDITY")


    def deleteSheet(self,spreadSheetId, sheetTitle):

        #self.spreadSheetId
        self.sheetId = self.getSheetIdByTitle(spreadSheetId, sheetTitle)

        self.data = {
          "requests": [
            {
              "deleteSheet": {
              "sheetId": self.sheetId
              }
            }
          ]
        }

        try:
            self.res = self.gsheets.spreadsheets().batchUpdate(spreadsheetId = spreadSheetId, body = self.data).execute()
        except:
            print("Sheet {} does not exist, or there is an error deleting, continuing".format(sheetTitle))

    def bulkInsertRecord(self, spreadsheetId, sheetTitle, data):
      
        self.gsheets.spreadsheets().values().update(spreadsheetId=spreadsheetId, range="{0}!A2".format(sheetTitle), body=data, valueInputOption='RAW').execute()

    def insertRecord(self,spreadsheetId, sheetId, *args):

        self.data = {"requests": [
           {
             "appendCells": {
               "sheetId": sheetId,
               "rows": [  {"values": [
                   #{"userEnteredValue": {"stringValue": example1}},
                   #{"userEnteredValue": {"stringValue": example2}},
                   #{"userEnteredValue": {"stringValue": example3}},
                   #{"userEnteredValue": {"stringValue": example4}}

                  ]}],
               "fields" : "userEnteredValue"
              }
            }
            ]
          }

        for item_number, column_value in enumerate(args):
            for batchUpdate in self.data["requests"]:
                for row in batchUpdate["appendCells"]["rows"]:
                    row["values"].append({'userEnteredValue': {'stringValue': str(column_value)}})


        self.res = self.gsheets.spreadsheets().batchUpdate(spreadsheetId = spreadsheetId,body = self.data).execute()

