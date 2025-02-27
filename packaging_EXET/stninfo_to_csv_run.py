from datetime import datetime, timedelta, timezone
import sqlite3
import os
import csv
import pandas as pd
import hashlib


import argparse
from urllib.request import urlopen
from urllib.request import HTTPError, URLError
from io import TextIOWrapper
import re
import _config as cfg 
import numpy as np


def read_lines(dt, api_url):
    tm = (dt+timedelta(hours=9)).strftime('%Y%m%d%H%M')
    lines = []
    try :
    
        url = api_url + tm + "&help=1&authKey=VsCrv8PCThmAq7_Dwp4ZGA"
        print(url)
        resp = urlopen(url)
        lines = TextIOWrapper(resp, encoding='euc-kr' ).readlines()
        return lines
    except HTTPError as e :
        print("[ERROR] HTTP Error ", e.code)
        return False
    except URLError as e :
        print("[ERROR] URL Error ", e.reason)
        return False
    except Exception as e :
        print("[ERROR] Error ", e)
        return False    


def make_obs_stn_csv(save_dir, points):
    
    dir_path = os.path.dirname(save_dir)
    os.makedirs(dir_path, exist_ok=True)
    try:
        with open(save_dir, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=['dt', 'id', 'lon', 'lat', 'ht'])
            writer.writeheader()  # Write the header
            for pt in points:
                writer.writerow(pt)  # Write each pt as a row

        return points   
    
    except Exception as e:
        print("[ERROR] Error saving to text file: ", e)
        return False

def reqApiAsosInfoData(dt) : 
    '''
    Get ASOS data and save to csv file.
    
    Parameters:
    - dt(datetime): The datetime for which to request the ASOS station information

    Returns:
    - list: station information, 
            False if an error occurs during the API request.
    '''
    api_url = "https://apihub.kma.go.kr/api/typ01/url/stn_inf.php?inf=SFC&stn=&tm="
    lines = read_lines(dt, api_url)
    strDt = dt.strftime('%Y-%m-%d')
    points = []
    save_dir = cfg.PATH_OBS_STN.format(YYYY=strDt[0:4], YYYYMMDD=strDt, OBS='asos') #PATH_OBS_STN =  ../DAIN/STN/stn_{YYYYMMDD}_{OBS}.csv 으로 설정파일에 
    if lines ==False:
        print("[ERROR] Error ")
        return False
    
    for line in lines :
        if len(line) < 60 :
            continue
        if line[0]=='#':
            continue
        #    90  128.56473000   38.25085000 41211210     17.53     10.00 4090 105 속초                 ----                 11D20402 5182033035  282
        pt = {
            'dt' : strDt,
            'id' : line[0:5].strip(),
            'lon' : float(line[5:19].strip()),
            'lat' : float(line[19:33].strip()),
            'ht' : float(line[43:52].strip()),
        }
        points.append(pt)
            
    points = make_obs_stn_csv(save_dir, points)
    return points
        


def reqApiAwsInfoData(dt) :
    '''
    Requests AWS information from API and save to csv file.

    Parameters:
    - dt(datetime): The datetime for which to request the AWS station information

    Returns:
    - list: station information, 
            False if an error occurs
    '''
    api_url = "https://apihub.kma.go.kr/api/typ01/url/stn_inf.php?inf=AWS&stn=&tm="
    lines = read_lines(dt, api_url)
    strDt = dt.strftime('%Y-%m-%d')
    points = []
    save_dir = cfg.PATH_OBS_STN.format(YYYY=strDt[0:4],YYYYMMDD=strDt, OBS='aws')
    if lines ==False:
        print("[ERROR] Error ")
        return False
    
    for line in lines :
        if len(line) < 60 :
            continue
        if line[0]=='#':
            continue
        #    90  128.56473000   38.25085000 41211210     17.53     10.00 4090 105 속초                 ----                 11D20402 5182033035  282
        pt = {
            'dt' : strDt,
            'id' : line[0:5].strip(),
            'lon' : float(line[6:19].strip()),
            'lat' : float(line[20:33].strip()),
            'ht' : float(line[44:52].strip()),
        }
        points.append(pt)
        
    points = make_obs_stn_csv(save_dir, points)
    return points


