import os
from datetime import datetime, timedelta
import netCDF4
import subprocess
import uuid

PATH_MODEL_FILE = '/ARCV/NWP/GRIB/MODL/LDPS/N128/{YYYYMM}/{DD}/l015_v070_erlo_unis_h{STEP}.{YYYYMM}{DD}{HH}.gb2'
#wgrib2 /h1/data/nwp/ARCV/GRIB/MODL/LDPS/N128/202404/15/l015_v070_erlo_unis_h000.2024041500.gb2 -match ":(NCPCP|SNOL)"

# 지점별 데이터 추출
def model_extract(modelDt, interval, maxHour, stnXyList, tmpPath) :    
    rstData = {}
    testsum=0
    for step in range(interval, maxHour+interval, interval) :        
        modelPath = PATH_MODEL_FILE.format(YYYYMM=modelDt.strftime('%Y%m'), DD=modelDt.strftime('%d'), HH=modelDt.strftime('%H'), STEP=str(step).zfill(3))
        #print(modelPath)
        if not os.path.exists(modelPath) :
            print(f'[ERROR] Not found {modelPath}')
            return None

        varNames = ["NCPCP", "SNOL"]
        try :
            joined_variables = ":(" + '|'.join([vn for vn in varNames]) + ")"
            joined_ijlat = ' '.join([f'-ijlat {stnInfo["x"]+1} {stnInfo["y"]+1}' for stnInfo in stnXyList])
            output = subprocess.run(f'export OMP_NUM_THREADS=1 && wgrib2 {modelPath} -match "{joined_variables}" -var {joined_ijlat}', shell=True ,capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as grepexc:                                                                                                   
            print("[ERROR] during wgrib2", grepexc.returncode, grepexc.output)
            return None
        list_output = output.stdout.split('\n')[:-1]
        if len(list_output) < len(varNames) :
            raise Exception(f'No data found in {modelPath}, {joined_ijlat}')
        
        targetDt = modelDt + timedelta(hours=step)
        rstVals = {}
        for vn in varNames: rstVals[vn] = []
        for i, line in enumerate(list_output):
            line_split = line.split(':')
            vn = varNames[i]
            for j, data in enumerate(line_split[3:]) :
                data_split = data.split(',')[2:]                
                rstVals[vn].append(float(data_split[2].split('=')[1]))       
        for i, v in enumerate(rstVals[varNames[0]]) :
            prec_tot = 0
            for vn in varNames :
                prec_tot += round(rstVals[vn][i], 2)
            
            stn = stnXyList[i]['stn']
            pt = {
                'stn' : stnXyList[i]['stn'],
                'model_dt' : modelDt.strftime('%Y-%m-%d %H:%M:%S'),
                'target_dt' : targetDt.strftime('%Y-%m-%d %H:%M:%S'),
                'step' : step,
                'prec' : prec_tot,
                'x' : stnXyList[i]['x'],
                'y' : stnXyList[i]['y'],
                'sum' : testsum
            }
            
            #pt['prec'] = round(pt['prec'], 2)
            #if pt['prec'] == 0 : continue
            #insertDatas.append(pt)
            if stn not in rstData : 
                rstData[stn] = []
            prec_tot = round(prec_tot, 2)
            rstData[stn].append(prec_tot)
    
    return rstData