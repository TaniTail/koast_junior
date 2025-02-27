import os
from datetime import datetime, timedelta
#import netCDF4
import subprocess
import uuid


PATH_MODEL_FILE = '/ARCV/NWP/GRIB/MODL/GDPS/N128/{YYYYMM}/{DD}/g128_v070_ergl_unis_h{STEP}.{YYYYMM}{DD}{HH}.gb2'

# 지점별 데이터 추출
def model_extract(modelDt, interval, maxHour, stnXyList, tmpPath) :
    #insertDatas = []
    rstData = {}
    for step in range(interval, maxHour+interval, interval) :        
        modelPath = PATH_MODEL_FILE.format(YYYYMM=modelDt.strftime('%Y%m'), DD=modelDt.strftime('%d'), HH=modelDt.strftime('%H'), STEP=str(step).zfill(3))
        #print(modelPath)
        if not os.path.exists(modelPath) :
            print(f'[ERROR] Not found {modelPath}')
            return None

        #tmpModelPath = tmpPath + '/' + str(uuid.uuid4()).replace('-', '') + '.nc'
        try :
            joined_ijlat = ' '.join([f'-ijlat {stnInfo["x"]+1} {stnInfo["y"]+1}' for stnInfo in stnXyList])
            output = subprocess.run(f'export OMP_NUM_THREADS=1 && wgrib2 {modelPath} -match "APCP" -var {joined_ijlat}', shell=True ,capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as grepexc:                                                                                                   
            print("[ERROR] during wgrib2", grepexc.returncode, grepexc.output)
            return None
        list_output = output.stdout.split('\n')[:-1]
        if len(list_output) == 0:
            raise Exception(f'No data found in {modelPath}, {joined_ijlat}')
        
        targetDt = modelDt + timedelta(hours=step)
        for i, line in enumerate(list_output):
            line_split = line.split(':')
            for j, data in enumerate(line_split[3:]) :
                stn = stnXyList[j]['stn']
                data_split = data.split(',')[2:]
                prec_tot = float(data_split[2].split('=')[1])
                prec_tot = round(prec_tot, 2)
                pt = {
                    'stn' : stnXyList[j]['stn'],
                    'model_dt' : modelDt.strftime('%Y-%m-%d %H:%M:%S'),
                    'target_dt' : targetDt.strftime('%Y-%m-%d %H:%M:%S'),
                    'step' : step,
                    'prec' : prec_tot,
                    'x' : stnXyList[j]['x'],
                    'y' : stnXyList[j]['y'],
                }
                if stn not in rstData : 
                    rstData[stn] = []
                prec_tot = round(prec_tot, 2)
                rstData[stn].append(prec_tot)

    return rstData

