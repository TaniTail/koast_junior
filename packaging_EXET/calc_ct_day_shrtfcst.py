#import json
from datetime import datetime, timedelta
import os
import sqlite3
import argparse
import math
import _config as cfg

# 단기예보기준 검증 규칙에 따라 72h/120h 이상 예측 모델만 검증 가능

class CalcContingencyDayShrtFcst:
    maxFcstHours = [72, 120]
    modelIdxs = {
        72 : { # 최대 예측 시간 72h
            3 : { # 임계시간 3h
                -24 : { # 모델 발표일시
                    # 단기예보 발표일시 : 모델 예측 시간 인덱스(셀번호)
                    2  : [6,7,8,9,10,11,12,13,14,15,16,17,18,19,20] # 모델 예보시각 / 임계시간 = 셀번호
                },
                -12 : {
                    5  : [  7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28], # 예보관 발표시각 별 사용할 모델 예보시각 3시
                    8  : [    8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28], # 예보관 발표시각 별 사용할 모델 예보시각 6시
                    11 : [      9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28], # 예보관 발표시각 별 사용할 모델 예보시각 9시
                    14 : [        10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28] # 예보관 발표시각 별 사용할 모델 예보시각 12시
                },
                0 : {
                    17 : [           11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28],
                    20 : [              12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28],
                    23 : [                 13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28]
                }
            },
            6 : {
                -24 : {
                    2  : [3,4,5,6,7,8,9]
                },
                -12 : {
                    5  : [3,4,5,6,7,8,9,10,11,12,13],
                    8  : [  4,5,6,7,8,9,10,11,12,13],
                    11 : [    5,6,7,8,9,10,11,12,13],
                    14 : [      6,7,8,9,10,11,12,13]
                },
                0 : {
                    17 : [    5,6,7,8,9,10,11,12,13],
                    20 : [      6,7,8,9,10,11,12,13],
                    23 : [        7,8,9,10,11,12,13]
                }
            },
            12 : {
                -24 : {
                    2  : [1,2,3,4]
                },
                -12 : {
                    5  : [1,2,3,4,5,6],
                    8  : [  2,3,4,5,6],
                    11 : [  2,3,4,5,6],
                    14 : [  2,3,4,5,6]
                },
                0 : {
                    17 : [  2,3,4,5,6],
                    20 : [    3,4,5,6],
                    23 : [    3,4,5,6]
                }
            }
        },
        120 : { # 최대 예측 시간 120h
            3 : { # 임계시간 3h
                -24 : { # 발표시각
                    2  : [6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36] # 모델 예보시각 / 임계시간 = 셀번호
                },
                -12 : {
                    5  : [  7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44], # 예보관 발표시각 별 사용할 모델 예보시각 3시
                    8  : [    8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44], # 예보관 발표시각 별 사용할 모델 예보시각 6시
                    11 : [      9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44], # 예보관 발표시각 별 사용할 모델 예보시각 9시
                    14 : [        10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44] # 예보관 발표시각 별 사용할 모델 예보시각 12시
                },
                0 : {
                    17 : [           11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44],
                    20 : [              12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44],
                    23 : [                 13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44]
                }
            },
            6 : {
                -24 : {
                    2  : [3,4,5,6,7,8,9,10,11,12,13,14,15,16,17]
                },
                -12 : {
                    5  : [3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21],
                    8  : [  4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21],
                    11 : [    5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21],
                    14 : [      6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21]
                },
                0 : {
                    17 : [    5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21],
                    20 : [      6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21],
                    23 : [        7,8,9,10,11,12,13,14,15,16,17,18,19,20,21]
                }
            },
            12 : {
                -24 : {
                    2  : [1,2,3,4,5,6,7,8]
                },
                -12 : {
                    5  : [1,2,3,4,5,6,7,8,9,10,11],
                    8  : [  2,3,4,5,6,7,8,9,10,11],
                    11 : [  2,3,4,5,6,7,8,9,10,11],
                    14 : [  2,3,4,5,6,7,8,9,10,11]
                },
                0 : {
                    17 : [  2,3,4,5,6,7,8,9,10,11],
                    20 : [    3,4,5,6,7,8,9,10,11],
                    23 : [    3,4,5,6,7,8,9,10,11]
                }
            }
        }
    }
    # frameObsIdxs = None
    # frameModelIdxs = None
    def __init__(self) -> None:

        pass

    def GetDayObs(self, targetDay, thresholdHour, stnIds, obsCode, maxFcstHour) -> dict:
        '''
        Calculates and returns the Observed Accumulative Precipitation for the given date, thresholdHour
        
        Parameters:
        - targetDay(datetime): date (KST)
        - thresholdHour(int): Time to determine the prediction interval
        - stnIds(list): Station Id list
        - obsCode(str): Observation code (aws, asos)
        - maxFcstHour(int): max forecasting hour

        Returns:
        - dict: Observed Accumulative precipitation by section for each station
        '''
        # targetDay : 예보관관점(강수예보평가기준)은 KST 이나 ymd만 입력받아 사용하므로 이미 UTC로 변환된 셈
        
        # 예보 시간 및 관측 시간을 저장할 리스트 초기화
        frameObsIdxs = []
        
        # 예보 시간 및 발행 시간을 기준으로 관측 구간을 설정
        for modelBaseT in self.modelIdxs[maxFcstHour][thresholdHour] :
            for pubTm in self.modelIdxs[maxFcstHour][thresholdHour][modelBaseT] :
                for s in self.modelIdxs[maxFcstHour][thresholdHour][modelBaseT][pubTm] :
                    # 새로운 관측 시간 구간을 리스트에 추가
                    if s not in frameObsIdxs :
                        frameObsIdxs.append(s)    
        
        # 각 관측소별로 관측 데이터를 저장할 사전 초기화
        obs = {}
        for stn in stnIds :
            obs[stn] = {}
            for s in frameObsIdxs :
                obs[stn][s] = 0 # 초기값을 0으로 설정

        #targetDtUTCStart = targetDay - timedelta(hours=(min(frameObsIdxs)+1)*thresholdHour)
        
        # 기준 시간을 설정하여 관측 기간을 계산
        targetDtUTCStart = targetDay - timedelta(days=1) # 기준일 하루 전부터 시작
        targetDtUTCEnd = targetDtUTCStart + timedelta(hours=max(frameObsIdxs)*thresholdHour)
        

        # 파일에서 읽어올 UTC 시간 범위를 계산
        fileDtUTC = datetime(targetDtUTCStart.year, targetDtUTCStart.month, targetDtUTCStart.day)
        fileDtUTCEnd = datetime(targetDtUTCEnd.year, targetDtUTCEnd.month, targetDtUTCEnd.day)
        
        # 관측 데이터를 파일에서 읽어들이는 루프
        while fileDtUTC <= fileDtUTCEnd :
            #ymd = fileDtUTC.strftime('%Y%m%d')
            #txtFile = cfg.PATH_OBS_TXT.format(OBS=obsCode, YYYY=ymd[0:4], YYYYMMDD=ymd)
            
            # 파일 이름을 구성 (연도와 날짜 정보 포함)
            txtFile = cfg.PATH_OBS_TXT.format(OBS=obsCode, YYYY=fileDtUTC.strftime('%Y'), YYYYMMDD=fileDtUTC.strftime('%Y%m%d'))
            
        
           # 파일이 존재하는지 확인하고 없으면 에러 출력 후 종료
            if os.path.exists(txtFile) == False :
                print('GetDayObs - File not found - ' + txtFile)
                return False

            # 파일을 열고 데이터를 읽어옴
            f = open(txtFile, 'r')
            while True :
                line = f.readline()
                if not line : break # 파일의 끝에 도달하면 종료
                if len(line) < 242 : continue # stnId:9,dt:9,rn:9*24,=:8 # 데이터가 유효한지 확인 (길이가 충분한지)
                stn = int(line[0:9]) # 관측소 ID 추출
                if stn not in stnIds : # 해당 관측소가 관심 리스트에 없으면 무시
                    continue
                
                 # 각 시간별로 데이터를 처리
                for hIdx in range(0,24) :
                    pos = 18 + (hIdx * 9) # 각 시간 데이터의 위치 계산
                    tmp = line[pos:pos+9].strip() # 관측된 강수량 데이터 추출
                    rn = None
                    if len(tmp) < 1 : continue
                    rn = float(tmp) # 강수량 데이터를 실수형으로 변환
                    hour = hIdx + 1 # 1h ~ 24h # 시간 값을 1~24 시간 범위로 변환
                    obsDtUTC = fileDtUTC + timedelta(hours=hour) # 관측 시간을 UTC로 변환
                    
                     # 기준 시작 시간과의 차이를 시간 단위로 계산
                    gap = (obsDtUTC - targetDtUTCStart).total_seconds() / 3600
                    si = math.ceil( gap / thresholdHour) - 1 # idx 는 3가 0으로 시작 # 관측 구간 인덱스 계산
                    
                    # 해당 구간이 유효한지 확인
                    if si not in obs[stn] :
                        continue
                    #print(thresholdHour, stn, hour, obsDtUTC, targetDtUTCStart, gap, si)
                    
                    # 관측된 강수량 데이터를 해당 구간에 더해줌
                    obs[stn][si] += round(rn, 1)
                    obs[stn][si] = round(obs[stn][si], 1)
            f.close() #파일 닫기
            fileDtUTC = fileDtUTC + timedelta(days=1) # 다음 날짜로 이동

        return obs # 결과 반환
    
    def GetDayModel(self, targetDay, thresholdHour, stnIds, modelCode, obsCode, maxFcstHour) -> dict:
        '''
        Calculates and returns the Model predicted Accumulative Precipitation for the given date, thresholdHour
        
        Parameters:
        - targetDay(datetime): date (KST)
        - thresholdHour(int): Time to determine the prediction interval
        - stnIds(list): Station Id list
        - modelCode(str): model code
        - obsCode(str): Observation code (aws, asos)
        - maxFcstHour(int): max forecasting hour

        Returns:
        - dict: Model Predicted Accumulative Precipitation by section for each station
        '''
        
        # targetDay : 예보관관점(강수예보평가기준)은 KST 이나 ymd만 입력받아 사용하므로 추가 변환 안함
        frameModelIdxs = {}
        for modelBaseT in self.modelIdxs[maxFcstHour][thresholdHour] :
            frameModelIdxs[modelBaseT] = []
            for pubTm in self.modelIdxs[maxFcstHour][thresholdHour][modelBaseT] :
                for s in self.modelIdxs[maxFcstHour][thresholdHour][modelBaseT][pubTm] :
                    if s not in frameModelIdxs[modelBaseT] :
                        frameModelIdxs[modelBaseT].append(s)

        modelSum = {}
        for stn in stnIds :
            modelSum[stn] = {}
            for modelBaseT in frameModelIdxs :
                modelSum[stn][modelBaseT] = {}
                for s in frameModelIdxs[modelBaseT] :
                    modelSum[stn][modelBaseT][s] = None

        for modelBaseT in frameModelIdxs :
            
            modelFcstMaxHour = max(frameModelIdxs[modelBaseT]) * thresholdHour
            modelDtBase = targetDay + timedelta(hours=modelBaseT)

            #targetDtUTCStart = targetDay - timedelta(hours=(min(frameModelIdxs[modelBaseT])+1)*thresholdHour)
            targetDtUTCStart = targetDay - timedelta(days=1)
            #targetDtUTCEnd = targetDtUTCStart + timedelta(hours=max(frameModelIdxs[modelBaseT])*thresholdHour)

            txtFile = cfg.PATH_MODEL_EXTRACT_TXT.format(MODEL=modelCode, OBS=obsCode, YYYY=modelDtBase.strftime('%Y'), YYYYMMDDHH=modelDtBase.strftime('%Y%m%d%H'))
            if os.path.exists(txtFile) == False :
                print('GetDayModel - File not found - ' + txtFile)
                return False

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
                if len(tmp2)<2 : continue
                k1 = tmp2[0]
                v1 = tmp2[1]
                if k1 == 'fcstInterval' or k1 == 'fcstMaxHour' :
                    v1 = int(v1)
                info[k1] = v1
            
            
            if modelFcstMaxHour > info['fcstMaxHour'] :
                print('GetDayModel - not enough ft - ' + str(modelFcstMaxHour) + '/' + str(info['fcstMaxHour']) + ' : ' + txtFile)
                return False
            if thresholdHour < info['fcstInterval'] :
                print('GetDayModel - file interval is bigger then thresholdHour - ' + str(thresholdHour) + '/' + str(info['fcstInterval']) + ' : ' + txtFile)
                return False
            if thresholdHour % info['fcstInterval'] != 0 :
                print('GetDayModel - thresholdHour is not multiples of file fcstInterval - ' + str(thresholdHour) + '/' + str(info['fcstInterval']) + ' : ' + txtFile)
                return False

            info['model_dt'] = datetime.strptime(info['ymdh'], '%Y%m%d%H')
            # szModelDt = info['model_dt'].strftime("%Y-%m-%d %H:%M:%S")

            #print('modelFile : ' + info['ymdh'] + ', ModelBaseT : ' + str(modelBaseT))
            while True :
                line = f.readline()
                if not line : break
                if len(line) < 6 : continue
                if line[0] == '#' : continue
                stn = int(line[0:6])
                if stn not in stnIds :
                    continue
                for step in range(info['fcstInterval'], modelFcstMaxHour+info['fcstInterval'], info['fcstInterval']) :
                    stepDtUTC = info['model_dt'] + timedelta(hours=step)
                    #gap = (stepDtUTC - targetDtUTCStart + timedelta(hours=modelBaseT)).total_seconds() / 3600
                    #gap = gap + modelBaseT
                    gap = (stepDtUTC - targetDtUTCStart).total_seconds() / 3600
                    si = math.ceil( gap / thresholdHour) - 1 # idx 는 3가 0으로 시작

                    #print(thresholdHour, stn, info['ymdh'], step, sIdx, tmp, modelBaseT, targetDtUTCStart, gap, stepDtUTC, si)
                    #continue

                    if si not in frameModelIdxs[modelBaseT] :
                        continue

                    sIdx = int(step / info['fcstInterval'])
                    pos = 6 + 2 + ((sIdx-1) * 7)
                    tmp = line[pos:pos+7].strip()


                    if len(tmp) < 1 : continue
                    rn = float(tmp)
                    if modelSum[stn][modelBaseT][si] is None :
                        modelSum[stn][modelBaseT][si] = 0
                    modelSum[stn][modelBaseT][si] += round(rn, 2)
                    modelSum[stn][modelBaseT][si] = round(modelSum[stn][modelBaseT][si], 2)

                    #print(thresholdHour, stn, info['ymdh'], step, sIdx, tmp, modelBaseT, targetDtUTCStart, gap, stepDtUTC, si)
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


    def CalcContingency(self, targetDay, thresholdHour, stnIds, modelCode, obs, model, maxFcstHour) -> dict:
        '''
        Calculates Contingency table with Observed Accumulative Precipitation and Model Predicted Accumulative Precipitation
        
        Parameters:
        - targetDay(datetime): date (KST)
        - thresholdHour(int): Time to determine the prediction interval
        - stnIds(list): Station Id list
        - modelCode(str): model code
        - obs(dict): Observed Accumulative Precipitation by section for each station
        - model(dict): Model Predicted Accumulative Precipitation by section for each station
        - maxFcstHour(int): max forecasting hour

        Returns:
        - dict: Contingency table
        '''
        # modelSum[stn][modelBaseT][si]
        # obs[stn][si]

        #dtStart = targetDay - timedelta(hours=modelFcstMaxHour)
        #dtEnd = targetDay + timedelta(days=1) - timedelta(hours=thresholdHour)

        ct = {}
        for mm in cfg.thresholdMms:
            szMm = format(mm, ".1f")
            ct[szMm] = {}
            for stn in stnIds:
                stnVals = {}
                # for s in ss :
                #     stnVals[str(s)] = {'h':0, 'f':0, 'm':0, 'z':0, 't':0}

                for modelBaseT in self.modelIdxs[maxFcstHour][thresholdHour] :
                    for pubTm in self.modelIdxs[maxFcstHour][thresholdHour][modelBaseT] :
                        for si in self.modelIdxs[maxFcstHour][thresholdHour][modelBaseT][pubTm] :
                            
                            modelV = model[stn][modelBaseT][si]
                            obsV = obs[stn][si]
                            if modelV is None :
                                modelV = 0
                            if obsV is None :
                                obsV = 0

                            ft = True if modelV >= mm else False
                            ob = True if obsV >= mm else False

                            szS = str(pubTm)
                            if szS not in stnVals :
                                stnVals[szS] = {'h':0, 'f':0, 'm':0, 'z':0, 't':0}
                            rstCode = 'z'
                            if ft is True and ob is True: rstCode = 'h'
                            elif ft is False and ob is True: rstCode = 'm'
                            elif ft is True and ob is False: rstCode = 'f'
                            elif ft is False and ob is False: rstCode = 'z'
                            # else :
                            #     print('what ??', mm, modelV, obsV, ft, ob)
                            stnVals[szS][rstCode] += 1
                            stnVals[szS]['t'] += 1
                # print(stn)
                # print(stnVals)
                ct[szMm][stn] = stnVals
        return ct
    

    def SaveContingencyDay(self, targetDay, thresholdHour, stnIds, modelCode, obsCode, ct, maxFcstHour) :       
        '''
        Store Contingency table of targetDay data from each observation point in a database
        
        Parameters:
        - targetDay(datetime): date (KST)
        - thresholdHour(int): Time to determine the prediction interval
        - stnIds(list): Station Id list
        - modelCode(str): model code
        - obsCode(str): Observation code
        - ct(dict): Contingency table
        - maxFcstHour(int): max forecasting hour

        Returns:
        - None       
        '''         
    
        ss = []
        for modelBaseT in self.modelIdxs[maxFcstHour][thresholdHour] :
            for pubTm in self.modelIdxs[maxFcstHour][thresholdHour][modelBaseT] :
                ss.append(pubTm)

        insertDatas = []
        for mm in cfg.thresholdMms:
            szMm = format(mm, ".1f")
            for s in ss :
                for stn in stnIds :
                    row = {
                        'd' : targetDay.strftime('%Y-%m-%d'),
                        's' : s,
                        'th_hour' : thresholdHour,
                        'mm' : szMm,
                        'stn' : stn,
                        'h' : ct[szMm][stn][str(s)]['h'],
                        'f' : ct[szMm][stn][str(s)]['f'],
                        'm' : ct[szMm][stn][str(s)]['m'],
                        'z' : ct[szMm][stn][str(s)]['z'],
                        't' : ct[szMm][stn][str(s)]['t']
                    }
                    #print(row)
                    insertDatas.append(row)
        dbFile = cfg.PATH_CT_DAILY_DB_ADDTIONAL.format(MODEL=modelCode, OBS=obsCode, YYYY=targetDay.strftime('%Y'), YYYYMM=targetDay.strftime('%Y%m'), ADD_CODE='shrt')
        dbFileDir = os.path.dirname(dbFile)
        if not os.path.isdir(dbFileDir) :
            os.makedirs(dbFileDir)

        conn = sqlite3.connect(dbFile, timeout=30)
        cur = conn.cursor()
        cur.execute('CREATE TABLE IF NOT EXISTS ct (d DATETIME, th_hour INTEGER, s INTEGER, mm TEXT, stn TEXT, h INTEGER, f INTEGER, m INTEGER, z INTEGER, t INTEGER, PRIMARY KEY (d, th_hour, s, mm, stn))')
        cur.executemany('INSERT OR REPLACE INTO ct (d, th_hour, s, mm, stn, h, f, m, z, t) VALUES (:d, :th_hour, :s, :mm, :stn, :h, :f, :m, :z, :t)', insertDatas)
        conn.commit()
        conn.close()

        pass


    def SumContingency(self, thresholdHour, stnIds, modelCode, ct, maxFcstHour) -> dict:
        
        '''
        Sum the values in the Contingency Table for given stnIds, ththresholdHour
        
        Parameters:
        - thresholdHour(int): Time to determine the prediction interval
        - stnIds(list): Station Id list
        - modelCode(str): model code
        - ct(dict): Contingency table
        - maxFcstHour(int): max forecasting hour

        Returns:
        - dict: Sum Contingency Table values for each Threshold precipitation(szMm) and publish time(pubTm)
        '''  
        ss = []
        for modelBaseT in self.modelIdxs[maxFcstHour][thresholdHour] :
            for pubTm in self.modelIdxs[maxFcstHour][thresholdHour][modelBaseT] :
                ss.append(pubTm)

        ctSum = {}
        for mm in cfg.thresholdMms:
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
    
    def SaveContingencyDaySum(self, targetDay, thresholdHour, modelCode, obsCode, ctSum, maxFcstHour) :
        '''
        Store precipitation forecast validation data of targeDay in a SQLite database
        
        Parameters:
        - targetDay(datetime): date (KST)
        - thresholdHour(int): Time to determine the prediction interval
        - modelCode(str): model code
        - obsCode(str): Observation code (aws, asos)
        - ctSum(dict): Sum Contingency Table values for each Threshold precipitation and publish time
        - maxFcstHour(int): max forecasting hour

        Returns:
        - None
        
        '''
        ss = []
        for modelBaseT in self.modelIdxs[maxFcstHour][thresholdHour] :
            for pubTm in self.modelIdxs[maxFcstHour][thresholdHour][modelBaseT] :
                ss.append(pubTm)

        insertDatas = []
        for mm in cfg.thresholdMms:
            szMm = format(mm, ".1f")
            for s in ss :
                #print(str(s), ctSum[szMm][str(s)])
                row = {
                    'd' : targetDay.strftime('%Y-%m-%d'),
                    'th_hour' : thresholdHour,
                    's' : s,
                    'mm' : szMm,
                    'model' : modelCode,
                    'h' : ctSum[szMm][str(s)]['h'],
                    'f' : ctSum[szMm][str(s)]['f'],
                    'm' : ctSum[szMm][str(s)]['m'],
                    'z' : ctSum[szMm][str(s)]['z'],
                    't' : ctSum[szMm][str(s)]['t']
                }
                insertDatas.append(row)
        if not os.path.isdir(cfg.PATH_DAOU + "/daily_shrt/" + targetDay.strftime('%Y')) :
            os.makedirs(cfg.PATH_DAOU + "/daily_shrt/" + targetDay.strftime('%Y'))
            
        dbFile = cfg.PATH_CT_DAILYSUM_DB_ADDTIONAL.format(OBS=obsCode, YYYY=targetDay.strftime('%Y'), YYYYMM=targetDay.strftime('%Y%m'), ADD_CODE='shrt')
        dbFileDir = os.path.dirname(dbFile)
        if not os.path.isdir(dbFileDir) :
            os.makedirs(dbFileDir)

        conn = sqlite3.connect(dbFile, timeout=30)
        cur = conn.cursor()
        cur.execute('CREATE TABLE IF NOT EXISTS ct (d DATETIME, th_hour INTEGER, s INTEGER, mm TEXT, model TEXT, h INTEGER, f INTEGER, m INTEGER, z INTEGER, t INTEGER, PRIMARY KEY (d, th_hour, s, mm, model))')
        cur.executemany('INSERT OR REPLACE INTO ct (d, th_hour, s, mm, model, h, f, m, z, t) VALUES (:d, :th_hour, :s, :mm, :model, :h, :f, :m, :z, :t)', insertDatas)
        conn.commit()
        conn.close()

        pass
    
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
    parser.add_argument('--model', required=True, help='gdps_ne36/gdps_n128/ecmf')
    parser.add_argument('--obs', required=True, help='asos/aws')
    parser.add_argument('--targetDate', required=True, help='yyyymmdd')

    args = parser.parse_args()

    dt = datetime.strptime(args.targetDate, '%Y%m%d')

    print("- Calc Contingency ShrtFcstVrfy Rule : ", args.model, args.obs, args.targetDate)

    calcCt = CalcContingencyDayShrtFcst()
    # # stn List
    # stnIds = []
    # f = open(PATH_STNXY_FILE_FORMAT.format(model=args.model, obs=args.obs), 'r')
    # while True :
    #     line = f.readline()
    #     if not line : break
    #     if line.startswith('#') : continue
    #     row = line.strip().split(',')
    #     stnIds.append(int(row[0]))
    # f.close()

    # modelIdxs = {
    # 3 : { # 임계시간
    #     -24 : [ # 발표시각
    #         [6,7,8,9,10,11,12,13,14,15,16,17,18,19,20] # 모델 예보시각
            
    stnIds = calcCt.GetStnIds(args.model, args.obs, dt)

    #for thresholdHour in cfg.modelConf[args.model]['modelThresholdHours']:
    for maxFcstHour in calcCt.maxFcstHours :
        for thresholdHour in calcCt.modelIdxs[maxFcstHour] :
            print(args.model, args.obs, args.targetDate, 'thresholdHour : ', thresholdHour)
            
            model = calcCt.GetDayModel(dt, thresholdHour, stnIds, args.model, args.obs, maxFcstHour)
            if model is None or model is False:
                continue
            
            obs = calcCt.GetDayObs(dt, thresholdHour, stnIds, args.obs, maxFcstHour)
            if obs is None or obs is False :
                continue
            
            ct = calcCt.CalcContingency(dt, thresholdHour, stnIds, args.model, obs, model, maxFcstHour) 

            #print(ct)
            ctSum = calcCt.SumContingency( thresholdHour, stnIds, args.model, ct, maxFcstHour) 
            #print(ctSum)

            calcCt.SaveContingencyDay(dt, thresholdHour, stnIds, args.model, args.obs, ct, maxFcstHour)
            #print(ctSum)
            calcCt.SaveContingencyDaySum(dt, thresholdHour, args.model, args.obs, ctSum, maxFcstHour)



