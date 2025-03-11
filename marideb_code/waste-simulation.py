import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import requests
from scipy.interpolate import griddata
import shapely.geometry

def fetch_tidal_current_data(api_url):
    """KHOA API에서 조류 데이터 가져오기"""
    response = requests.get(api_url)
    
    if response.status_code == 200:
        json_data = response.json()
        tidal_data = json_data["result"]["data"]
        
        df_tidal = pd.DataFrame(tidal_data)
        df_tidal.rename(columns={"pre_lat": "Latitude", "pre_lon": "Longitude"}, inplace=True)
        
        # 숫자형 데이터 변환
        df_tidal["Latitude"] = df_tidal["Latitude"].astype(float)
        df_tidal["Longitude"] = df_tidal["Longitude"].astype(float)
        df_tidal["current_speed"] = df_tidal["current_speed"].astype(float)
        df_tidal["current_dir"] = df_tidal["current_dir"].astype(float)
        
        return df_tidal
    else:
        print(f"API 요청 실패! 상태 코드: {response.status_code}")
        return None

def load_ship_density_data(file_path):
    """선박 밀집도 데이터 로드"""
    df_ship = pd.read_csv(file_path)
    df_ship["Latitude"] = df_ship["Latitude"].astype(float)
    df_ship["Longitude"] = df_ship["Longitude"].astype(float)
    df_ship["Density"] = df_ship["Density"].astype(float)
    return df_ship

def create_grid(df_ship, df_tidal, grid_size=50):
    """시뮬레이션을 위한 격자 생성"""
    lon_min, lon_max = 125, 132  # 한국 전체 해역
    lat_min, lat_max = 33, 38
    
    lon_grid = np.linspace(lon_min, lon_max, grid_size)
    lat_grid = np.linspace(lat_min, lat_max, grid_size)
    lon_mesh, lat_mesh = np.meshgrid(lon_grid, lat_grid)
    
    return lon_mesh, lat_mesh

def interpolate_data(df_ship, df_tidal, lon_mesh, lat_mesh):
    """데이터를 격자에 보간"""
    density = griddata(
        (df_ship['Longitude'], df_ship['Latitude']),
        df_ship['Density'],
        (lon_mesh, lat_mesh),
        method='cubic',
        fill_value=0
    )
    
    angles = np.radians(90 - df_tidal["current_dir"])
    U = df_tidal["current_speed"] * np.cos(angles)
    V = df_tidal["current_speed"] * np.sin(angles)
    
    U_interp = griddata(
        (df_tidal['Longitude'], df_tidal['Latitude']),
        U,
        (lon_mesh, lat_mesh),
        method='cubic',
        fill_value=0
    )
    
    V_interp = griddata(
        (df_tidal['Longitude'], df_tidal['Latitude']),
        V,
        (lon_mesh, lat_mesh),
        method='cubic',
        fill_value=0
    )
    
    return density, U_interp, V_interp

def create_ocean_mask(lon_mesh, lat_mesh):
    """육지를 제외한 해양 영역 마스크 생성"""
    ocean_mask = np.ones_like(lon_mesh)
    land = cfeature.NaturalEarthFeature('physical', 'land', '50m')
    
    # 격자 간격으로 건너뛰며 계산
    step = 2
    for i in range(0, lon_mesh.shape[0], step):
        for j in range(0, lon_mesh.shape[1], step):
            point = shapely.geometry.Point(lon_mesh[i,j], lat_mesh[i,j])
            for geom in land.geometries():
                if point.within(geom):
                    ocean_mask[i:i+step, j:j+step] = np.nan
                    break
    
    return ocean_mask

def simulate_waste_movement(density, U_interp, V_interp, ocean_mask, dt=1, max_time=4):
    """쓰레기 이동 시뮬레이션"""
    waste = density.copy() * ocean_mask
    waste_history = [waste.copy()]
    steps = max_time + 1  # 0시간부터 4시간까지

    for step in range(max_time):
        print(f"Simulating hour {step+1}/{max_time}")
        waste_new = waste.copy()
        
        # 이류 항 계산
        dx = 0.01
        dy = 0.01
        
        waste_new[1:-1, 1:-1] -= (
            (U_interp[1:-1, 1:-1] * 
             (waste[1:-1, 2:] - waste[1:-1, :-2]) / (2 * dx)) * dt
        )
        
        waste_new[1:-1, 1:-1] -= (
            (V_interp[1:-1, 1:-1] * 
             (waste[2:, 1:-1] - waste[:-2, 1:-1]) / (2 * dy)) * dt
        )
        
        # 확산 항 계산
        diffusion_coef = 0.01
        waste_new[1:-1, 1:-1] += diffusion_coef * (
            (waste[2:, 1:-1] + waste[:-2, 1:-1] + 
             waste[1:-1, 2:] + waste[1:-1, :-2] - 
             4 * waste[1:-1, 1:-1]) / (dx * dy)
        ) * dt
        
        waste_new = waste_new * ocean_mask
        waste_new[waste_new < 0] = 0
        
        waste = waste_new
        waste_history.append(waste.copy())
    
    return waste_history

