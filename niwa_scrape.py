# -*- coding: utf-8 -*-
"""
Created on Wed Apr 18 15:09:02 2018
@author: Sean

Scrapes forecast data from niwa api and put into rds database. Runs through regions of wellington, auckland, christchurch
-schedule as cron job to run daily at 7am NZDT

niwa api access is of form: https://weather.niwa.co.nz/data/hourly/wellington. Data format is json
data is logged to tables named nw_wellington, nw_auckland, nw_christchurch

"""
import requests
import json
import numpy as np
import datetime 
import psycopg2

# webscrape block
class niwaScraper:
    def readurl(self,url):
        # api query
        r=requests.get(url)
        parsed_json = json.loads(r.text)
        
        runTime=parsed_json.get('analysisTime')  # model run time (this is the issued time for the forecast)

        issuedayUTC=datetime.datetime.strptime(runTime, '%Y-%m-%dT%H:%M:%SZ')
        issueday=issuedayUTC+datetime.timedelta(hours=12) # shift to NZST
        issuedaySTR="{:%Y-%m-%d %H:%M:%S}".format(issueday)
        
        # summaries dict has the daily forecast summaries. 
        data_json=parsed_json.get('summaries')
        
        # gets forecast params for every day
        data_all=[]
        for items in data_json:
            forecasttxt = '%s, %s, %s, %s' % (items.get('cloud'),items.get('precipitation'),items.get('windDesc'),items.get('windDirection')) # build text forecast
            forecastdaySTR=items.get('date') # forecasted day
            forecastday=datetime.datetime.strptime(forecastdaySTR, '%Y-%m-%d')
            deltaT=forecastday-issueday.replace(hour=0,minute=0,second=0) # time difference between issue time and forecasted time
            data=[forecastdaySTR,issuedaySTR,deltaT.days,forecasttxt,items.get('rainAmount'),round(items.get('windSpeed')),items.get('maxTemp'),items.get('minTemp')] # all forecast data
            data_all.append(data)    
        
        # returns all the data in an array ready for inserting into table    
        data_all=np.array(data_all)    
        return data_all

# insert in database block
class rdsDB:
    def insertblock(self,tableName,dataC):
        conn = psycopg2.connect("")
        cur = conn.cursor()
        for row in dataC:
            cur.execute("""INSERT INTO %s(forecastday,issueday,delta,forecasttxt,rain,wind,high,low) VALUES ('%s','%s','%s','%s','%s','%s','%s','%s')""" % ('nw_'+tableName,row[0],row[1],row[2],row[3],row[4],row[5],row[6],row[7]))
        conn.commit()
        cur.close()
        conn.close()

# run all block
class doAll:
    def region(self,regionName):        
        k=niwaScraper()
        niwa_url='https://weather.niwa.co.nz/data/hourly/%s' %regionName # 4 day forecast here
        (data)=k.readurl(niwa_url)
        j=rdsDB()
        j.insertblock(regionName,data)
        
        
h=doAll()
h.region('Wellington')
h.region('Christchurch')
h.region('Auckland')

