# nc 파일에서 위경도 격자파일을 생성

# module load python/3.8.12
# module load gcc/11.1 netcdf/4.9.0
# module load wgrib2/3.1.0

import netCDF4
import numpy as np
import os

dataInputDir = "./sample/models"
dataOutputDir = "../DABA"



# # gdps ne36
# print("gdps ne36")
# f2 = netCDF4.Dataset("/ARCV/NWP/RAWD/MODL/GDPS/NE36/202404/15/00/ERLY/FCST/post/sfc.ft000.nc", format="netcdf4")

# lats_tmp = np.asarray(f2.variables['lats'][:])
# lons_tmp = np.asarray(f2.variables['lons'][:])

# #lats2 = np.tile(lats_tmp, (len(lons_tmp), 1))
# #lons2 = np.swapaxes(np.tile(lons_tmp, (len(lats_tmp), 1)), 0, 1)
# lats2 = np.swapaxes(np.tile(lats_tmp, (len(lons_tmp), 1)), 0, 1)
# lons2 = np.tile(lons_tmp, (len(lats_tmp), 1))

# np.savez(f"{dataOutputDir}/grid_latlon_gdps_ne36.npz", lats=lats2, lons=lons2)

# latlons2 = np.load(f"{dataOutputDir}/grid_latlon_gdps_ne36.npz", allow_pickle = True)
# print(latlons2['lats'])
# print(latlons2['lons'])


# # gdps n128
# print("gdps n128")
# os.system(f"wgrib2 /ARCV/NWP/GRIB/MODL/GDPS/N128/202404/15/g128_v070_ergl_unis_h000.2024041500.gb2 -match \"APCP\" -netcdf ../DAIN/TMP/g128_v070_ergl_unis_h000.2024041500.prec.nc")
# f5 = netCDF4.Dataset(f"../DAIN/TMP/g128_v070_ergl_unis_h000.2024041500.prec.nc", format="netcdf4")

# lats_tmp = np.asarray(f5.variables['latitude'][:])
# lons_tmp = np.asarray(f5.variables['longitude'][:])

# lats5 = np.swapaxes(np.tile(lats_tmp, (len(lons_tmp), 1)), 0, 1)
# lons5 = np.tile(lons_tmp, (len(lats_tmp), 1))

# np.savez(f"{dataOutputDir}/grid_latlon_gdps_n128.npz", lats=lats5, lons=lons5)

# latlons5 = np.load(f"{dataOutputDir}/grid_latlon_gdps_n128.npz", allow_pickle = True)

# os.remove('../DAIN/TMP/g128_v070_ergl_unis_h000.2024041500.prec.nc')

# print(latlons5['lats'])
# print(latlons5['lons'])



# # rdps ne36
# print("rdps ne36")
# os.system(f"wgrib2 /ARCV/NWP/GRIB/MODL/RDPS/NE36/202404/15/r030_v040_ne36_unis_h000.2024041500.gb2 -match \"APCP\" -netcdf ../DAIN/TMP/r030_v040_ne36_unis_h000.2024041500.prec.nc")
# f5 = netCDF4.Dataset(f"../DAIN/TMP/r030_v040_ne36_unis_h000.2024041500.prec.nc", format="netcdf4")

# lats5 = np.asarray(f5.variables['latitude'][:])
# lons5 = np.asarray(f5.variables['longitude'][:])

# np.savez(f"{dataOutputDir}/grid_latlon_rdps_ne36.npz", lats=lats5, lons=lons5)

# latlons5 = np.load(f"{dataOutputDir}/grid_latlon_rdps_ne36.npz", allow_pickle = True)

# os.remove('../DAIN/TMP/r030_v040_ne36_unis_h000.2024041500.prec.nc')
# print(latlons5['lats'])
# print(latlons5['lons'])



# # ldps n128
# print("ldps n128")
# os.system(f"wgrib2 /ARCV/NWP/GRIB/MODL/LDPS/N128/202404/15/l015_v070_erlo_unis_h000.2024041500.gb2 -match \":(NCPCP|SNOL)\" -netcdf ../DAIN/TMP/l015_v070_erlo_unis_h000.2024041500.prec.nc")
# f5 = netCDF4.Dataset(f"../DAIN/TMP/l015_v070_erlo_unis_h000.2024041500.prec.nc", format="netcdf4")

