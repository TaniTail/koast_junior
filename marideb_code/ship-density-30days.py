import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def process_ship_density_data(timestep_data, nearest_grid_data, ship_density_data):
    """
    각 조사 차수와 날짜에 대해 이전 30일간의 선박밀집도 데이터 처리
    
    Parameters:
    - timestep_data: 조사 차수 및 날짜 데이터 (DataFrame)
    - nearest_grid_data: 각 정점별 가장 가까운 그리드 정보 (DataFrame)
    - ship_density_data: 선박밀집도 데이터 (Dictionary 형태, key: 날짜, value: 해당 날짜의 DataFrame)
    
    Returns:
    - 각 정점별 30일 선박밀집도 정보 (DataFrame)
    """
    result = []
    
    # 정점명과 가장 가까운 그리드 매핑 생성
    grid_mapping = dict(zip(nearest_grid_data['정점명'], nearest_grid_data['가장_가까운_그리드']))
    
    # 각 차수별, 정점별로 처리
    for _, row in timestep_data.iterrows():
        station_name = row['정점명']
        round_num = row['차수']
        survey_date = datetime.strptime(row['날짜'], '%Y-%m-%d')  # 날짜 형식은 실제 데이터에 맞게 조정 필요
        
        # 해당 정점의 가장 가까운 그리드 찾기
        if station_name not in grid_mapping:
            print(f"경고: '{station_name}' 정점의 가장 가까운 그리드 정보가 없습니다.")
            continue
            
        nearest_grid = grid_mapping[station_name]
        
        # 이전 30일 날짜 리스트 생성
        date_list = [(survey_date - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(1, 31)]
        
        # 30일간의 선박밀집도 데이터 수집
        density_values = []
        
        for date in date_list:
            if date in ship_density_data:
                # 해당 날짜의 선박밀집도 데이터에서 해당 그리드의 값 찾기
                # 실제 데이터의 컬럼명에 맞게 수정
                grid_id_col = 'grid_id' if 'grid_id' in ship_density_data[date].columns else 'grid_name'
                density_col = 'density' if 'density' in ship_density_data[date].columns else 'ship_density'
                
                grid_density = ship_density_data[date].loc[
                    ship_density_data[date][grid_id_col] == nearest_grid, 
                    density_col
                ].values
                
                if len(grid_density) > 0:
                    density_values.append(grid_density[0])
                else:
                    print(f"경고: {date} 날짜에 {nearest_grid} 그리드의 선박밀집도 데이터가 없습니다.")
                    density_values.append(np.nan)
            else:
                print(f"경고: {date} 날짜의 선박밀집도 데이터가 없습니다.")
                density_values.append(np.nan)
        
        # 30일 평균 선박밀집도 계산
        avg_density = np.nanmean(density_values) if len(density_values) > 0 else np.nan
        max_density = np.nanmax(density_values) if len(density_values) > 0 else np.nan
        
        result.append({
            '정점명': station_name,
            '차수': round_num,
            '조사날짜': survey_date.strftime('%Y-%m-%d'),
            '30일_평균_선박밀집도': avg_density,
            '30일_최대_선박밀집도': max_density,
            '데이터_포함일수': sum(~np.isnan(density_values)),
            '가장_가까운_그리드': nearest_grid
        })
    
    return pd.DataFrame(result)

def load_ship_density_data(base_path, date_list):
    """
    여러 날짜의 선박밀집도 데이터를 로드하는 함수
    
    Parameters:
    - base_path: 선박밀집도 데이터 파일이 있는 기본 경로
    - date_list: 로드할 날짜 리스트 (YYYY-MM-DD 형식)
    
    Returns:
    - 날짜별 선박밀집도 데이터 (Dictionary)
    """
    ship_density_data = {}
    
    for date in date_list:
        try:
            # 날짜 형식 변환 (YYYY-MM-DD -> YYYYMMDD)
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            date_formatted = date_obj.strftime('%Y%m%d')
            
            # 파일명 형식: sden_YYYYMMDDHHMM_grid3.csv
            # 일단 해당 날짜의 0100(01시) 데이터를 사용
            file_path = f"{base_path}/sden_{date_formatted}0100_grid3.csv"
            
            data = pd.read_csv(file_path)
            ship_density_data[date] = data
        except Exception as e:
            print(f"경고: {date} 날짜의 선박밀집도 데이터 로드 실패: {str(e)}")
    
    return ship_density_data

# 메인 실행 코드
def main():
    # 조사 차수 및 날짜 데이터 로드
    timestep_data = pd.read_csv('marideb_timestep.csv')
    
    # 정점별 가장 가까운 그리드 정보 로드 (find_nearest_grid 함수로 생성한 파일)
    nearest_grid_data = pd.read_csv('station_nearest_grid.csv')
    
    # 조사 날짜의 고유 목록 생성
    unique_survey_dates = timestep_data['날짜'].unique()
    
    # 모든 조사에 필요한 이전 30일 날짜 목록 생성
    all_required_dates = set()
    for date_str in unique_survey_dates:
        survey_date = datetime.strptime(date_str, '%Y-%m-%d')  # 날짜 형식은 실제 데이터에 맞게 조정 필요
        for i in range(1, 31):
            prev_date = (survey_date - timedelta(days=i)).strftime('%Y-%m-%d')
            all_required_dates.add(prev_date)
    
    # 선박밀집도 데이터 로드 (기본 경로는 실제 데이터 위치에 맞게 조정 필요)
    ship_density_data = load_ship_density_data('D:/marideb/code/sden_2023_lv3', list(all_required_dates))
    
    # 30일 선박밀집도 데이터 처리
    result = process_ship_density_data(timestep_data, nearest_grid_data, ship_density_data)
    
    # 결과 저장
    result.to_csv('station_30days_ship_density.csv', index=False, encoding='utf-8-sig')
    print(f"총 {len(result)}개 정점-차수의 30일 선박밀집도 정보를 저장했습니다.")
    
    return result

if __name__ == "__main__":
    main()
