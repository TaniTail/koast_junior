import os
import numpy as np
from datetime import datetime, timedelta
# import netCDF4

PATH_MODEL_FILE = '/ARCV/NWP/RAWD/MODL/GDPS/NE36/{YYYYMM}/{DD}/{HH}/ERLY/FCST/post/sfc.ft{STEP}.nc'

# 지점별 데이터 추출
def model_extract(modelDt, interval, maxHour, stnXyList, tmpPath) :
    rstData = {}
    
    grid_size_y = 2880# 격자 수
    grid_size_x = 1440
    
    
    
    
    
    for step in range(interval, maxHour+interval, interval) :  
        
        
        ##########################################################################
    
        # modelPath = PATH_MODEL_FILE.format(YYYYMM=modelDt.strftime('%Y%m'), DD=modelDt.strftime('%d'), HH=modelDt.strftime('%H'), STEP=str(step).zfill(3))
        # #print(modelPath)
        # if not os.path.exists(modelPath) :
        #     print(f'[ERROR] Not found {modelPath}')
        #     return None
        
        precc = np.random.rand(grid_size_y, grid_size_x)  # 랜덤 배열 (2차원 배열!)
        precl = np.random.rand(grid_size_y, grid_size_x)  # 랜덤 배열

        targetDt = modelDt + timedelta(hours=step)
        
        
        
        # 더미파일 만들기 
        
        # ncfile = netCDF4.Dataset(modelPath, 'r', format='netcdf4')
        # precc = ncfile['precc'][0][:]
        # precl = ncfile['precl'][0][:]
        ####################################################################################



        for stnInfo in stnXyList :
            x = stnInfo['x']
            y = stnInfo['y']
            stn = stnInfo['stn']
            # prec_tot = precc[y][x] + precl[y][x]
            prec_tot = precc[y][x] + precl[y][x]
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
            if stn not in rstData : 
                rstData[stn] = []
            prec_tot = round(prec_tot, 2)
            rstData[stn].append(prec_tot)

            #insertDatas.append(pt)
        # ncfile.close() # 더미 파일 하면서 해시친 부분임
    
    return rstData
    