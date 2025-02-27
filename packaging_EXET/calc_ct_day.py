#import json
from datetime import datetime, timedelta
import os
import sqlite3
import argparse
import math
import _config as cfg
import pandas as pd


class CalcContingencyDay :
    def __init__(self) -> None:
        pass

    def GetDayObs(self, targetDay, thresholdHour, stnIds, obsCode) -> dict:
        '''
        Calculates and returns the Observed Accumulative Precipitation for the given date, thresholdHour
        
        Parameters:
        - targetDay(datetime): date (KST)
        - thresholdHour(int): Time to determine the prediction interval
        - stnIds(list): Station Id list
        - obsCode(str): Observation code (aws, asos)

        Returns:
        - dict: Observed Accumulative precipitation by section for each station
        '''
        ymd = targetDay.strftime('%Y%m%d')
        txtFile = cfg.PATH_OBS_TXT.format(OBS=obsCode, YYYY=ymd[0:4], YYYYMMDD=ymd) # "./DAIN/OBS/{YYYY}/rain_obsv_{OBS}.{YYYYMMDD}" 
    
        if os.path.exists(txtFile) == False :
            print('GetDayObs - File not found - ' + txtFile)
            return False

        obs = {}
        for stn in stnIds :
            obs[stn] = {}
            for s in range(thresholdHour, 24+thresholdHour, thresholdHour) :
                obs[stn][s] = 0
        
        f = open(txtFile, 'r')
        while True :
            line = f.readline()
            if not line : break
            if len(line) < 242 : continue # stnId:9,dt:9,rn:9*24,=:8
            stn = int(line[0:9]) # # stnId:9,dt:9,rn:9*24,=:8
            if stn not in stnIds :
                continue
            #posBase = 18
            for hIdx in range(0,24) :
                pos = 18 + (hIdx * 9)
                tmp = line[pos:pos+9].strip()
                rn = None
                if len(tmp) < 1 : continue
                rn = float(tmp)
                hour = hIdx + 1 # 1h ~ 24h
                s = math.ceil(hour / thresholdHour) * thresholdHour
                obs[stn][s] += round(rn, 1)
                obs[stn][s] = round(obs[stn][s], 1)
        f.close()

        return obs
    
    def GetDayModel(self, targetDay, thresholdHour, stnIds, modelCode, obsCode) -> dict:
        '''
        Calculates and returns the Model predicted Accumulative Precipitation for the given date, thresholdHour
        
        Parameters:
        - targetDay(datetime): date (KST)
        - thresholdHour(int): Time to determine the prediction interval
        - stnIds(list): Station Id list
        - modelCode(str): model code
        - obsCode(str): Observation code (aws, asos)

        Returns:
        - dict: Model Predicted Accumulative Precipitation by section for each station
        '''
        targetDayEnd = targetDay + timedelta(days=1)

        modelSum = {stn : {} for stn in stnIds}
        modelFcstMaxHour = max(cfg.modelConf[modelCode]['modelFcstMaxHours'])

        dtStart = targetDay - timedelta(hours=max(cfg.modelConf[modelCode]['modelFcstMaxHours']))
        dtEnd = targetDay + timedelta(days=1) - timedelta(hours=thresholdHour)

        modelDts = []
        dt = dtStart
        while dt <= dtEnd :
            for t in cfg.modelConf[modelCode]['t'] : # 모델의 발표 시각마다
                dt1 = dt + timedelta(hours=t)
                dt1Str = dt1.strftime("%Y-%m-%d %H:%M:%S")
                for s in range(thresholdHour, modelFcstMaxHour+thresholdHour, thresholdHour) :
                    dt2 = dt1 + timedelta(hours=s)
                    if dt2 <= targetDay or dt2>targetDayEnd :
                        continue
                    if dt1Str not in modelDts :
                        modelDts.append(dt1Str)
                    for stn in stnIds :
                        if dt1Str not in modelSum[stn] :
                            modelSum[stn][dt1Str] = {}                        
                        modelSum[stn][dt1Str][s] = 0
            dt = dt + timedelta(days=1)
            
        txtFiles = []
        for modelDtStr in modelDts :
            modelDt = datetime.strptime(modelDtStr, '%Y-%m-%d %H:%M:%S')
            fn = cfg.PATH_MODEL_EXTRACT_TXT.format(MODEL=modelCode, OBS=obsCode, YYYY=modelDt.strftime('%Y'), YYYYMMDDHH=modelDt.strftime('%Y%m%d%H'))
            if os.path.exists(fn) == False :
                print('GetDayModel - File not found - ' + fn)
                return False
            txtFiles.append(fn)

        # 각 발표 시각 마다 thresholdHour 단위로 취합
        for txtFile in txtFiles :
            #print(txtFile)
            f = open(txtFile, 'r')
            line = f.readline()
            if not line :
                print('GetDayModel - no lines - ' + txtFile)
                return False
            if line[0:6] != '# INFO' :
                print('GetDayModel - no info line - ' + txtFile)
                return False
            tmp = line.split(',')
            info = {}
            for kv in tmp :
                tmp2 = kv.strip().split(':')
                #print(kv)
                #print(tmp2)
                if len(tmp2)<2 : continue
                k1 = tmp2[0]
                v1 = tmp2[1]
                if k1 == 'fcstInterval' or k1 == 'fcstMaxHour' :
                    v1 = int(v1)
                info[k1] = v1
            #print(info)
            
            if modelFcstMaxHour > info['fcstMaxHour'] :
                print('GetDayModel - not enough ft - ' + txtFile)
                return False
            if thresholdHour < info['fcstInterval'] :
                print('GetDayModel - file interval is bigger then thresholdHour - ' + txtFile)
                return False
            if thresholdHour % info['fcstInterval'] != 0 :
                print('GetDayModel - thresholdHour is not multiples of file fcstInterval - ' + txtFile)
                return False

            model_dt = datetime.strptime(info['ymdh'], '%Y%m%d%H')
            
            szModelDt = model_dt.strftime("%Y-%m-%d %H:%M:%S")

            while True :
                line = f.readline()
                if not line : break
                if len(line) < 6 : continue
                if line[0] == '#' : continue
                stn = int(line[0:6])
                if stn not in stnIds :
                    continue
                #print(line)
                
                #print(modelSum[stn][szModelDt])
                
                for step in range(info['fcstInterval'], modelFcstMaxHour+info['fcstInterval'], info['fcstInterval']) :
                    sIdx = int(step / info['fcstInterval'])
                    pos = 6 + 2 + ((sIdx-1) * 7)
                    tmp = line[pos:pos+7].strip()
                    #print(stn, step, sIdx, pos, tmp)
                    
                    thS = math.ceil(step / thresholdHour) * thresholdHour
                    #print(thS, '=', step, '/', thresholdHour, '*', thresholdHour)
                    if thS not in modelSum[stn][szModelDt] :
                        continue
                    if len(tmp) < 1 : continue
                    rn = float(tmp)

                    modelSum[stn][szModelDt][thS] += round(rn, 2)
                    modelSum[stn][szModelDt][thS] = round(modelSum[stn][szModelDt][thS], 2)
            f.close()

        # # 모델값 출력 포맷
        # maxHour = max(cfg.modelConf[modelCode]['modelFcstMaxHours'])
        # modelDts.sort()
        # for dt in modelDts :
        #     print(dt)
        #     print("      ", end='')
        #     for s in range(thresholdHour, maxHour+thresholdHour, thresholdHour) :
        #         print(format(s, "7d"), end='')
        #     print("")
        #     for stn in modelSum :
        #         print(format(stn, "6d"), end='')
        #         for s in range(thresholdHour, maxHour+thresholdHour, thresholdHour) :
        #         #for s in modelSum[stn][dt] :
        #             if dt in modelSum[stn] and s in modelSum[stn][dt] :
        #                 print(format(modelSum[stn][dt][s], "7.2f"), end='')
        #             else :    
        #                 print("   x.xx", end='')
        #         print("")
        #     print("")
                
        return modelSum

        
    




    def CalcContingency(self, targetDay, thresholdHour, stnIds, modelCode, obs, model) -> dict:
        '''
        Calculates Contingency table with Observed Accumulative Precipitation and Model Predicted Accumulative Precipitation
        
        Parameters:
        - targetDay(datetime): date (KST)
        - thresholdHour(int): Time to determine the prediction interval
        - stnIds(list): Station Id list
        - modelCode(str): model code
        - obs(dict): Observed Accumulative Precipitation by section for each station
        - model(dict): Model Predicted Accumulative Precipitation by section for each station

        Returns:
        - dict: Contingency table
        '''
        ymd1 = targetDay.strftime('%Y-%m-%d') + " 00:00:00"
        ymd2 = (targetDay+timedelta(days=1)).strftime('%Y-%m-%d') + " 00:00:00"
        
        modelFcstMaxHour = max(cfg.modelConf[modelCode]['modelFcstMaxHours'])

        dtStart = targetDay - timedelta(hours=modelFcstMaxHour)
        dtEnd = targetDay + timedelta(days=1) - timedelta(hours=thresholdHour)

        ct = {}
        for mm in cfg.thresholdMms:
            szMm = format(mm, ".1f")
            ct[szMm] = {}
            for stn in stnIds:
                stnVals = {}
                # for s in ss :
                #     stnVals[str(s)] = {'h':0, 'f':0, 'm':0, 'z':0, 't':0}

                for modelDtStr in model[stn] :
                    for s in model[stn][modelDtStr] :
                        
                        modelV = model[stn][modelDtStr][s]

                        obsDt = datetime.strptime(modelDtStr, '%Y-%m-%d %H:%M:%S') + timedelta(hours=s)

                        obsS = obsDt.hour
                        if obsS == 0 : obsS = 24
                        
                        obsV = obs[stn][obsS]

                        
                        ft = True if modelV >= mm else False
                        ob = True if obsV >= mm else False

                        szS = str(s)
                        if szS not in stnVals :
                            stnVals[szS] = {'h':0, 'f':0, 'm':0, 'z':0, 't':0}
                        rstCode = 'z'
                        if ft is True and ob is True: rstCode = 'h' # hit
                        elif ft is False and ob is True: rstCode = 'm' # miss
                        elif ft is True and ob is False: rstCode = 'f' # false alarm
                        elif ft is False and ob is False: rstCode = 'z' # correct negative, null
                        
                        stnVals[szS][rstCode] += 1
                        stnVals[szS]['t'] += 1

                        

                # print(stn)
                # print(stnVals)
                ct[szMm][stn] = stnVals
        return ct
    

    def rows_ContingencyDay(self, targetDay, thresholdHour, stnIds, modelCode, obsCode, ct):
        '''
        make rows for the daily contingency table
        
        Parameters:
        - targetDay (datetime): The date for which the contingency table is being created (KST).
        - thresholdHour (int): The time interval for which the predictions are made.
        - stnIds (list): A list of station IDs.
        - modelCode (str): The code of the model being used.
        - obsCode (str): The code for the observed data (not used in this function).
        - ct (dict): The contingency data, containing observed and predicted values for each station and threshold.

        Returns:
        - list: A list of dictionaries, each representing a row in the contingency table.
        '''
                
        insertDatas = []
        for mm in cfg.thresholdMms:
            szMm = format(mm, ".1f")
            for s in range(thresholdHour, max(cfg.modelConf[modelCode]['modelFcstMaxHours'])+thresholdHour, thresholdHour):
                for stn in stnIds:
                    row = {
                        'd': targetDay.strftime('%Y-%m-%d'),
                        's': s,
                        'th_hour': thresholdHour,
                        'mm': szMm,
                        'stn': stn,
                        'h': ct[szMm][stn][str(s)]['h'],
                        'f': ct[szMm][stn][str(s)]['f'],
                        'm': ct[szMm][stn][str(s)]['m'],
                        'z': ct[szMm][stn][str(s)]['z'],
                        't': ct[szMm][stn][str(s)]['t']
                    }
                    insertDatas.append(row)
        return insertDatas

    def rows_ContingencyDaySum(self, targetDay, thresholdHour, modelCode, obsCode, ctSum):
        '''
        make rows for the contingency daily sum table
        
        Parameters:
        - targetDay (datetime): The date for which the summary contingency table is being created (KST).
        - thresholdHour (int): The time interval for which the predictions are aggregated.
        - modelCode (str): The code of the model being used.
        - obsCode (str): The code for the observed data (not used in this function).
        - ctSum (dict): The summary contingency data, containing aggregated observed and predicted values for each threshold.

        Returns:
        - list: A list of dictionaries, each representing a row in the summary contingency table.
        '''
        insertDatas = []
        for mm in cfg.thresholdMms:
            szMm = format(mm, ".1f")
            for s in range(thresholdHour, max(cfg.modelConf[modelCode]['modelFcstMaxHours'])+thresholdHour, thresholdHour):
                row = {
                    'd': targetDay.strftime('%Y-%m-%d'),
                    'th_hour': thresholdHour,
                    's': s,
                    'mm': szMm,
                    'model': modelCode,
                    'h': ctSum[szMm][str(s)]['h'],
                    'f': ctSum[szMm][str(s)]['f'],
                    'm': ctSum[szMm][str(s)]['m'],
                    'z': ctSum[szMm][str(s)]['z'],
                    't': ctSum[szMm][str(s)]['t']
                }
                insertDatas.append(row)
        return insertDatas

    def SaveContingencyDay(self, targetDay, modelCode, obsCode, data):
        '''
        Save the contingency data for a specific day.

        Parameters:
        - targetDay (datetime): The date for which the contingency data is being saved (KST).
        - modelCode (str): The code of the model being used.
        - obsCode (str): The code for the observed data.
        - data (dict or list): The contingency data to be saved in CSV format.

        Returns:
        - None: The function saves the data to a CSV file without returning any values.
        '''
        csvFile = cfg.PATH_CT_DAILY_CSV.format(MODEL=modelCode, OBS=obsCode, YYYY=targetDay.strftime('%Y'), YYYYMMDD=targetDay.strftime('%Y%m%d'))
        csvFileDir = os.path.dirname(csvFile)
        
        if not os.path.isdir(csvFileDir):
            os.makedirs(csvFileDir)
        
        df = pd.DataFrame(data)
        df.to_csv(csvFile, index=False)

    def SaveContingencyDaySum(self, targetDay, modelCode, obsCode, data):
        '''
        Save the summary contingency data for a specific day.

        Parameters:
        - targetDay (datetime): The date for which the summary contingency data is being saved (KST).
        - modelCode (str): The code of the model being used.
        - obsCode (str): The code for the observed data.
        - data (dict or list): The summary contingency data to be saved in CSV format.

        Returns:
        - None: The function saves the data to a CSV file without returning any values.
        '''
        csvFile = cfg.PATH_CT_DAILYSUM_CSV.format(MODEL=modelCode, OBS=obsCode, YYYY=targetDay.strftime('%Y'), YYYYMMDD=targetDay.strftime('%Y%m%d'))
        csvFileDir = os.path.dirname(csvFile)
        
        if not os.path.isdir(csvFileDir):
            os.makedirs(csvFileDir)
        
        df = pd.DataFrame(data)
        df.to_csv(csvFile, index=False)



    def SumContingency(self, thresholdHour, stnIds, modelCode, ct) -> dict:
        '''
        Sum the values in the Contingency Table for given stnIds, ththresholdHour
        
        Parameters:
        - thresholdHour(int): Time to determine the prediction interval
        - stnIds(list): Station Id list
        - modelCode(str): model code
        - ct(dict): Contingency table

        Returns:
        - dict: Sum Contingency Table values for each Threshold precipitation(szMm) and publish time(pubTm)
        '''
        maxHour = max(cfg.modelConf[modelCode]['modelFcstMaxHours'])
        ss = []
        for s in range(thresholdHour, maxHour+thresholdHour, thresholdHour):
            ss.append(s)

        ctSum = {}
        for mm in cfg.thresholdMms:
            #szMm = round(mm, 1)
            szMm = format(mm, ".1f")
            ctSum[szMm] = {}
            for s in ss :
                szS = str(s)
                h = 0
                f = 0
                m = 0
                z = 0
                for stn in stnIds :
                    h += ct[szMm][stn][szS]['h']
                    f += ct[szMm][stn][szS]['f']
                    m += ct[szMm][stn][szS]['m']
                    z += ct[szMm][stn][szS]['z']
                    
                ctSum[szMm][szS] = {'h': h, 'f': f, 'm': m, 'z': z, 't': h+f+m+z}
        return ctSum
    
   
    
    def GetStnIds(self, model, obs, dt) :
        '''
        Read station location information from a given file and returns a list of station IDs
        
        Parameters:
        - model(str): model code
        - obs(str): Observation code (aws, asos)
        - dt(datetime): datetime for finding a file

        Returns:
        - list: station IDs
        '''
        stnIds = []       
        xyfile = cfg.PATH_MODEL_STNXY.format(MODEL=model, OBS=obs, YYYY=dt.strftime('%Y'), YYYYMMDD=dt.strftime('%Y%m%d'))
        if os.path.exists(xyfile) == False :
            return False
        f = open(xyfile, 'r')
        
        # 첫 줄을 건너뛰어 헤더를 무시 (STNXY 파일 헤더 넣으면서 바뀐 부분)
        f.readline()
        
        while True :
            line = f.readline()
            if not line : break
            row = line.split(',')
            x = int(row[3])
            y = int(row[4])
            if x is None or y is None :
                continue
            stnId = int(row[0])
            stnIds.append(stnId)
        f.close()
            
        return stnIds



