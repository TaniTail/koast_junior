import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import os
import glob
from tqdm import tqdm
import math

# 1. 해안쓰레기 데이터 로드
def load_waste_data(file_path='해양쓰레기_위치통합데이터.csv', encoding='utf-8'):
    """해안쓰레기 데이터 로드"""
    try:
        waste_df = pd.read_csv(file_path, encoding=encoding)
        print(f"해안쓰레기 데이터 로드 완료: {len(waste_df)}개 정점")
        return waste_df
    except UnicodeDecodeError:
        # 인코딩이 맞지 않을 경우 다른 인코딩 시도
        print(f"인코딩 '{encoding}'으로 읽기 실패. 'cp949'로 시도합니다.")
        waste_df = pd.read_csv(file_path, encoding='cp949')
        print(f"해안쓰레기 데이터 로드 완료: {len(waste_df)}개 정점")
        return waste_df
    except Exception as e:
        print(f"파일 '{file_path}' 로드 중 오류 발생: {str(e)}")
        raise

# 2. 선박밀집도 데이터 파일 목록 확인
def get_ship_density_files(directory='.', pattern='sden_*_grid3.csv'):
    """선박밀집도 파일 목록 가져오기"""
    file_list = glob.glob(os.path.join(directory, pattern))
    file_list.sort()  # 시간순 정렬
    print(f"선박밀집도 파일 {len(file_list)}개 발견 (디렉토리: {directory})")
    return file_list

# 3. 위경도 문자열을 숫자로 변환하는 함수
def parse_latlon(latlon_str):
    """위경도 문자열 (예: '35.475, 129.425')을 숫자 튜플로 변환"""
    try:
        lat, lon = map(float, latlon_str.replace(' ', '').split(','))
        return lat, lon
    except:
        return None, None

# 4. 두 지점 간의 거리 계산 (하버사인 공식)
def haversine_distance(lat1, lon1, lat2, lon2):
    """하버사인 공식을 사용하여 두 좌표 간 거리(km) 계산"""
    # 지구 반경 (km)
    R = 6371.0
    
    # 라디안으로 변환
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # 위도, 경도 차이
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # 하버사인 공식
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    # 거리 (km)
    distance = R * c
    
    return distance

# 5. 특정 정점에 가장 가까운 그리드 찾기
def find_closest_grid(grid_df, point_lat, point_lon, max_distance=10):
    """주어진 위경도에 가장 가까운 그리드 찾기 (최대 거리 제한)"""
    min_distance = float('inf')
    closest_grid = None
    
    for idx, row in grid_df.iterrows():
        grid_lat, grid_lon = parse_latlon(row['위경도'])
        if grid_lat is None or grid_lon is None:
            continue
            
        distance = haversine_distance(point_lat, point_lon, grid_lat, grid_lon)
        
        if distance < min_distance and distance <= max_distance:
            min_distance = distance
            closest_grid = row.copy()
            closest_grid['distance_km'] = distance
    
    return closest_grid

# 6. 파일명에서 날짜시간 추출
def extract_datetime_from_filename(filename):
    """파일명(sden_202502200100_grid3.csv)에서 날짜시간 추출"""
    # 파일명에서 날짜 부분 추출
    try:
        basename = os.path.basename(filename)
        date_part = basename.split('_')[1]
        
        # 날짜시간 파싱 (YYYYMMDDHHMM 형식)
        year = int(date_part[:4])
        month = int(date_part[4:6])
        day = int(date_part[6:8])
        hour = int(date_part[8:10])
        minute = int(date_part[10:12])
        
        return datetime(year, month, day, hour, minute)
    except:
        print(f"파일명 파싱 실패: {filename}")
        return None