def plot_results(lon_mesh, lat_mesh, density, U_interp, V_interp, waste_history, ocean_mask):
    """시뮬레이션 결과 시각화"""
    print(f"Available timesteps: {len(waste_history)}")
    
    sns.set_context("notebook", font_scale=1.2)
    fig = plt.figure(figsize=(20, 12))
    projection = ccrs.PlateCarree()
    
    def create_map_axes(position):
        ax = fig.add_subplot(position, projection=projection)
        ax.coastlines(resolution='50m', color='black', linewidth=1)
        ax.add_feature(cfeature.LAND, facecolor='lightgray', alpha=0.5)
        ax.add_feature(cfeature.OCEAN, facecolor='lightblue', alpha=0.3)
        gl = ax.gridlines(draw_labels=True, x_inline=False, y_inline=False)
        gl.top_labels = False
        gl.right_labels = False
        ax.set_extent([125, 132, 33, 38], crs=projection)
        return ax
    
    # 선박 밀집도
    ax1 = create_map_axes(231)
    masked_density = density * ocean_mask
    im1 = ax1.pcolormesh(lon_mesh, lat_mesh, masked_density, 
                         shading='auto', cmap='YlOrRd',
                         transform=projection)
    ax1.set_title('Initial Ship Density')
    plt.colorbar(im1, ax=ax1, orientation='horizontal', pad=0.05)
    
    # 해류 벡터장
    ax2 = create_map_axes(232)
    skip = 5
    U_masked = U_interp * ocean_mask
    V_masked = V_interp * ocean_mask
    ax2.quiver(lon_mesh[::skip, ::skip], lat_mesh[::skip, ::skip],
               U_masked[::skip, ::skip], V_masked[::skip, ::skip],
               transform=projection)
    ax2.set_title('Tidal Current Vectors')
    
    # 시간별 쓰레기 분포
    times = [0, 1, 2, 4]  # 초기, 1시간 후, 2시간 후, 4시간 후
    positions = [233, 234, 235, 236]
    
    for t, pos in zip(times, positions):
        ax = create_map_axes(pos)
        im = ax.pcolormesh(lon_mesh, lat_mesh, waste_history[t],
                          shading='auto', cmap='YlOrRd',
                          transform=projection)
        ax.set_title(f'Waste Distribution at t={t}h')
        plt.colorbar(im, ax=ax, orientation='horizontal', pad=0.05)
    
    plt.tight_layout()
    plt.show()

def main():
    # API URL 및 데이터 경로 설정
    api_url = "http://www.khoa.go.kr/api/oceangrid/tidalCurrentArea/search.do"
    api_url += "?ServiceKey=c/JboSuOOn1VCop00VUC1w=="
    api_url += "&Date=20250220&Hour=01&Minute=00"
    api_url += "&MaxX=132&MinX=125&MaxY=38&MinY=33&ResultType=json"
    
    ship_density_file = "cleaned_sden_202502200100_grid3.csv"
    
    # 데이터 로드
    df_tidal = fetch_tidal_current_data(api_url)
    df_ship = load_ship_density_data(ship_density_file)
    
    if df_tidal is None:
        return
    
    # 격자 생성 및 데이터 보간
    lon_mesh, lat_mesh = create_grid(df_ship, df_tidal)
    density, U_interp, V_interp = interpolate_data(df_ship, df_tidal, lon_mesh, lat_mesh)
    
    # 해양 마스크 생성
    ocean_mask = create_ocean_mask(lon_mesh, lat_mesh)
    
    # 쓰레기 이동 시뮬레이션
    waste_history = simulate_waste_movement(density, U_interp, V_interp, ocean_mask)
    
    # 결과 시각화
    plot_results(lon_mesh, lat_mesh, density, U_interp, V_interp, waste_history, ocean_mask)

if __name__ == "__main__":
    main()