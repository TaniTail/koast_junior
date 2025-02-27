#MODEL_CODES = ['gdps_ne36', 'gdps_n128', 'rdps_ne36', 'ldps', 'ecmf']
PATH_DAIN = "../DAIN"
PATH_DABA = "../DABA"
PATH_DABA = "../DABA"
PATH_OBS = "../DAIN/OBS"
PATH_DAOU = "../DAOU"

PATH_OBS_STN =  PATH_DAIN + "/OBS_STN/{YYYY}/stn_{YYYYMMDD}_{OBS}.csv" #############################추가한 거// 
PATH_MODEL_STN = PATH_DAIN + "/MODEL_STN/stn_{YYYYMMDD}_{MODEL}_{OBS}.csv"

PATH_TMP = PATH_DAIN + '/TMP'
PATH_OBS_LATEST = PATH_OBS + '/latest_{OBS}.txt'
PATH_OBS_DB = PATH_OBS + "/{YYYY}/{OBS}_{YYYYMM}.db"
PATH_OBS_TXT = PATH_OBS + "/{YYYY}/rain_obsv_{OBS}.{YYYYMMDD}" 

PATH_STN_LIST = PATH_DABA + "/stn_{MODEL}_{OBS}.dat" # 지점번호만 사용

PATH_AWS_INFO_DB = PATH_DAIN + "/STN/aws_info.db"



PATH_MODEL_EXTRACT_TXT = PATH_DAIN + "/MODEL/{MODEL}/{YYYY}/extract_{MODEL}_{OBS}.{YYYYMMDDHH}"

PATH_MODEL_STNXY = PATH_DAIN + "/STNXY/{MODEL}/stnxy_{MODEL}_{OBS}.csv" ################################수정한거임
# PATH_MODEL_STNXY_CHANGEONLY_TXT = PATH_DAIN + "/STN/CHANGE_ONLY/{MODEL}/stnxy_{MODEL}_{OBS}_{YYYYMMDD}.csv"


PATH_CT_DAILY_CSV = PATH_DAOU + "/daily/{YYYY}/ct_day_{MODEL}_{OBS}_{YYYYMMDD}.csv"
PATH_CT_DAILYSUM_CSV = PATH_DAOU + "/daily/{YYYY}/ct_daysum_{OBS}_{YYYYMMDD}.csv"
# PATH_CT_DAILY_DB = PATH_DAOU + "/daily/{YYYY}/ct_day_{MODEL}_{OBS}_{YYYYMM}.db"
# PATH_CT_DAILYSUM_DB = PATH_DAOU + "/daily/{YYYY}/ct_daysum_{OBS}_{YYYYMM}.db"

PATH_PRETTY_FORMAT_DIR = PATH_DAOU + "/pretty/{YYYYMM}/{MODEL}"

PATH_CT_DAILY_DB_ADDTIONAL = PATH_DAOU + "/daily_{ADD_CODE}/{YYYY}/ct_day_{MODEL}_{OBS}_{YYYYMM}.db"
PATH_CT_DAILYSUM_DB_ADDTIONAL = PATH_DAOU + "/daily_{ADD_CODE}/{YYYY}/ct_daysum_{OBS}_{YYYYMM}.db"

PATH_PRETTY_FORMAT_DIR_ADDTIONAL = PATH_DAOU + "/pretty_{ADD_CODE}/{YYYYMM}/{MODEL}"


thresholdMms = [ 0.1, 1.0, 5.0, 12.5, 15.0, 25.0, 50.0 ]

modelConf = {
    
    'gdps_ne36' : {
        'modelThresholdHours' : [ 3, 6, 12 ],
        'modelFcstMaxHours' : [ 72, 120 ],
        'modelExtractHours' : 135,
        't' : [0, 12],
        'fcstInterval' : 3
    },
    'klfs_ne36' : {
        'modelThresholdHours' : [ 1, 3 ],
        'modelFcstMaxHours' : [ 12 ],
        'modelExtractHours' : 12,
        't' : [0, 3, 6, 9, 12, 15, 18, 21],
        'fcstInterval' : 1
    },
}


#modelCodes = ['gdps_ne36', 'gdps_n128', 'rdps_ne36', 'ldps_n128', 'ecmf', 'klfs_ne36', 'klfs_n128']
#obsCodes = ['asos', 'aws']