# 7. 주어진 정점에 대한 모든 시간의 선박밀집도 데이터 수집
def collect_density_for_station(station_lat, station_lon, station_name, ship_files, max_files=None):
    """단일 정점에 대한 모든 선박밀집도 데이터 수집"""
    result_data = []
    
    # 파일 수 제한 (테스트용)
    if max_files:
        ship_files = ship_files[:max_files]
    
    for file_path in tqdm(ship_files, desc=f"정점 {station_name} 처리 중"):
        try:
            # 파일에서 날짜시간 추출
            file_datetime = extract_datetime_from_filename(file_path)
            if file_datetime is None:
                continue
                
            # 선박밀집도 데이터 로드 (다양한 인코딩 시도)
            try:
                ship_df = pd.read_csv(file_path, encoding='utf-8')
            except UnicodeDecodeError:
                try:
                    ship_df = pd.read_csv(file_path, encoding='cp949')
                except:
                    print(f"파일 {file_path}를 읽을 수 없습니다. 건너뜁니다.")
                    continue
            
            # 가장 가까운 그리드 찾기
            closest_grid = find_closest_grid(ship_df, station_lat, station_lon)
            
            if closest_grid is not None:
                # 기본 정보
                result_row = {
                    '정점명': station_name,
                    '날짜시간': file_datetime,
                    '위도': station_lat,
                    '경도': station_lon,
                    '격자번호': closest_grid['격자번호'],
                    '격자_위경도': closest_grid['위경도'],
                    '거리_km': closest_grid['distance_km'],
                    '교통량': closest_grid['교통량(척)'],
                    '밀집도': closest_grid['밀집도(%)']
                }
                
                # 선박 유형별 데이터
                ship_types = ['어선', '여객선', '화물선', '유조선', '예인선', '수상레저기구', '기타선']
                for ship_type in ship_types:
                    result_row[ship_type] = closest_grid[ship_type]
                
                # 톤수별 데이터
                tonnage_types = ['1t미만', '1t ~ 2t', '2t ~ 3t', '3t ~ 5t', '5t ~ 10t', 
                                '10t ~ 50t', '50t ~ 100t', '100t ~ 500t', '500t이상', '미상']
                for tonnage in tonnage_types:
                    result_row[tonnage] = closest_grid[tonnage]
                
                result_data.append(result_row)
        except Exception as e:
            print(f"파일 {file_path} 처리 중 오류: {str(e)}")
    
    # 결과 데이터프레임 변환
    result_df = pd.DataFrame(result_data)
    
    # 날짜시간 기준 정렬
    if not result_df.empty:
        result_df = result_df.sort_values('날짜시간')
    
    return result_df

# 8. 모든 정점에 대한 선박밀집도 데이터 수집
def analyze_all_stations(waste_df, ship_files, output_dir='정점별_선박밀집도'):
    """모든 정점에 대한 선박밀집도 데이터 수집 및 저장"""
    # 출력 디렉토리 생성
    os.makedirs(output_dir, exist_ok=True)
    
    # 모든 정점 요약 정보
    summary_data = []
    
    # 각 정점별로 처리
    for idx, station in waste_df.iterrows():
        station_name = station['정점명']
        station_lat = station['위도']
        station_lon = station['경도']
        
        print(f"\n[{idx+1}/{len(waste_df)}] 정점 '{station_name}' 처리 중...")
        
        # 해당 정점의 선박밀집도 데이터 수집
        station_density = collect_density_for_station(
            station_lat, station_lon, station_name, ship_files
        )
        
        # 결과 저장
        if not station_density.empty:
            output_file = os.path.join(output_dir, f"{station_name}_선박밀집도.csv")
            station_density.to_csv(output_file, index=False, encoding='utf-8')
            print(f"  - {len(station_density)}개 데이터 수집, '{output_file}'에 저장됨")
            
            # 요약 정보 저장
            summary_row = {
                '정점명': station_name,
                '위도': station_lat,
                '경도': station_lon,
                '데이터수': len(station_density),
                '평균_교통량': station_density['교통량'].mean(),
                '최대_교통량': station_density['교통량'].max(),
                '평균_밀집도': station_density['밀집도'].mean(),
                '최대_밀집도': station_density['밀집도'].max()
            }
            
            # 선박 유형별 평균
            ship_types = ['어선', '여객선', '화물선', '유조선', '예인선', '수상레저기구', '기타선']
            for ship_type in ship_types:
                summary_row[f'평균_{ship_type}'] = station_density[ship_type].mean()
            
            summary_data.append(summary_row)
        else:
            print(f"  - 데이터 수집 실패")
    
    # 요약 정보 저장
    summary_df = pd.DataFrame(summary_data)
    summary_file = os.path.join(output_dir, "정점별_선박밀집도_요약.csv")
    summary_df.to_csv(summary_file, index=False, encoding='utf-8')
    print(f"\n요약 정보가 '{summary_file}'에 저장되었습니다.")
    
    return summary_df