# lats5 = np.asarray(f5.variables['latitude'][:])
# lons5 = np.asarray(f5.variables['longitude'][:])

# np.savez(f"{dataOutputDir}/grid_latlon_ldps_n128.npz", lats=lats5, lons=lons5)

# latlons5 = np.load(f"{dataOutputDir}/grid_latlon_ldps_n128.npz", allow_pickle = True)

# os.remove('../DAIN/TMP/l015_v070_erlo_unis_h000.2024041500.prec.nc')
# print(latlons5['lats'])
# print(latlons5['lons'])







# rdps ne36
#/ARCV/NWP/GRIB/MODL/RDPS/NE36/202404/15/r030_v040_ne36_unis_h000.2024041500.gb2
#f2 = netCDF4.Dataset(f"{dataInputDir}/rdps_pres_h000.2023092400.nc", format="netcdf4")

#lats2 = np.asarray(f2.variables['XLAT'][0][:])
#lons2 = np.asarray(f2.variables['XLONG'][0][:])

#np.savez(f"{dataOutputDir}/grid_latlon_rdps_ne36.npz", lats=lats2, lons=lons2)

#latlons2 = np.load(f"{dataOutputDir}/grid_latlon_rdps_ne36.npz", allow_pickle = True)
#print(latlons2['lats'])
#print(latlons2['lons'])


# # gdps n128
# f3 = netCDF4.Dataset(f"{dataInputDir}/umglaa_pb000.nc", format="netcdf4")

# lats3 = np.asarray(f3.variables['latitude'][:])
# lons3 = np.asarray(f3.variables['longitude'][:])

# #lats3 = np.tile(lats_tmp, (len(lons_tmp), 1))
# #lons3 = np.swapaxes(np.tile(lons_tmp, (len(lats_tmp), 1)), 0, 1)
# lats3 = np.swapaxes(np.tile(lats_tmp, (len(lons_tmp), 1)), 0, 1)
# lons3 = np.tile(lons_tmp, (len(lats_tmp), 1))

# np.savez(f"{dataOutputDir}/grid_latlon_gdps_n128.npz", lats=lats3, lons=lons3)

# latlons3 = np.load(f"{dataOutputDir}/grid_latlon_gdps_n128.npz", allow_pickle = True)
# print(latlons3['lats'])
# print(latlons3['lons'])


# # ecmf
# print("ecmf")
# import pygrib
# fn = '/ARCV/NWP/GRIB/MODL/ECMW/T127/202404/1500/e025_v025_nhem_h000.202404150000.gb1'
# grb = pygrib.open(fn)
# g = grb.select(name='Total precipitation')
# lat, lon = g[0].latlons()
# lats_tmp = np.asarray(lat)
# lons_tmp = np.asarray(lon)

# np.savez(f"{dataOutputDir}/grid_latlon_ecmf.npz", lats=lats_tmp, lons=lons_tmp)

# latlons4 = np.load(f"{dataOutputDir}/grid_latlon_ecmf.npz", allow_pickle = True)
# print(latlons4['lats'])
# print(latlons4['lons'])

# klfs_ne36
print("klfs ne36")
path = '/ARCV/NWP/RAWD/MODL/KLFS/NE36/202405/11/klfs_lc05_fcst.202405110000'
f1 = netCDF4.Dataset(path, format="netcdf4")

lats1 = np.asarray(f1.variables['XLAT'][0][:])
lons1 = np.asarray(f1.variables['XLONG'][0][:])

np.savez(f"{dataOutputDir}/grid_latlon_klfs_ne36.npz", lats=lats1, lons=lons1)

latlons = np.load(f"{dataOutputDir}/grid_latlon_klfs_ne36.npz", allow_pickle = True)
print(latlons['lats'])
print(latlons['lons'])


# klfs_n128
print("klfs n128")
path = '/ARCV/NWP/RAWD/MODL/KLFS/N128/202405/11/klfs_lc05_fcst.202405110000'
f1 = netCDF4.Dataset(path, format="netcdf4")

lats1 = np.asarray(f1.variables['XLAT'][0][:])
lons1 = np.asarray(f1.variables['XLONG'][0][:])

np.savez(f"{dataOutputDir}/grid_latlon_klfs_n128.npz", lats=lats1, lons=lons1)

latlons = np.load(f"{dataOutputDir}/grid_latlon_klfs_n128.npz", allow_pickle = True)
print(latlons['lats'])
print(latlons['lons'])