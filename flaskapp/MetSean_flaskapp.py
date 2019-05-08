#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Wed Jul 11 18:01:45 2018
@author: Sean

Metsean flaskapp

renders pages:
    1. Home page
    2. Forecast query page at (/wellington, /christchurch, /auckland). Displays weather observations and scoring where available
    3. Analysis page (/analyis-wellington ...) showing forecast accuracy plot

notes:
    - There are 2 threshold variables hidden in here which effect scoring shown in tables. 
    The threshold values here should match those in scoring.py

"""
import psycopg2
import numpy as np
import datetime
from flask import Flask, render_template, request

app = Flask(__name__)

# home page
@app.route('/')
def main():
    return render_template('index.html')
 
# forecast query table
@app.route('/<lookup>',  methods=["GET","POST"])
def regionLookup(lookup):
    try: # is date provided
        (region,dateSTR)=lookup.split('_')
    except: # if date not provided then start on today
        region=str(lookup)
        forecastday=datetime.datetime.utcnow()+datetime.timedelta(hours=12)
        dateSTR='%s-%s-%s' % (forecastday.year,forecastday.month,forecastday.day)    
    date=datetime.datetime.strptime(dateSTR,'%Y-%m-%d')

    #connect to db    
    conn = psycopg2.connect("")
    cur = conn.cursor()

    #first get the observations for the day if available
    stations={'wellington':['Wellington Airport','Kelburn, Wellington','Porirua City'],
         'auckland':['Auckland Airport','Whenuapai',''],
         'christchurch':['Christchurch Airport','New Brighton Pier','Lyttelton']}    
    thresholdObs=0.1
 
    try:
        cur.execute("""SELECT rain, wind, dir, high, low from %s WHERE day = '%s' AND (station = '%s' OR station = '%s' OR station = '%s')""" %('obs_'+region,dateSTR,stations[region][0],stations[region][1],stations[region][2]))
        rows1 = cur.fetchall()
        
        # stations are not group at this stage so need to do some massaging
        (rain,wind,wdir,high,low)=zip(*rows1)
        rain=np.asarray(rain,dtype=np.float)
        wind=np.asarray(wind,dtype=np.float)
        high=np.asarray(high,dtype=np.float)
        low=np.asarray(low,dtype=np.float)
        rain=np.nan_to_num(rain)     # treat NaN as zero
        # change wind angle into bearing
        try:
	        wdirstr=str(np.array(['N','NE','E','SE','S','SW','W','NW','N'])[np.digitize([wdir[np.nanargmax(wind)]],22+np.array([0,45,90,135,180,215,270,315,339]))][0])
    	except:
            wdirstr='NA'

        #build a text string with obs summary
        wthstr='average of '+str(round(np.mean(rain),1))+'mm of rain, max wind gust of '+str(np.nanmax(wind))+'km/h '+wdirstr+', max temperature '+str(np.nanmax(high))+'degC, min temperature '+str(np.nanmin(low))+'degC'
        #build an array with obs data
        dataObs=[str(round(np.nanmax(rain),1)),str(round(np.nanmax(wind),0)),wdirstr,str(np.nanmax(high)),str(np.nanmin(low))]
    except:  
        dataObs=[]
 

    #then get forecasts for this date (rain thresholds are hidden here)
    forecasterLst=list([['nw','Niwa',0.1],['ms','Metservice',0.9],['wc','weather.com',20],['yr','yr.no',0.1]])
    forecasterLst=np.asarray(forecasterLst)
    deltaAll=[0,1,2,3,4,5,6,7,8,9,10]
    deltaAll=np.asarray(deltaAll)
    dataAll=[]
    rainAll=[]
    scoreAll=[]

    # loop through all forecasters
    for forecaster in forecasterLst:
        threshold=float(forecaster[2])

        # initialise empty arrays
        data=(np.asarray(['']*np.size(deltaAll))).astype('S100')
        rain=(np.asarray(['']*np.size(deltaAll))).astype('S100')
        score=np.asarray([np.NaN]*np.size(deltaAll))
        
        # query table and fill arrays
        try:
            cur.execute("""SELECT forecasttxt,delta,rain from %s WHERE forecastday = '%s'  """ %(forecaster[0]+'_'+region,dateSTR))
            rows = cur.fetchall()
            rows = np.asarray(rows)
            try: # copes with days of obs before forecast
                delta=rows[:,1].astype(int)
                data[delta]=(rows[:,0]) 
                rain[delta]=(rows[:,2])
                score[delta]=(rows[:,2].astype(float)>threshold)==(float(dataObs[0])>thresholdObs)
            except:
                pass
            dataAll.append(data)
            rainAll.append(rain)
            scoreAll.append(score)
        except:
            pass

    # massaging array to make it easy to display in html table
    dataAll = np.asarray(dataAll)    
    dataAll = np.vstack((deltaAll,dataAll))
    dataAll = np.transpose(dataAll)
    scoreAll = np.asarray(scoreAll)    
    scoreAll = np.transpose(scoreAll)
    rainAll = np.asarray(rainAll)    
    rainAll = np.transpose(rainAll)
    delta=datetime.timedelta(days=1)

    # indicate correct forecasts by coloring cell green
    colorsAll=np.zeros((np.size(scoreAll,0),np.size(scoreAll,1)),'S100')
    colorsAll[scoreAll==1]='#28a745'
    colorsAll[scoreAll!=1]='#e9ecef'
    return render_template('region.html',dataAll=dataAll, colorsAll=colorsAll,rainAll=rainAll, region=region ,dateSTR=dateSTR, delta=delta, date=date,forecasterLst=forecasterLst[:,1], dataObs=dataObs)

#analysis page
@app.route('/analysis-<region>')
def analysis(region):
    plot=open(region+'.svg').read().decode(errors='ignore')
    return render_template('analysis.html',plot=plot,region=region) 


if __name__ == "__main__":
#   app.run(debug=True)  
    app.run(host="0.0.0.0", port=80)  
    
    