################################gts observation station list
def reqApiGtsInfoData(dt) :
    '''
    Requests GTS information from API and save to csv file.

    Parameters:
    - dt(datetime): The datetime for which to request the AWS station information

    Returns:
    - list: station information, 
            False if an error occurs
    '''
    api_url = "https://apihub.kma.go.kr/api/typ01/url/stn_gts1.php?tm="
    lines = read_lines(dt, api_url)
    strDt = dt.strftime('%Y-%m-%d')
    points = []
    save_dir = cfg.PATH_OBS_STN.format(YYYY=strDt[0:4], YYYYMMDD=strDt, OBS='gts')
    if lines ==False:         
        print("[ERROR] Error ")
        return False
    
    for line in lines :
        if len(line) < 60 :
            continue
        if line[0]=='#':
            continue
        #    90  128.56473000   38.25085000 41211210     17.53     10.00 4090 105 속초                 ----                 11D20402 5182033035  282
        # 60001 0  -17.88888889   27.81888889   32 -   32 - - 
        pt = {
            'dt' : strDt,
            'id' : line[0:5].strip(),
            'lon' : float(line[7:21].strip()),
            'lat' : float(line[22:35].strip()),
            'ht' : float(line[36:40].strip()),
        }
        points.append(pt)
        
    points = make_obs_stn_csv(save_dir, points)
    return points

##############################################################################################




def find_nearest_point(olat, olon, mlats, mlons):
   '''
   Finds the nearest grid point in latitude and longitude to a given observation point
   
   Parameters:
   - olat(float)            : latitude of obs (0d)
   - olon(float)            : longitude of obs (0d)
   - mlats(numpy.ndarray)   : latitude of grid (1d)                                    
   - mlons(numpy.ndarray)   : longitude of grid (1d)
   
   Returns:
   - tuple: containing
            - int: Index of the nearest latitude point in the grid (y-coordinate)
            - int: Index of the nearest longitude point in the grid (x-coordinate)
            - float: Latitude of the nearest grid point
            - float: Longitude of the nearest grid point
   '''
   diff = (olon - mlons)**2. + (olat - mlats)**2.
   #print(diff)
   ypos, xpos = np.unravel_index(np.argmin(diff), diff.shape)
   #ypos, xpos = np.unravel_index(np.abs(diff).argmin(), diff.shape)
   
   return int(ypos), int(xpos), mlats[ypos, xpos], mlons[ypos, xpos]


def loadModelGrid(modelCode) :
    '''
    Loads the grid latitude and longitude data for a specified model from a .npz file
    
    Parameters:
    - modelCode (str): Model code
    
    Returns:
    - numpy.ndarray or bool 
            - A numpy array containing the grid latitude and longitude data if the file exists
            - False if the grid file does not exist
    '''
    modelGridNpzFile = cfg.PATH_DABA + '/grid_latlon_' + modelCode + '.npz'
    if os.path.exists(modelGridNpzFile) == False :
        print('[ERROR] grid file not exists. ' + modelGridNpzFile)
        return False
    gridLatlon = np.load(modelGridNpzFile, allow_pickle = True)
    
    return gridLatlon













def model_station_info(dt, obscode, modelcode):
    '''
    
    
    Parameters:
    - dt (datetime) : datetime to decide station info.
    - obscode (str) : observation code like 'aws', 'asos'
    - modelCode (str): Model code
    
    Returns:
    - dict : 
    '''
    ymd = dt.strftime('%Y-%m-%d')
    obs_stn_info =[]
    modelStnInfos={}
    
    if obscode == 'aws':
        obs_stn_info = reqApiAwsInfoData(dt)
        
    
#     '''
#     이런식으로 생겼음
#     [
#     {'dt': '2024-10-17', 'id': '41211', 'lon': 128.56473, 'lat': 38.25085, 'ht': 17.53},
#     {'dt': '2024-10-17', 'id': '51820', 'lon': 128.60000, 'lat': 38.30000, 'ht': 20.00},
#     ...]
# ]
#     '''


    if obscode == 'asos':
        obs_stn_info = reqApiAsosInfoData(dt)
        
    if obscode == 'gts':
        obs_stn_info = reqApiGtsInfoData(dt)
    
    
    gridLatlon = loadModelGrid(modelcode) #모델의 격자 latlon을 가져 온다. 
    
    # 관측 지점 리스트인 obs_stn_info가 나온다
    # 그러면 만일 기존 xyfile = cfg.PATH_MODEL_STNXY.format(MODEL=modelCode, OBS=obsCode, YYYY=dt.strftime('%Y'))에 id리스트랑 비교.
      
    
    for stn in obs_stn_info: #하나의 스테이션에 대해서 가장 가까운 격자점을 찾는다.
        
        stnId = stn['id']
        # print(stnId) 
        y, x, mlat, mlon = find_nearest_point(float(stn['lat']), float(stn['lon']), gridLatlon['lats'], gridLatlon['lons'] )
        #여기서 - 모델의 격자 중 가장 가까운 지점의 y,x 인덱스와, 그 가장 가까운 관측소의 아이디, 랫롱 반환됨 
        newRow = {'model':modelcode, 'id': stnId, 'x':x, 'y':y, 'lon':stn['lon'], 'lat':stn['lat'], 'dt':ymd}
        modelStnInfos[newRow['id']] = newRow
    
    return modelStnInfos    



