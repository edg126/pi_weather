###
###   Python 2.7
###   This Process takes readings from a weather temperature / humidity sensor on the raspberry pi
###   And inserts records into a mysql database, and also into google sheets
###   Because google sheets has limited amount of values it can hold, it resets every 90K, and preloads
###   the data with averaged data from mysql

#improvements
#instead of pulling NOAA time every hour, attempt to pull around the time suggested in xml
#before creating a new  noaa_weather_reading_id entry, check to see if the observation time is the same as the new reading.
#   if so, then continue to use the old one.
#wait until google fixes their bug with their API that allows different userformatting for bulk vs append

from __future__ import print_function
import argparse
import MySQLdb
import time
import datetime
import Adafruit_DHT
import socket #used to get hostname entry into database
import sys 
import ConfigParser

from settings import Settings
from gsheets import GSheets

import urllib2 #used for noaa readings
import xml.etree.ElementTree as ET #parse xml from noaa readings

import email.utils #used for noaa parsedate

tSettings = Settings()

def main():
    #thermostatId = thermostat()

    #settings
    spreadsheetId = tSettings.SPREADSHEET_ID
    sheetTitle = tSettings.SHEET_TITLE

    #initialize and connect to google sheets
    ss = GSheets()

    #initialize and connect to database
    dbConnect()

    #prepare sheets environment
    prepareSheetsEnv(ss, spreadsheetId, sheetTitle)
    
    #get the sheet id, since this can change with each delete sheet
    sheetId = ss.getSheetIdByTitle(spreadsheetId, sheetTitle)
      
    #welcome screen
    printStartScreen()

    #since location won't chang while running, get this only once
    location = locationOptions()

    approachingMaxCols = 0 #if this number gets to 50K in case our sheet runs for a long time, then we need to reset google sheets
    # taking the rounded hourly values, cutting rows down by a factor of 12.

    #get the initial noaa reading and time
    noaa_weather_reading_id = noaa()
    last_noaa_reading = datetime.datetime.now()
  


    while True:
        (temperature, humidity, host, weather_time) = collectData()

        #check the time, if it's gone past the hour, pull again
        curr_reading = datetime.datetime.now()
        diff = curr_reading - last_noaa_reading
        minutesFromLastNoaaReading = diff.total_seconds() / 60


        #print('total minutes from last noaa reading: {}'.format(minutesFromLastNoaaReading))
        if minutesFromLastNoaaReading >= 60.0: 
            noaa_weather_reading_id = noaa()
            last_noaa_reading = datetime.datetime.now()            

        print('Temperature: {0:0.1f} F'.format(temperature))
        print('Humidity:    {0:0.1f} %'.format(humidity))

        sqlInsert = """insert into weather_reading
               (location_id, weather_reading_time, created_by, temperature, humidity, noaa_weather_reading_id)
                values (%s,%s,%s,%s,%s,%s)"""

        sqlValues = [location, weather_time, host, temperature, humidity, noaa_weather_reading_id]


        weatherReadingId = insertSQLGetId(sqlInsert, sqlValues)
        ss.insertRecord(spreadsheetId, sheetId, location, weather_time, temperature, humidity)

        approachingMaxCols+=1
        time.sleep(tSettings.FREQUENCY_SECONDS) 