# 9. 정점별 선박밀집도 시계열 시각화
def visualize_station_density(station_file, output_dir='시각화'):
    """단일 정점의 선박밀집도 시계열 시각화"""
    # 출력 디렉토리 생성
    os.makedirs(output_dir, exist_ok=True)
    
    # 데이터 로드
    df = pd.read_csv(station_file, encoding='utf-8')
    df['날짜시간'] = pd.to_datetime(df['날짜시간'])
    station_name = df['정점명'].iloc[0]
    
    # 시간대별 집계 데이터 생성
    df['연월일'] = df['날짜시간'].dt.date
    df['시간'] = df['날짜시간'].dt.hour
    daily_avg = df.groupby('연월일').agg({
        '교통량': 'mean',
        '밀집도': 'mean',
        '어선': 'mean',
        '여객선': 'mean',
        '화물선': 'mean',
        '유조선': 'mean'
    }).reset_index()
    
    hourly_avg = df.groupby('시간').agg({
        '교통량': 'mean',
        '밀집도': 'mean',
        '어선': 'mean',
        '여객선': 'mean',
        '화물선': 'mean',
        '유조선': 'mean'
    }).reset_index()
    
    # 1. 일별 교통량 및 밀집도 추이
    plt.figure(figsize=(14, 7))
    plt.subplot(2, 1, 1)
    plt.plot(daily_avg['연월일'], daily_avg['교통량'], marker='o', linestyle='-', label='교통량(척)')
    plt.title(f'정점 {station_name} - 일별 평균 교통량 추이')
    plt.xticks(rotation=45)
    plt.ylabel('선박 수 (척)')
    plt.grid(True)
    
    plt.subplot(2, 1, 2)
    plt.plot(daily_avg['연월일'], daily_avg['밀집도'], marker='o', linestyle='-', color='orange', label='밀집도(%)')
    plt.title(f'정점 {station_name} - 일별 평균 밀집도 추이')
    plt.xticks(rotation=45)
    plt.ylabel('밀집도 (%)')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f'{station_name}_일별추이.png'))
    plt.close()
    
    # 2. 시간대별 교통량 및 밀집도 패턴
    plt.figure(figsize=(14, 7))
    plt.subplot(2, 1, 1)
    plt.plot(hourly_avg['시간'], hourly_avg['교통량'], marker='o', linestyle='-', label='교통량(척)')
    plt.title(f'정점 {station_name} - 시간대별 평균 교통량')
    plt.xlabel('시간 (시)')
    plt.ylabel('선박 수 (척)')
    plt.grid(True)
    plt.xticks(range(0, 24))
    
    plt.subplot(2, 1, 2)
    plt.plot(hourly_avg['시간'], hourly_avg['밀집도'], marker='o', linestyle='-', color='orange', label='밀집도(%)')
    plt.title(f'정점 {station_name} - 시간대별 평균 밀집도')
    plt.xlabel('시간 (시)')
    plt.ylabel('밀집도 (%)')
    plt.grid(True)
    plt.xticks(range(0, 24))
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f'{station_name}_시간대별패턴.png'))
    plt.close()
    
    # 3. 선박 유형별 비율
    plt.figure(figsize=(10, 6))
    ship_types = ['어선', '여객선', '화물선', '유조선', '예인선', '수상레저기구', '기타선']
    type_means = [df[ship_type].mean() for ship_type in ship_types]
    plt.pie(type_means, labels=ship_types, autopct='%1.1f%%', startangle=90)
    plt.axis('equal')
    plt.title(f'정점 {station_name} - 선박 유형별 평균 비율')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f'{station_name}_선박유형비율.png'))
    plt.close()
    
    print(f"정점 {station_name}의 시각화가 완료되었습니다.")

