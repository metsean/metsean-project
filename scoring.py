# -*- coding: utf-8 -*-
"""
Created on Fri Jul 13 11:45:19 2018
@author: Sean

Analysis script which compares rain forecasts to observation and scores accuracy

For each region the analysis workflow is:
    1. read observation table to find recorded rain for all days
    2. for each of these days compare history of forecast rain predications. Forecast scores as correct if:
        a. rain forecasted and rain observed
        b. no rain forecasted and no rain observed
    3. the accuracy is the ratio of correct forecast scores to total scores
    4. repeat 2-3 for all forecast providers

Notes:
    - there are adjustable threshold parameters for observation and forecasted rain

Output is a rain forecast accuracy plot in svg format. 

Output is viewable as http://www.metsean.xyz/analysis-wellington,
http://www.metsean.xyz/analysis-auckland, http://www.metsean.xyz/analysis-christchurch

"""
import psycopg2
import numpy as np
import matplotlib.pyplot as plt
 
class analysis:
    def Region(self,tableName,stationList,forecaster,threshold):
        conn = psycopg2.connect("")
        cur = conn.cursor()
        
        # first read observation tables to get rain data
        cur.execute("""SELECT day, rain from %s WHERE station = '%s' OR station = '%s' OR station = '%s'""" %('obs_'+tableName,stationList[0],stationList[1],stationList[2]))
        rows = cur.fetchall()
        
        # stations are not grouped at this stage so need to do some massaging
        (dates,rain)=zip(*rows)
        dates=np.asarray(dates,dtype=np.str)
        rain=np.asarray(rain,dtype=np.float)
        rain=np.nan_to_num(rain)     # treat NaN as zero
        datesUn=np.unique(dates)     # find unique dates 
 
        # define lists
        rainSummedAll=[]        
        deltaAll=[0,1,2,3,4,5,6,7,8,9,10]
        dataAll=[]
        
        for days in reversed(datesUn):    #loop through unique days
            data=np.asarray([np.NaN]*np.size(deltaAll))

            cond=[dates==days]  # finding all rows for day
            selection=np.select(cond,list([rain]))    
            rainSummed=sum(selection) # sum the observed rain fall for this day for queried stations
            rainSummedAll.append(rainSummed)
            
            # check forecasted rain for this date for extent of forecast                
            cur.execute("""SELECT rain,delta from %s WHERE forecastday = '%s'  """ %(forecaster+'_'+tableName,days))
            rows2 = cur.fetchall()
            rows2 = np.asarray(rows2)

            try: # copes with days of obs before forecast
                delta=rows2[:,1].astype(int)

            # this is the did it rain check. These observational thresholds can be adjusted
                thresholdObs=0.1
                data[delta]= (rows2[:,0]>threshold)==(rainSummed>thresholdObs) 
                dataAll.append(data)
            except:
                pass
                         
        dataAll = np.asarray(dataAll)    
        rainSummedAll = np.asarray(rainSummedAll)

       #stats             
        dataAll[:,np.count_nonzero(~np.isnan(dataAll),axis=0)<10]=np.nan # ignore forecast deltas with low occurence

        count=np.size(dataAll,axis=0)    # number of observed days with forecast 
        eventcount=(sum(rainSummedAll>thresholdObs)).astype(float) # number of rain days
        guess=eventcount/np.size(rainSummedAll,axis=0)         # baseline guess accuracy
        score=(np.nansum(dataAll,axis=0)).astype(float)/np.nansum(~np.isnan(dataAll),axis=0) # score is number of correct forecasts / total forecasts
        stats=[count,int(eventcount),guess,thresholdObs,datesUn[0],datesUn[-1]] # output stats array compiled from above
        
        cur.close()
        conn.close()
       
        return score,deltaAll,stats

# input region name and oberservation station list. Performs analysis for all forecasters and generates plot 
class doAll:
    def region(self,regionName,stationList):   
        fig = plt.figure(1, figsize=(8,8))
        fig.clf()

        ax = fig.add_subplot(111)
        
        k=analysis()
        forecasterLst=list([['nw','Niwa',0.1],['ms','Metservice',0.1],['yr','yr.no',0.1],['wc','weather.com',20]])

        for forecaster in forecasterLst:
            (score,delta,stats)=k.Region(regionName,stationList,forecaster[0],forecaster[2])
            plt.plot(delta,score,label=forecaster[1],linewidth=3.0)       
        
        plt.plot([delta[0],delta[-1]],[np.max([stats[2],1-stats[2]]),np.max([stats[2],1-stats[2]])],linestyle=':',label='baseline',color='black')   
        plt.title('Rain forecast accuracy for '+regionName+'\nfor period '+str(stats[4])+' to '+str(stats[5]))                   
        plt.xlabel('days forward')           
        plt.ylabel('accuracy')      
        props = dict(boxstyle='square',facecolor='white', alpha=1)
        plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0)    
        ax.text(0.95, 0.05, 'count = '+str(stats[0])+'\nrain days = '+str(stats[1])+'\nthreshold(mm) = '+str(stats[3]), horizontalalignment='right', transform=ax.transAxes,bbox=props, color='black')
        plt.savefig(regionName+'.svg', bbox_inches='tight')
        plt.draw()
        plt.show()

h=doAll()
h.region('Wellington',list(['Wellington Airport','Kelburn, Wellington','Porirua City']))
h.region('Auckland',list(['Auckland Airport','Whenuapai','']))
h.region('Christchurch',list(['Christchurch Airport','New Brighton Pier','Lyttelton']))