def prepareSheetsEnv(authInstance, spreadsheetId, sheetTitle):
    print("Preparing Google Sheets environment...")

    print("--Deleting sheet")
    authInstance.deleteSheet(spreadsheetId, sheetTitle)    
    print("--Creating new sheet")
    authInstance.createSheet(spreadsheetId, sheetTitle)
    sheetId = authInstance.getSheetIdByTitle(spreadsheetId, sheetTitle)
    print("--Inserting Header")
    authInstance.insertRecord(spreadsheetId, sheetId, "LOCATION_ID", "WEATHER_READING_TIME", "TEMPERATURE", "HUMIDITY")
    print("--Querying historic data from database")
    resultsToPopulate = queryWeatherPopulationSql()
    print("--Bulk inserting records from database")
    #sort the list asc, so the order makes sense when we start populating.  It is in reverse order because we
    #wanted pull the most recent 40K records from the database
    resultsToPopulate = sorted(resultsToPopulate, key=lambda x:datetime.datetime.strptime(x[1],'%Y-%m-%d %H:%M:%S'))
    #populate google sheets with summary data from mysql
    data = {"values": [list(row) for row in resultsToPopulate]}
    authInstance.bulkInsertRecord(spreadsheetId, sheetTitle, data)
    #SHEETS.spreadsheets().values().update(spreadsheetId=SPREADSHEET_ID, range="{0}!A2".format(SHEET), body=data, valueInputOption='RAW').execute()

    print("\nGoogle sheet data is ready!")
    #return sheetId



def dbConnect():
   db = MySQLdb.Connection(host=tSettings.SQLHOST,  
                     user=tSettings.SQLUSER,        
                     passwd=tSettings.SQLPW,  
                     db=tSettings.SQLDB       
                        )
   return db

def queryWeatherPopulationSql():

    db = dbConnect()
    cur = db.cursor()

    #note: google sheets needs results as a list of lists, mysqldb does it as tuples, so need list converstions.  Also mysqldb
    #imports dates into python chunks that sheets can't figure out.  For now, convert to char 


    #take the average by hour, this will cut back on the amount of data overtime written to google sheets.  will allow for 4.5 years
    # worth of data.
    #only takes 40,000 rows because google sheets has a limit of 400,000 on their grid (cells * rows).
    #cast(DATE_FORMAT(wr.weather_reading_time, "%Y-%m-%d %H:00:00") as char)
    sql = """SELECT wr.location_id LOCATION_ID,
             cast(DATE_FORMAT(wr.weather_reading_time, "%Y-%m-%d %H:00:00") as char) WEATHER_READING_TIME,
             round(avg(wr.temperature),2) TEMPERATURE, 
             round(avg(wr.humidity),2)HUMIDITY
             FROM WEATHER.weather_reading wr
             WHERE not(ifnull(temperature,0) <=0 OR ifnull(humidity,0) <=0) 
             GROUP BY wr.location_id, cast(DATE_FORMAT(wr.weather_reading_time, "%Y-%m-%d %H:00:00") as char)
             ORDER BY wr.weather_reading_time desc limit 40000
         """

    cur.execute(sql)

    results = list(cur.fetchall())

    cur.close()
    db.close()

    return results


def printStartScreen():
    print('Logging sensor measurements every {0} seconds.'.format(tSettings.FREQUENCY_SECONDS))
    print('Press Ctrl-C to quit.')
    print("Enter your location\n")



def locationOptions():

    db = dbConnect()
    cur = db.cursor()

    print("\n\nEnter a location:\n0 NO_LOCATION")
    cur.execute("SELECT location_id, location_desc FROM location")
    for row in cur.fetchall():
        print(row[0],row[1])

    cur.close()
    db.close()

    location = raw_input('> ')
    return location


def getTimestamp():
    ts = time.time()
    st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    return st

def getHostname():
    hn = socket.gethostname()
    return hn


def getWeatherReading():
    # Type of sensor, can be Adafruit_DHT.DHT11, Adafruit_DHT.DHT22, or Adafruit_DHT.AM2302.
    DHT_TYPE = Adafruit_DHT.DHT22
    # Example of sensor connected to Raspberry Pi pin 23
    #DHT_PIN  = 23
    DHT_PIN = 4
    # Example of sensor connected to Beaglebone Black pin P8_11
    #DHT_PIN  = 'P8_11'

    # Attempt to get sensor reading.
    humidity, temperature = Adafruit_DHT.read(DHT_TYPE, DHT_PIN)

    #print('get_weather_reading: ', humidity, temperature)
    if temperature is not None and humidity is not None:
        temperature = (temperature * 1.8) + 32  #convert C to F
        temperature = round(temperature, 2)
        humidity = round(humidity, 2)
    return (temperature, humidity)


