import os
from datetime import datetime, timedelta
import netCDF4
import subprocess
import uuid


PATH_MODEL_FILE = '/ARCV/NWP/GRIB/MODL/GDPS/N128/{YYYYMM}/{DD}/g128_v070_ergl_unis_h{STEP}.{YYYYMM}{DD}{HH}.gb2'

# 지점별 데이터 추출
def model_extract(modelDt, interval, maxHour, stnXyList, tmpPath) :
    rstData = {}
    for step in range(interval, maxHour+interval, interval) :        
        modelPath = PATH_MODEL_FILE.format(YYYYMM=modelDt.strftime('%Y%m'), DD=modelDt.strftime('%d'), HH=modelDt.strftime('%H'), STEP=str(step).zfill(3))
        #print(modelPath)
        if not os.path.exists(modelPath) :
            print(f'[ERROR] Not found {modelPath}')
            return None

        tmpModelPath = tmpPath + '/' + str(uuid.uuid4()).replace('-', '') + '.nc'
        try :
            subprocess.run(f'wgrib2 {modelPath} -match "APCP" -netcdf {tmpModelPath}', shell=True ,capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as grepexc:                                                                                                   
            print("[ERROR] during wgrib2nc", grepexc.returncode, grepexc.output)
            if os.path.exists(tmpModelPath) :
                try :
                    os.remove(tmpModelPath)
                except Exception as e:
                    print("[WARN] Error during remove gdps_n128 temp file")
                    print(e)
            return None

        targetDt = modelDt + timedelta(hours=step)
        ncfile = netCDF4.Dataset(tmpModelPath, 'r', format='netcdf4')
        apcp = ncfile['APCP_surface'][0][:]
    
        for stnInfo in stnXyList :
            x = stnInfo['x']
            y = stnInfo['y']
            stn = stnInfo['stn']
            prec_tot = apcp[y][x]
            pt = {
                'stn' : stn,
                'model_dt' : modelDt.strftime('%Y-%m-%d %H:%M:%S'),
                'target_dt' : targetDt.strftime('%Y-%m-%d %H:%M:%S'),
                'step' : step,
                'prec' : prec_tot
            }
            #print(pt)
            #if pt['prec'] is None : continue
            #pt['prec'] = round(pt['prec'], 2)
            #if pt['prec'] == 0 : continue

            #insertDatas.append(pt)
            if stn not in rstData : 
                rstData[stn] = []
            prec_tot = round(prec_tot, 2)
            rstData[stn].append(prec_tot)
        ncfile.close()
        try :
            os.remove(tmpModelPath)
        except Exception as e:
            print("[WARN] Error during remove gdps_n128 temp file")
            print(e)
            pass
    
    return rstData

