import os
from datetime import datetime, timedelta
import netCDF4

PATH_MODEL_FILE = '/ARCV/NWP/RAWD/MODL/RDPS/NE36/{YYYYMM}/{DD}/{HH}/rdps_fcst_{TYYYY}-{TMM}-{TDD}_{THH}'

# 지점별 데이터 추출
def model_extract(modelDt, interval, maxHour, stnXyList, tmpPath) :
    stnLastRains = {}
    rstData = {}
    for step in range(interval, maxHour+interval, interval) :
        targetDt = modelDt + timedelta(hours=step)
        modelPath = PATH_MODEL_FILE.format(YYYYMM=modelDt.strftime('%Y%m'), DD=modelDt.strftime('%d'), HH=modelDt.strftime('%H'),
        TYYYY=targetDt.strftime('%Y'), TMM=targetDt.strftime('%m'), TDD=targetDt.strftime('%d'), THH=targetDt.strftime('%H'))
        #print(modelPath)
        if not os.path.exists(modelPath) :
            print(f'[ERROR] Not found {modelPath}')
            return None

        ncfile = netCDF4.Dataset(modelPath, 'r', format='netcdf4')
        rainnc = ncfile['RAINNC'][0]
        rainc = ncfile['RAINC'][0]

        for stnInfo in stnXyList :
            x = stnInfo['x']
            y = stnInfo['y']
            stn = stnInfo['stn']
            #prec_tot = apcp[:][y][x]
            prec_tot = tmpVal = rainnc[y][x] + rainc[y][x]
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
        ncfile.close()
    
    return rstData