def collectData():
    host = getHostname()
    fail_counter = 0

    while fail_counter < 20:
        (temperature, humidity) = getWeatherReading()
        ts = getTimestamp()
        # Skip to the next reading if a valid measurement couldn't be taken.
        # This might happen if the CPU is under a lot of load and the sensor
        # can't be reliably read (timing is critical to read the sensor).

        if humidity is None or temperature is None:
            print('Error in temp or humidity reading.')
            time.sleep(5)
            fail_counter+=1
            continue
        if humidity is not None and temperature is not None:
            break


    if humidity is None or temperature is None:
        raise Exception('Too many failures attempting to read temperature, exiting.')
        exit()

    #print('HT:',temperature, humidity, host, ts)
    return(temperature, humidity, host, ts)



def insertSQLGetId(sqlInsertQuery, valueList):
    #values used to avoid sql injection, and allow for None to be inserted as null
    db = dbConnect()
    cur = db.cursor()

    try:
       cur.execute(sqlInsertQuery, valueList)
       db.commit()
    except:
       print("error inserting into sql")
       db.rollback()

    lastRowId = cur.lastrowid
    cur.close()
    db.close()
 
    return lastRowId


def thermostat():
    #This is not currently being used.  We adjust the heat during the winter and I don't trust myself to adequately update the database
    print("Enter current thermostat reading: ", end = "")
    thermostatTemperature = input()
    insertSQL = "insert into thermostat (temperature) values (%s)"
    insertValues = [thermostatTemperature]
        
    thermostatId = insertSQLGetId(insertSQL, insertValues)

    return thermostatId

def noaa():

    noaa_url = "http://w1.weather.gov/xml/current_obs/display.php?stid=" + tSettings.STATION_ID
    #url = urllib2.urlopen(noaa_url)
    url = urllib2.urlopen(noaa_url)
    xml_data = url.read()


    tree = ET.fromstring(xml_data)
    noaa = dict((child.tag, child.text) for child in tree)


    #assumes that everything will be local, and can ignore the timezone adjustment
    raw = noaa.get('observation_time_rfc822')
    date_tuple = email.utils.parsedate_tz(raw)
    date_stamp = email.utils.mktime_tz(date_tuple)
    observation_time = datetime.datetime.fromtimestamp(date_stamp)

    insertSQLCode = """insert into noaa_weather_reading
           (LOCATION,STATION,LATITUDE,LONGITUDE,OBSERVATION_TIME,
           WEATHER,TEMPERATURE,RELATIVE_HUMIDITY,WIND_DIR,WIND_DEGREES,
           WIND_WPH,WIND_GUST_MPH,PRESSURE_IN,DEWPOINT,HEAT_INDEX,
           VISIBILITY) values (%s, %s, %s, %s, %s,
                                %s, %s, %s, %s, %s, 
                                %s, %s, %s, %s, %s,
                                %s)
           """

    valueList = [noaa.get('location', None), noaa.get('station_id', None), noaa.get('latitude', None), noaa.get('longitude', None), observation_time,
              noaa.get('weather', None), noaa.get('temp_f', None), noaa.get('relative_humidity', None), noaa.get('wind_dir', None), noaa.get('wind_degrees', None),
              noaa.get('wind_mph',None), noaa.get('wind_gust_mph',None), noaa.get('pressure_in',None), noaa.get('dewpoint_f',None), noaa.get('heat_index_f',None),
              noaa.get('visibility_mi', None)]

    noaa_weather_reading_id = insertSQLGetId(insertSQLCode, valueList)

    return noaa_weather_reading_id


if __name__ == "__main__": main()
