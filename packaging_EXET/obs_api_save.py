from datetime import datetime, timedelta, timezone
import os

import argparse
from urllib.request import urlopen
from urllib.request import HTTPError, URLError
from io import TextIOWrapper
import re
import _config as cfg


def saveObsData(obsCode, dt, dailySet) :
    '''
     Saves observed data to a text file

    Parameters:
    - obsCode (str): The observation code
    - dt (datetime): The date (KST)
    - dailySet (dict): A dictionary containing observed data for each station 
                       (key : station IDs, value : lists of hourly data) 
                       
    Returns:
        -None
    '''
    ymd = dt.strftime('%Y%m%d')
    txtFile = cfg.PATH_OBS_TXT.format(OBS=obsCode, YYYY=ymd[0:4], YYYYMMDD=ymd)
    txtFileDir = os.path.dirname(txtFile)
    if not os.path.isdir(txtFileDir) :
        os.makedirs(txtFileDir)

    cont = ""
    #stnCnt = 0
    for stnId in dailySet :
        cont += stnId.rjust(9)
        cont += ymd.rjust(9)
        for hIdx in range(0, 24) :
            #print(stnCnt, hIdx, stnId, dailySet[stnId][hIdx])
            if dailySet[stnId][hIdx] is None :
                cont += "         "
            else :
                cont += format(dailySet[stnId][hIdx], "9.1f")
        cont += "       =\n"
        #stnCnt += 1
    
    f = open(txtFile, 'w')
    f.write(cont)
    f.close()

    pass

def reqApiAsosData(dt) :
    '''
    Get ASOS data for the requested date and time from API.

    Parameters:
    - dt (datetime): requested date (KST)

    Returns:
    - dict: (key: station ID, value: precipitation ) 
            returns None if there is no data, False if there is an error
    '''
    tm = (dt+timedelta(hours=9)).strftime('%Y%m%d%H%M') # UTC to KST
    #print('proc ' + tm)
    saveKeys = [ 'STN', 'RN' ]
    keyIndexes = [None, None]
    lines = []
    try :
        url = "http://api.kma.go.kr/url/kma_sfctm.php?tm=" + tm + "&stn=0&help=0"
        #url = "http://10.2.10.65/fake_aws_api/asos.php?tm=" + tm + "&stn=0&help=0"
        resp = urlopen(url)
        #print(url)
        lines = TextIOWrapper(resp, encoding='euc-kr' ).readlines()
    except HTTPError as e :
        print("[ERROR] HTTP Error ", e.code)
        return False
    except URLError as e :
        print("[ERROR] URL Error ", e.reason)
        return False
    except Exception as e :
        print("[ERROR] Error ", e)
        return False    

    obsVals = {}
    isStarted = False
    for line in lines :
        if len(line) < 10 :
            continue
        if isStarted == False :
            if line[2:].startswith('YYMMDDHHMI') is True :
                isStarted = True
                header = re.split(r'\s+', line[2:])
                for i in range(len(saveKeys)) :
                    kn = saveKeys[i]
                    for j in range(len(header)) :
                        if kn == header[j] :
                            keyIndexes[i] = j
                            break
                    pass
                pass
            else :
                continue
            
        else :
            if line[0]=='#':
                continue
            tmp = re.split(r'\s+', line)
            row = {}
            for i in range(len(saveKeys)) :
                if len(tmp) < keyIndexes[i]+1 :
                    row[saveKeys[i]] = None
                    continue
                row[saveKeys[i]] = tmp[keyIndexes[i]]

            
            rn = None
            if row['RN'] != '-9.0' :
                rn = float(row['RN'])

            obsVals[row['STN']] = rn
        pass # end else isStarted
    return obsVals


def reqApiAwsData(dt) :
    '''
    Get AWS data for the requested date and time from API.

    Parameters:
    - dt (datetime): requested date (KST)

    Returns:
    - dict: (key: station ID, value: 1 hour precipitation ) 
            returns None if there is no data, False if there is an error
    '''
    tm = (dt+timedelta(hours=9)).strftime('%Y%m%d%H%M') # UTC to KST
    #print('proc ' + tm)
    saveKeys = [ 'STN', 'RN_HR1' ] # 원래
    keyIndexes = [None, None]
    lines = []
    try :
        # url = "http://api.kma.go.kr/url/awsh.php?tm=" + tm + "&stn=0&help=0"
        url = "https://apihub.kma.go.kr/api/typ01/url/awsh.php?tm=" + tm + "&help=1&authKey=-uv3O-FtR1Gr9zvhbYdRMA"
        #url = "http://10.2.10.65/fake_aws_api/aws.php?tm=" + tm + "&stn=0&help=0"
        resp = urlopen(url)
        #print(url)
        lines = TextIOWrapper(resp, encoding='euc-kr' ).readlines()
    except HTTPError as e :
        print("[ERROR] HTTP Error ", e.code)
        return False
    except URLError as e :
        print("[ERROR] URL Error ", e.reason)
        return False
    except Exception as e :
        print("[ERROR] Error ", e)
        return False    

    obsVals = {}
    isStarted = False
    for line in lines :
        if len(line) < 10 :
            continue
        if isStarted == False :
            if line[2:].startswith('YYMMDDHHMI') is True :
                isStarted = True
                header = re.split(r'\s+', line[2:])
                for i in range(len(saveKeys)) :
                    kn = saveKeys[i]
                    for j in range(len(header)) :
                        if kn == header[j] :
                            keyIndexes[i] = j
                            break
                    pass
                pass
            else :
                continue
            
        else :
            if line[0]=='#':
                continue
            tmp = re.split(r'\s+', line)
            row = {}
            for i in range(len(saveKeys)) :
                if len(tmp) < keyIndexes[i]+1 :
                    row[saveKeys[i]] = None
                    continue
                row[saveKeys[i]] = tmp[keyIndexes[i]]

            
            rn = None
            if row['RN_HR1'] != '-9.0' and row['RN_HR1'] != '-99.0' :
                rn = float(row['RN_HR1'])

            obsVals[row['STN']] = rn
        pass # end else isStarted
    return obsVals

if __name__ == '__main__' :

    parser = argparse.ArgumentParser()
    parser.add_argument('--obs', required=True, help='asos/aws')
    parser.add_argument('--start', required=True, help='yyyymmdd')
    parser.add_argument('--end', required=True, help='yyyymmdd')
    
    args = parser.parse_args()
    #print('aws', args.start, args.end)

    dtStart = None
    dtEnd = None
    dtStart = datetime.strptime(args.start, '%Y%m%d')
    dtEnd = datetime.strptime(args.end, '%Y%m%d')

    dt = dtStart
    while dt <= dtEnd :
        dailySet = {}
        for h in range(1,25) : # 01h~24h
            dt2 = dt + timedelta(hours=h)
            if args.obs == 'asos' :
                print("ASOS",dt2)
                stnVals = reqApiAsosData(dt2)
            elif args.obs == 'aws' : 
                print("AWS",dt2)
                stnVals = reqApiAwsData(dt2)
            else :
                print("wrong obs type : " + args.obs)
                break
            for stnId in stnVals :
                if stnId not in dailySet :
                    dailySet[stnId] = []
                    for i in range(h) : # 신규 지점?
                        dailySet[stnId].append(None)
                dailySet[stnId].append(stnVals[stnId])
            # API 상 관측데이터 누락?
            for stnId in dailySet :
                if stnId not in stnVals :
                    dailySet[stnId].append(None)
        saveObsData(args.obs, dt, dailySet)
        dt = dt + timedelta(days=1)
        
        