class Settings():
    """A class to store all settings for the temperature readings"""

    def __init__(self):
        """Initialize the settings"""

        #humidity sensor settings
        #how long ot wait (in seconds) between measurements.
        self.FREQUENCY_SECONDS = 300
        #google drive settings
        #googlesheets allows only 100,000 rows * cols, so when we approach
        #the number below, reset the process to only pull the most recent
        #records from the database
        self.MAX_SHEET_VOL_RESET = 90000
        self.BULK_INSERT_ROW_COUNT = 40000   

        #GOOGLE SHEETS SETTINGS
        #since you can have multiple spreadsheets with the same name
        #we are using the same spreadsheet id instead of creating new ones
        #so files that read from this sheet can always access it.
        self.SPREADSHEET_ID = "long_hashed_string_copied_from_sheets_url"
        self.SPREADSHEET_ID_NAME = "Temperature_Test"
        #on dropping and adding, what would you like the sheet named.
        self.SHEET_TITLE = "test5"
        #number of columns to create on the sheet we are creating
        self.SHEET_NUM_COLS = 4

        #database settings
        self.SQLHOST = "host"
        self.SQLUSER = "user"
        self.SQLPW = "pw"
        self.SQLDB = "database"

       