def writeXyCsv(obsCode, modelCode, stnInfos, dt) :
    '''
    Writes station information to a CSV file, Optionally creates a separate file if changes are detected

    Parameters:
    - obsCode(str): Observation code
    - modelCode(str): Model code
    - stnInfos(dict): station information
    - dt(datetime): Date and time

    Returns:
    - bool: True if the file was written successfully, False otherwise
    '''
    cont = ""
    cont += "stnId,lat,lon,x,y\n"######### 헤더 추가 
    for stnId in stnInfos :
        stnXyInfo = stnInfos[stnId]
        cont += f"{stnXyInfo['id']},{stnXyInfo['lat']},{stnXyInfo['lon']},{stnXyInfo['x']},{stnXyInfo['y']}\n"

    xyfile = cfg.PATH_MODEL_STNXY.format(MODEL=modelCode, OBS=obsCode, YYYY=dt.strftime('%Y'))
    if os.path.exists(xyfile) :
        os.remove(xyfile)
    xyfileDir = os.path.dirname(xyfile)
    if not os.path.isdir(xyfileDir) :
        try :
            os.makedirs(xyfileDir)
        except Exception as e :
            print("[ERROR] Error ", e)
            return False

    f = open(xyfile, 'w')
    f.write(cont)
    f.close()


    pass


            

def hash_dataframe(df):
    return hashlib.sha256(pd.util.hash_pandas_object(df, index=True).values).hexdigest()


#######################
if __name__ == '__main__' :
    szModelCodes = ""
    for modelCode in cfg.modelConf :
        if szModelCodes != "" :
            szModelCodes += ","
        szModelCodes += modelCode


    parser = argparse.ArgumentParser()
    parser.add_argument('--dt', required=True, help='now or yyyymmdd or yyyymmddhh')
    parser.add_argument('--model', required=True, help='comma seperated model codes. eg. ' + szModelCodes)
    parser.add_argument('--obs', required=True, help='comma seperated obs codes. eg. asos,aws')

    args = parser.parse_args()

    modelCodes = args.model.split(',')
    obsCodes = args.obs.split(',')

    
    dt = None
            
    if args.dt == 'now' :
        now = datetime.now(timezone.utc)
        tmp = now.strftime('%Y%m%d') + '0000'
        dt = datetime.strptime(tmp, '%Y%m%d')
    else :
        if len(args.dt) >= 6 :
            dt = datetime.strptime(args.dt[0:8]+'0000', '%Y%m%d%H%M')
        else :
            print('datetime format error. ')
            exit(1)


    for obsCode in obsCodes :
        stnApiList = None
        if obsCode == 'asos' :
            stnApiList = reqApiAsosInfoData(dt)
        elif obsCode == 'aws' : 
            stnApiList = reqApiAwsInfoData(dt)
        elif obsCode == 'gts':
            stnApiList = reqApiGtsInfoData(dt)
        else :
            continue
        
        for modelCode in modelCodes :
            
            xyfile = cfg.PATH_MODEL_STNXY.format(MODEL=modelCode, OBS=obsCode)
            
            if not os.path.exists(xyfile): 
                
                print(f"File does not exist: {xyfile}, file writing.")
                modelStnInfos= model_station_info(dt, obsCode, modelCode)
                writeXyCsv(obsCode, modelCode, modelStnInfos, dt)
                
                
            else: 
                print(f"File exists: {xyfile}, comparing content.")
                
                existingData = pd.read_csv(xyfile, usecols=['stnId', 'lat', 'lon'], dtype={'stnId': int})
                stnApiList_df = pd.DataFrame(stnApiList)
                stnApiList_df = stnApiList_df.rename(columns={'id': 'stnId', 'lat': 'lat', 'lon': 'lon'})
                stnApiList_df = stnApiList_df[['stnId', 'lat', 'lon']]  # 필요한 열만 선택
                stnApiList_df['stnId'] = stnApiList_df['stnId'].astype(int)
                
                
            # 두 데이터프레임의 해시값 비교
            if hash_dataframe(existingData) != hash_dataframe(stnApiList_df):
                print(f"Changes detected, updating file: {xyfile}")
                modelStnInfos = model_station_info(dt, obsCode, modelCode)
                writeXyCsv(obsCode, modelCode, modelStnInfos, dt)
            else:
                print(f"No changes detected, skipping file update: {xyfile}")

               

    print('Station Data processed.')    
               
           
