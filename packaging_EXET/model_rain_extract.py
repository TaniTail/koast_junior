#import sqlite3
import os
from datetime import datetime
import argparse
import importlib

import _config as cfg


# 지점별 데이터 추출

def model_extract(modelCode, modelDt, interval, maxHour, stnXyList, obsCode) :
    '''
    Extracts model data for the specified model code and date, and saves the results to a text file

    Parameters:
    - modelCode(str): The code of the model to be extracted
    - modelDt(datetime): The date and time for which the model data is to be extracted
    - interval(int): The time interval for the forecast (in hours)
    - maxHour(int): The maximum forecast hour
    - stnXyList(list): A list of dictionaries containing station information (station IDs, coordinates)
    - obsCode(str): Observation code ('aws', 'asos')
    
        Returns:
        - None
    
    '''
    
    modelExtractor = importlib.import_module('model_extract.' + modelCode)

    modelData = modelExtractor.model_extract(modelDt, interval, maxHour, stnXyList, cfg.PATH_TMP)
    if modelData is None :
        print(f'[ERROR] {modelCode} model extract failed. {modelDt.strftime("%Y%m%d%H")}')
        return False

    #txtFile = cfg.PATH_MODEL_EXTRACT_TXT.format(MODEL=modelCode, OBS=obsCode, YYYY=modelDt.strftime('%Y'), TH_HR=interval, FT_HR=maxHour, YYYYMMDDHH=modelDt.strftime('%Y%m%d%H'))
    txtFile = cfg.PATH_MODEL_EXTRACT_TXT.format(MODEL=modelCode, OBS=obsCode, YYYY=modelDt.strftime('%Y'), YYYYMMDDHH=modelDt.strftime('%Y%m%d%H'))
    txtFileDir = os.path.dirname(txtFile)
    if not os.path.isdir(txtFileDir) :
        try :
            os.makedirs(txtFileDir)
        except :
            pass
    else :
        if os.path.exists(txtFile) :
            os.remove(txtFile)
    

    stnIds = []
    for stn in stnXyList :
        stnIds.append(stn['stn'])
    stnIds.sort()

    header1 = f"# INFO, model:{modelCode}, obs:{obsCode}, ymdh:{modelDt.strftime('%Y%m%d%H')}, fcstInterval:{interval}, fcstMaxHour:{maxHour}"
    header2 = "#   FT  "
    for step in range(interval, maxHour+interval, interval) : 
        header2 += format(step, "7d")
    cont = ""
    for sid in stnIds :
        #stnId = str(sid)
        cont += format(sid, "6d")
        cont += "  "
        for i in range(len(modelData[sid])) :
            cont += format(modelData[sid][i], "7.2f")
        cont += "\n"
    
    f = open(txtFile, 'w')
    f.write(header1)
    f.write("\n")
    f.write(header2)
    f.write("\n")
    f.write(cont)
    f.close()

def getStnXyList(model, obs, dt) :
    '''
    Read file and get station information including coordinates

    Parameters:
    - model(str): model code
    - obs(str): Observation code (aws, asos)
    - dt(datetime): datetime for finding a file (KST)

    Returns:
    - list: A list of dictionaries contains the station ID, latitude, longitude,
             and x, y coordinates of the station. If the file does not exist, returns False
    '''
    
    xyfile = cfg.PATH_MODEL_STNXY.format(MODEL=model, OBS=obs, YYYY=dt.strftime('%Y'), YYYYMMDD=dt.strftime('%Y%m%d'))
    if os.path.exists(xyfile) == False :
        return False
    # f.write(f"{stnXyInfo['stn']},{stnXyInfo['lat']},{stnXyInfo['lon']},{stnXyInfo['x']},{stnXyInfo['y']}\n")
    stnXyList = []
    with open(xyfile, 'r') as f:
        # 첫 번째 줄(헤더) 건너뛰기
        header = f.readline()
        
        for line in f:
            row = line.split(',')
            pt = {
                'stn': int(row[0]),
                'lat': float(row[1]),
                'lon': float(row[2]),
                'x': int(row[3]),
                'y': int(row[4])
            }
            stnXyList.append(pt)
        

    return stnXyList


# main
if __name__ == '__main__' :

    parser = argparse.ArgumentParser()
    parser.add_argument('--model', required=True, help='gdps_ne36/gdps_n128/rdps_ne36/ldps/ecmf/klfs_ne36/klfs_n128')
    parser.add_argument('--modelTm', required=True, help='yyyymmddhh')
    # parser.add_argument('--fcstInterval', required=True, help='hour')
    # parser.add_argument('--fcstMaxHours', required=True, help='hour')
    parser.add_argument('--obs', required=True, help='asos/aws')

    args = parser.parse_args()

    #print("- Model Extract : ", args.model, args.obs, args.modelTm, 'fcstInterval:', args.fcstInterval, 'fcstMaxHour:',args.fcstMaxHours)
    fcstInterval = cfg.modelConf[args.model]['fcstInterval']
    extractMaxHour = cfg.modelConf[args.model]['modelExtractHours']
    print("- Model Extract : ", args.model, args.obs, args.modelTm, 'interval:', str(fcstInterval), 'extractHour:', str(extractMaxHour))

    modelDt = datetime.strptime(args.modelTm, '%Y%m%d%H')

    stnXyList = getStnXyList(args.model, args.obs, modelDt)
 
    #model_extract(args.model, modelDt, int(args.fcstInterval), int(args.fcstMaxHours), stnXyList, args.obs)
    
    model_extract(args.model, modelDt, fcstInterval, extractMaxHour, stnXyList, args.obs)