# 10. 모든 정점 시각화
def visualize_all_stations(data_dir='정점별_선박밀집도', output_dir='시각화'):
    """모든 정점의 선박밀집도 데이터 시각화"""
    # 정점별 파일 목록
    station_files = glob.glob(os.path.join(data_dir, '*_선박밀집도.csv'))
    
    for station_file in station_files:
        print(f"파일 '{station_file}' 시각화 중...")
        visualize_station_density(station_file, output_dir)
    
    # 정점별 요약 데이터 시각화
    summary_file = os.path.join(data_dir, "정점별_선박밀집도_요약.csv")
    if os.path.exists(summary_file):
        summary_df = pd.read_csv(summary_file, encoding='utf-8')
        
        # 정점별 평균 교통량 비교
        plt.figure(figsize=(14, 8))
        summary_sorted = summary_df.sort_values('평균_교통량', ascending=False)
        sns.barplot(x='정점명', y='평균_교통량', data=summary_sorted.head(20))
        plt.title('정점별 평균 교통량 (상위 20개)')
        plt.xticks(rotation=90)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, '정점별_평균교통량_비교.png'))
        plt.close()
        
        # 정점별 평균 밀집도 비교
        plt.figure(figsize=(14, 8))
        summary_sorted = summary_df.sort_values('평균_밀집도', ascending=False)
        sns.barplot(x='정점명', y='평균_밀집도', data=summary_sorted.head(20))
        plt.title('정점별 평균 밀집도 (상위 20개)')
        plt.xticks(rotation=90)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, '정점별_평균밀집도_비교.png'))
        plt.close()

# 메인 실행 함수
def main(waste_data_path='해양쓰레기_위치통합데이터.csv', 
         ship_density_dir='.', 
         ship_pattern='sden_*_grid3.csv',
         output_dir='정점별_선박밀집도',
         viz_dir='시각화'):
    """
    주요 분석 실행 함수
    
    Parameters:
    -----------
    waste_data_path : str
        해안쓰레기 데이터 CSV 파일 경로
    ship_density_dir : str
        선박밀집도 데이터 파일이 있는 디렉토리 경로
    ship_pattern : str
        선박밀집도 파일 이름 패턴
    output_dir : str
        결과 데이터 저장 디렉토리
    viz_dir : str
        시각화 결과 저장 디렉토리
    """
    print("해안쓰레기 정점별 선박밀집도 추이 분석 시작...")
    print(f"- 해안쓰레기 데이터: {waste_data_path}")
    print(f"- 선박밀집도 데이터 디렉토리: {ship_density_dir}")
    print(f"- 선박밀집도 파일 패턴: {ship_pattern}")
    print(f"- 결과 저장 디렉토리: {output_dir}")
    print(f"- 시각화 저장 디렉토리: {viz_dir}")
    
    # 1. 해안쓰레기 데이터 로드
    waste_df = load_waste_data(waste_data_path)
    
    # 2. 선박밀집도 데이터 파일 목록 확인
    ship_files = get_ship_density_files(ship_density_dir, ship_pattern)
    
    # 3. 모든 정점에 대한 선박밀집도 데이터 수집 및 저장
    summary_df = analyze_all_stations(waste_df, ship_files, output_dir)
    
    # 4. 모든 정점의 선박밀집도 시각화
    visualize_all_stations(output_dir, viz_dir)
    
    print("분석 완료!")

if __name__ == "__main__":
    import argparse
    
    # 명령줄 인자 파싱
    parser = argparse.ArgumentParser(description="해안쓰레기 정점별 선박밀집도 추이 분석")
    parser.add_argument('--waste-data', type=str, default='해양쓰레기_위치통합데이터.csv',
                        help='해안쓰레기 데이터 CSV 파일 경로')
    parser.add_argument('--ship-dir', type=str, default='.',
                        help='선박밀집도 데이터 파일이 있는 디렉토리 경로')
    parser.add_argument('--ship-pattern', type=str, default='sden_*_grid3.csv',
                        help='선박밀집도 파일 이름 패턴')
    parser.add_argument('--output-dir', type=str, default='정점별_선박밀집도',
                        help='결과 데이터 저장 디렉토리')
    parser.add_argument('--viz-dir', type=str, default='시각화',
                        help='시각화 결과 저장 디렉토리')
    
    args = parser.parse_args()
    
    # 메인 함수 실행
    main(
        waste_data_path=args.waste_data,
        ship_density_dir=args.ship_dir,
        ship_pattern=args.ship_pattern,
        output_dir=args.output_dir,
        viz_dir=args.viz_dir
    )