if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--model', required=True, help='gdps_ne36/gdps_n128/rdps_ne36/ldps/ecmf')
    parser.add_argument('--obs', required=True, help='asos/aws')
    parser.add_argument('--targetDate', required=True, help='yyyymmdd')

    args = parser.parse_args()

    dt = datetime.strptime(args.targetDate, '%Y%m%d')

    print("- Calc Contingency : ", args.model, args.obs, args.targetDate)

    calcCt = CalcContingencyDay()
    
    stnIds = calcCt.GetStnIds(args.model, args.obs, dt)
    
    all_ct_data = []
    all_ctSum_data = []

    for thresholdHour in cfg.modelConf[args.model]['modelThresholdHours']:
        print(args.model, args.obs, args.targetDate, 'thresholdHour : ', thresholdHour)
        obs = calcCt.GetDayObs(dt, thresholdHour, stnIds, args.obs)
        if obs is None or obs is False:
            continue
        model = calcCt.GetDayModel(dt, thresholdHour, stnIds, args.model, args.obs)
        if model is None or model is False:
            continue

        ct = calcCt.CalcContingency(dt, thresholdHour, stnIds, args.model, obs, model) 
        ctSum = calcCt.SumContingency(thresholdHour, stnIds, args.model, ct) 

        # Accumulate data for all thresholdHours
        all_ct_data.extend(calcCt.rows_ContingencyDay(dt, thresholdHour, stnIds, args.model, args.obs, ct))
        all_ctSum_data.extend(calcCt.rows_ContingencyDaySum(dt, thresholdHour, args.model, args.obs, ctSum))

    # Save all accumulated data after the loop
    calcCt.SaveContingencyDay(dt, args.model, args.obs, all_ct_data)
    calcCt.SaveContingencyDaySum(dt, args.model, args.obs, all_ctSum_data)
