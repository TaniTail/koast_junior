#import json
from datetime import datetime, timedelta
import os
import sqlite3
import argparse
import _config as cfg


def CalcScores(modelCode, obsCode, startDt, endDt, thHour, thMm, maxFcstHour, addtionalCode) :
    '''
    Calculate Contingency table and Scores based on precipitation of given parameters (model, observation code, date etc.)

    Parameters:
    - modelCode(str): model code
    - obsCode(str): Observation code (aws, asos)
    - startDt (datetime): start datetime 
    - endDt (datetime): end datetime
    - thHour (int): thresholdHour (time interval)
    - thMm (float): thresholdMms, (precipitation threshold)
    - maxFcstHour (int): max forecasting hour
    - addtionalCode (str or None): addtionalCode, optional (shrt)

    Returns:
    - dict: 
        - 'ct' (dict): Contingency table for each time interval
        - 'score' (dict): Calculated scores ('ACCURACY', 'BIAS', 'CSI', 'ETS', 'POD', 'FAR', 'POFD')
    '''
    szMm = format(thMm, ".1f")
    
    dbFiles = []
    dt = startDt
    while dt <= endDt :
        #fn = PATH_CT_DB.format(obs=obsCode, yyyy=dt.strftime('%Y'), yyyymm=dt.strftime('%Y%m'))
        if addtionalCode is None :
            fn = cfg.PATH_CT_DAILYSUM_DB.format(OBS=obsCode, YYYY=dt.strftime('%Y'), YYYYMM=dt.strftime('%Y%m'))
        else :
            fn = cfg.PATH_CT_DAILYSUM_DB_ADDTIONAL.format(OBS=obsCode, YYYY=dt.strftime('%Y'), YYYYMM=dt.strftime('%Y%m'), ADD_CODE=addtionalCode)
        #print(fn)
        if fn not in dbFiles :
            dbFiles.append(fn)
        dt = dt + timedelta(days=1) #relativedelta..

    #print(dbFiles)
    #print(modelCode, obsCode, startDt, endDt, thHour, thMm)

    startYmd = (startDt-timedelta(hours=24)).strftime('%Y-%m-%d') + ' 00:00:00'
    endYmd = (endDt+timedelta(days=1)).strftime('%Y-%m-%d') + ' 00:00:00'

    cts = {}
    if addtionalCode != 'shrt' :
        for s in range(thHour, maxFcstHour+1, thHour) :
            cts[s] = {'h':0, 'f':0, 'm':0, 'z':0, 't':0}
    cts[0] = {'h':0, 'f':0, 'm':0, 'z':0, 't':0}
    

    for dbFile in dbFiles :
        conn = sqlite3.connect(dbFile, timeout=30)
        conn.row_factory = sqlite3.Row 
        cur = conn.cursor()

        query = f"SELECT s, h, f, m, z, t FROM ct WHERE d > '{startYmd}' AND d < '{endYmd}' AND th_hour='{thHour}' AND mm='{szMm}' AND model='{modelCode}' AND s<={maxFcstHour} ORDER BY s"
        cur.execute(query)
        
        while True :
            row = cur.fetchone()
            if not row : break
            #if row['s'] not in cts :
            #    cts[row['s']] = {'h':0, 'f':0, 'm':0, 'z':0, 't':0}

            #for x in row.keys() :
            #    print(x, row[x])

            s = row['s']

            if addtionalCode == 'shrt' :
                if s not in cts :
                    cts[s] = {'h':0, 'f':0, 'm':0, 'z':0, 't':0}

            cts[s]['h'] += row['h']
            cts[s]['f'] += row['f']
            cts[s]['m'] += row['m']
            cts[s]['z'] += row['z']
            cts[s]['t'] += row['t']

            cts[0]['h'] += row['h']
            cts[0]['f'] += row['f']
            cts[0]['m'] += row['m']
            cts[0]['z'] += row['z']
            cts[0]['t'] += row['t']
            
        conn.close()

    scNames = {'ACCURACY', 'BIAS', 'CSI', 'ETS', 'POD', 'FAR', 'POFD'}
    scores = {}
    for s in cts :
        scores[s] = {}
        ct = cts[s]
        
        for scName in scNames :
            scVal = -9.99
            if ct is None :
                pass
            elif ct['t'] == 0 :
                pass
            elif scName in ['BIAS', 'POD'] and ct['h'] == 0 and ct['m'] == 0 :
                pass
            elif scName == 'FAR' and ct['h'] == 0 and ct['f'] == 0 :
                pass
            elif scName == 'POFD' and ct['z'] == 0 and ct['f'] == 0 :
                pass
            elif scName == 'CSI' and ct['h'] == 0 and ct['m'] == 0 :
                pass
            else :
                if scName == 'ACCURACY' :
                    scVal = (ct['h'] + ct['z']) / (ct['t'])
                elif scName == 'BIAS' :
                    scVal = (ct['h'] + ct['f']) / (ct['h'] + ct['m'])
                elif scName == 'CSI' :
                    scVal = ct['h'] / (ct['h'] + ct['m'] + ct['f'])
                elif scName == 'ETS' :
                    ar = ((ct['h'] + ct['m']) * (ct['h'] + ct['f'])) / (ct['t'])
                    if (ct['h'] + ct['m'] + ct['f'] - ar) == 0 :
                        scVal = -9.99
                    else :
                        scVal = (ct['h'] - ar) / (ct['h'] + ct['m'] + ct['f'] - ar)
                elif scName == 'POD' :
                    scVal = ct['h'] / (ct['h'] + ct['m'])
                elif scName == 'FAR' :
                    scVal = ct['f'] / (ct['h'] + ct['f'])
                elif scName == 'POFD' :
                    scVal = ct['f'] / (ct['f'] + ct['z'])
            scores[s][scName] = scVal

    return {'ct':cts, 'score':scores}
    

