import os
from datetime import datetime, timedelta
import pygrib

PATH_MODEL_FILE = '/ARCV/NWP/GRIB/MODL/ECMW/T127/{YYYYMM}/{DD}{HH}/e025_v025_nhem_h{STEP}.{YYYYMM}{DD}{HH}00.gb1'

# 지점별 데이터 추출
def model_extract(modelDt, interval, maxHour, stnXyList, tmpPath) :
    
    stnLastRains = {}
    rstData = {}
    for step in range(interval, maxHour+interval, interval) :        
        modelPath = PATH_MODEL_FILE.format(YYYYMM=modelDt.strftime('%Y%m'), DD=modelDt.strftime('%d'), HH=modelDt.strftime('%H'), STEP=str(step).zfill(3))
        #print(modelPath)
        if not os.path.exists(modelPath) :
            print(f'[ERROR] Not found {modelPath}')
            return None

        targetDt = modelDt + timedelta(hours=step)

        grb = pygrib.open(modelPath)
        g = grb.select(name='Total precipitation')

        for stnInfo in stnXyList :
            x = stnInfo['x']
            y = stnInfo['y']
            stn = stnInfo['stn']
            prec_tot = tmpVal = g[0].values[y][x] * 1000 # change Unit from [m] to [mm])
            if interval != step : # 첫번째는 이전 스탭 강수량 없음
                prec_tot = tmpVal - stnLastRains[stn]         
            stnLastRains[stn] = tmpVal

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
        grb.close()

    return rstData
    