def SaveScores(modelCode, obsCode, startDt, endDt, thHour, thMm, maxFcstHour, scores, addtionalCode) :
    '''
    Save the evaluation scores to a file
    
    Parameters:
    - modelCode(str): model code
    - obsCode(str): Observation code (aws, asos)
    - startDt (datetime): start datetime 
    - endDt (datetime): end datetime
    - thHour (int): thresholdHour (time interval)
    - thMm (float): thresholdMms, (precipitation threshold)
    - maxFcstHour (int): max forecasting hour
    - scores (dict): calculated scores and statistical information
    - addtionalCode (str or None): addtionalCode, optional
    
    Returns:
    - None
    '''
    #dirpath = cfg.PATH_DAOU + '/pretty/' + startDt.strftime('%Y%m') + '/' + modelCode
    if addtionalCode is None :
        dirpath = cfg.PATH_PRETTY_FORMAT_DIR.format(MODEL=modelCode, YYYYMM=startDt.strftime('%Y%m'))
    else :
        dirpath = cfg.PATH_PRETTY_FORMAT_DIR_ADDTIONAL.format(MODEL=modelCode, YYYYMM=startDt.strftime('%Y%m'), ADD_CODE=addtionalCode)

    if not os.path.isdir(dirpath) :
        os.makedirs(dirpath)

    cont = " \n"
    cont += " ------------------------------------------------------\n"
    cont += " BASED ON OBSV  from {date1} to {date2}\n".format(date1=startDt.strftime('%Y%m%d'), date2=endDt.strftime('%Y%m%d'))
    cont += " ------------------------------------------------------\n"
    cont += " \n"
    cont += "  Valid Forecast time is  {ft1} hr\n".format(ft1=format(maxFcstHour, "5d"))
    cont += "  Threshold time  is  {th_hour} hr\n".format(th_hour=format(thHour, "9d"))
    cont += "  Threshold Value is    {th_mm} mm\n".format(th_mm=format(thMm, "7.1f"))
    cont += " \n"
    cont += "       Contingency Table\n"
    cont += "              "
    for s in scores['ct'] :
        #if s > maxFcstHour : break
        cont += format(s, "7d") + "H"
    cont += "\n"
    cont += "  Hits  Number"
    for s in scores['ct'] :
        #if s > maxFcstHour : break
        cont += format(scores['ct'][s]['h'], "8d")
    cont += "\n"
    cont += "  False Number"
    for s in scores['ct'] :
        #if s > maxFcstHour : break
        cont += format(scores['ct'][s]['f'], "8d")
    cont += "\n"
    cont += "  Miss  Number"
    for s in scores['ct'] :
        #if s > maxFcstHour : break
        cont += format(scores['ct'][s]['m'], "8d")
    cont += "\n"
    cont += "  Zero  Number"
    for s in scores['ct'] :
        #if s > maxFcstHour : break
        cont += format(scores['ct'][s]['z'], "8d")
    cont += "\n"
    cont += "  Total Number"
    for s in scores['ct'] :
        #if s > maxFcstHour : break
        cont += format(scores['ct'][s]['t'], "8d")
    cont += "\n"

    cont += " \n"
    cont += "       Categorical statistics\n"

    cont += "  Accuracy    "
    for s in scores['score'] :
        #if s > maxFcstHour : break
        cont += format(scores['score'][s]['ACCURACY'], "8.2f")
    cont += "\n"
    cont += "  Bias Score  "
    for s in scores['score'] :
        #if s > maxFcstHour : break
        cont += format(scores['score'][s]['BIAS'], "8.2f")
    cont += "\n"
    cont += "  P.O.D.      "
    for s in scores['score'] :
        #if s > maxFcstHour : break
        cont += format(scores['score'][s]['POD'], "8.2f")
    cont += "\n"
    cont += "  F.A.R.      "
    for s in scores['score'] :
        #if s > maxFcstHour : break
        cont += format(scores['score'][s]['FAR'], "8.2f")
    cont += "\n"
    cont += "  P.O.F.D.    "
    for s in scores['score'] :
        #if s > maxFcstHour : break
        cont += format(scores['score'][s]['POFD'], "8.2f")
    cont += "\n"
    cont += "  T.S. (CSI)  "
    for s in scores['score'] :
        #if s > maxFcstHour : break
        cont += format(scores['score'][s]['CSI'], "8.2f")
    cont += "\n"
    cont += "  E.T.S. (GSS)"
    for s in scores['score'] :
        #if s > maxFcstHour : break
        cont += format(scores['score'][s]['ETS'], "8.2f")
    cont += "\n"
    cont += " \n"

    cont += " ------------------------------------------------------\n"

    #print(dirpath, modelCode, thMm, thHour, maxFcstHour, startDt, endDt, obsCode)
    fn = dirpath + '/' + modelCode + '_vrfy_obsv_' + format(thMm, ".1f") + 'mm_' + str(thHour).zfill(2) + 'hr_' + str(maxFcstHour) + 'ft' + '_' + startDt.strftime('%Y%m%d') + '_' + endDt.strftime('%Y%m%d') + '_' + obsCode + '.txt'

    f = open(fn, 'w')
    f.write(cont)
    f.close()

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--model', required=True, help='gdps_ne36/gdps_n128/rdps_ne36/ldps/ecmf/klfs_ne36/klfs_n128')
    parser.add_argument('--obs', required=True, help='asos/aws')
    parser.add_argument('--startDate', required=True, help='yyyymmdd')
    parser.add_argument('--endDate', required=True, help='yyyymmdd')
    parser.add_argument('--addtionalCode', required=False, help='shrt:ShrtFcstVrfy(meteorologist) verification rule')

    args = parser.parse_args()

    if args.addtionalCode == None :
        print("Save ASCII format : ", args.model, args.obs, args.startDate, args.endDate)
    else :
        print("Save ASCII format : ", args.model, args.obs, args.startDate, args.endDate, args.addtionalCode)

    startDt = datetime.strptime(args.startDate, '%Y%m%d')
    endDt = datetime.strptime(args.endDate, '%Y%m%d')

    #print(args.model)
    for thresholdHour in cfg.modelConf[args.model]['modelThresholdHours']:
        #print('thresholdHour : ', thresholdHour)
        for thMm in cfg.thresholdMms:
            szMm = format(thMm, ".1f")
            #print(szMm)
            for maxFcstHour in cfg.modelConf[args.model]['modelFcstMaxHours'] :
                scores = CalcScores(args.model, args.obs, startDt, endDt, thresholdHour, thMm, maxFcstHour, args.addtionalCode)
                SaveScores(args.model, args.obs, startDt, endDt, thresholdHour, thMm, maxFcstHour, scores, args.addtionalCode)