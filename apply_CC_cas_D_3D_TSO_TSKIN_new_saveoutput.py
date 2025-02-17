import xarray as xr
import sys
import numpy as np
from scipy import interpolate
import argparse
from pathlib import Path

# Set up argument parsing
parser = argparse.ArgumentParser(description="Process CAS files with given parameters.")
parser.add_argument("cas_filename", help="Filename of the CAS-file")
parser.add_argument("gcm_name", help="Name of the GCM (e.g., MIROC6, EC-Earth3)")
parser.add_argument("input_dir_cas", help="Input directory")
parser.add_argument("output_dir_cas", help="Output directory")
parser.add_argument("input_dir_CC_mrso", help="Input directory containing the climate change signals")

# Parse arguments
args = parser.parse_args()

print(f"Opening CAS file: {args.cas_filename}")
print(f"Climate change signals will be read from: {args.input_dir_CC_mrso}/CC_{args.gcm_name}_ensmean_new_remapcon.nc_minus_1K")

# [Your existing Python script code continues here...]

# Now you can use args.cas_filename, args.gcm_name, args.input_dir, and args.output_dir in your script

cc_signal_file_path = f"{args.input_dir_CC_mrso}/CC_{args.gcm_name}_ensmean_new_remapcon.nc_minus_1K"

# open cas-file, to be modified
file_cas_original=xr.open_dataset(args.cas_filename)

# remove time dimension
file_cas = file_cas_original.isel(time=0)

# surface geopotential
Zsurf = file_cas['FIS']

# skin temperature
TS = file_cas['T_SKIN']

# air temperature
T = file_cas['T']

# specific humidity
QV = file_cas['QV']  

# cloud liquid water content [kg kg-1}
QC = file_cas['QC']  

# surface pressure
SP = file_cas['PS']

# coefficients defining sigma pressure coordinates
A = file_cas['akm']
B = file_cas['bkm']


# soil temperature
TSO = file_cas['T_SO']


print('Forcing data loaded!')

# open file containing CC profiles and select by month and day
file_CC = xr.open_dataset(cc_signal_file_path)


# Revert plev dimension to ascending order, same as in file_cas (necessary for interpolation) 
file_CC=file_CC.sel(plev=slice(None, None, -1))
    
# remove dimensiosion (time, lat, lon)
file_CC = file_CC.isel(time=0)

# on the 1000hPa level some GCMs produce just NaN values, so if this is the case, this level is dropped
#file_CC = file_CC.dropna(dim='plev')
# file_CC = file_CC.interpolate_na(dim='plev', method='linear', fill_value='extrapolate')

# get pressure levels [Pa]
plev_CC = file_CC['plev']

# get air temperature [K]
# find a way to save all values higher than 1000 to NAN
ta_CC = file_CC['ta'].where(file_CC['ta'] < 1000) #NOTE: why is this (< 1000) necessary?

# get relative humidity [%]
hur_CC = file_CC['hur'].where(file_CC['hur'] < 1000)

# get specific humidity [-]
#hus_CC = file_CC['hus'].where(file_CC['hus'] < 1000)

# get sea level pressure
psl_CC = file_CC['psl']


# get skin temperature
ts_CC = file_CC['ts']
    


print('Climate change signals loaded!')
      
      
#===========================================================================
#                            constants for calculations
#===========================================================================


Rd      = 287.06  # specific gas constant for dry air, taken from ECMWF geopotential calculator

# constants from OpenIFS
g       = 9.80665            # m s-2
eps     = 1.0 / ( 1.0 + 0.609133 )  # = Rd/Rw = Mw / Md
Mw      = 18.0153 * 0.001 # Kg/mol molecular weight of water
Md      = 28.9644 * 0.001 # Kg/mol molecular weight of dry air
Rstar   = 1.380658 * 6.0221367       #J/molK

# calculate 3D pressure (http://cfconventions.org/cf-conventions/cf-conventions.html#_atmosphere_hybrid_sigma_pressure_coordinate)
P = (A + B * SP) #.isel(lat=0.isel(lon=0)
P = P.assign_attrs(units='Pa').assign_attrs(Name='3D Pressure')

# for the calculation of saturation pressure es [Pa] from Murray (1967)
aw      = 17.2693882 #water
bw      = 35.86 #water
ai      = 21.8745584 #ice
bi      = 7.66 #ice



#===========================================================================
#                            define current state
#===========================================================================


# calculate exponential factor (ratio between sea level pressure and surface pressure), following the IFS documentation 
# (YESSAD. K, 2011, "FULL-POS IN THE CYCLE 38 OF ARPEGE/IFS.")
# this is needed because there is a climate change signal of mean sea level pressure
# and this needs to be transferred into a climate change signal of the surface pressue

# surface temperature (highest model level equals surface)
Tsurf = T.isel(level=-1) + 0.0065 * Rd * ( SP / P.isel(level=-1) - 1.00 ) * T.isel(level=-1) / g

# surface temperature at sea level
T0 = Tsurf + 0.0065 * Zsurf / g



# define temperature lapse rate gamma and modify it according to temperatures
gamma = SP * 0 + 0.0065 # array with 0.0065 everywhere, SP is just needed to get the right dimensions

# modfiy gamma according to temperatures
condition = ((T0 > 290.5) & (Tsurf <= 290.5))
gamma = gamma.where(~condition, ( 290.5 - Tsurf ) * g / Zsurf) # xr.where(condition, x, y) returns a new array with the same dimensions as the input arrays, wiht the original values where the condition is true, and modified values where the condition is false. '~' inverts the condition, so the values are modified where the original condition is true

condition = ((T0 > 290.5) & (Tsurf > 290.5))
gamma = gamma.where(~condition, 0.0)
Tsurf = Tsurf.where(~condition, 0.5 * (290.5 + Tsurf))

condition = (Tsurf < 255.0)    
Tsurf = Tsurf.where(~condition, 0.5 * (255.0 + Tsurf))



# exponential factor to modify surface pressure
x = gamma * Zsurf / g / Tsurf
expfac = np.exp(Zsurf / Rd / Tsurf * (1.0 - 0.5 * x + 1.0 / 3.0 * x ** 2))

      
print('Current climate state defined!')
      
      
#===========================================================================
#                            add climate change signals
#===========================================================================

psl_CC_new = psl_CC.fillna(0)

# first, add CC in pressure


dim_SP = SP.shape 
SP_new = np.zeros(dim_SP)

SP_new = SP + psl_CC_new / expfac

P_new = (A + B * SP_new)
# P_new = P_new.transpose('time','level','lat','lon')
# P = P.transpose('time','level','lat','lon')
P_new = P_new.transpose('level','lat','lon') 
P = P.transpose('level','lat','lon')
#SP_new = SP_new.transpose('time','lat','lon')


# interpolate current state (T and QV) onto the new pressure levels
dim = T.shape # get dimensions of T
T_new = T * 0 # create new array with same dimensions as T
QV_new = QV * 0 # create new array with same dimensions as Q

for ii in range(dim[2]):
    for jj in range(dim[1]):
        # define interpolation functions, fill_value='extrapolate' is needed to extrapolate if  the input values are outside teh defined range
        f_T = interpolate.interp1d(np.log(P[:,jj,ii]), T[:,jj,ii], fill_value='extrapolate')
        f_QV = interpolate.interp1d(np.log(P[:,jj,ii]), QV[:,jj,ii], fill_value='extrapolate')
        T_new[:,jj,ii] = f_T(np.log(P_new[:,jj,ii]))
        QV_new[:,jj,ii] = f_QV(np.log(P_new[:,jj,ii]))
        

# Make sure QV is not negative
QV_new = QV_new.where(QV_new >= 0, 0)

es = 610.78 * np.exp(aw * (T_new - 273.16) / (T_new - bw))

condition = (T_new >= 233.15)

# Calculation for over ice
es = es.where(condition, 610.78 * np.exp(ai * (T_new - 273.16) / (T_new - bi)))


# calculate RH of current state on new pressure levels
# current RH [not in %]
RH = P_new *  QV / ( Mw/Md + ( 1.0 - Mw/Md ) * QV ) / es
RH = RH.where(RH >= 0, 0)



# interpolate CC signals onto new pressure levels
dim = T.shape
hur_CC_f = T*0 # create empty array with same dimensions as T
ta_CC_f = T*0

# Log of original pressure levels, if not already
#log_plev_CC = np.log(plev_CC)

for lat in range(hur_CC.shape[1]):
    for lon in range(hur_CC.shape[2]):
        # Extract the slice for current lat and lon across all levels
        hur_slice = hur_CC[:, lat, lon]
        ta_slice = ta_CC[:, lat, lon]

        # Define interpolation functions for current lat, lon slice
        f_hur = interpolate.interp1d(np.log(plev_CC), hur_slice, fill_value='extrapolate')
        f_ta = interpolate.interp1d(np.log(plev_CC), ta_slice, fill_value='extrapolate')

        # Interpolate onto new pressure levels for this lat, lon
        # Ensure P_new[:, lat, lon] is in log-scale if your P_new wasn't initially
        hur_CC_f[:, lat, lon] = f_hur(np.log(P_new[:, lat, lon]))
        ta_CC_f[:, lat, lon] = f_ta(np.log(P_new[:, lat, lon]))

        
# add CC signal to RH
RH = RH + (hur_CC_f/100.0)
RH = RH.where(RH >= 0, 0)

# add CC signal to temperature
T_new = T_new + ta_CC_f


# calculate QV from changed T, P, and RH

QV_new = (Mw/Md) * RH * es / ( P_new - ( 1.0 - Mw/Md ) * RH * es )
QV_new = QV_new.where(QV_new >= 0.0, 0)



dim_ts = TS.shape 
TS_new = TS*0

TS_new = TS + ts_CC.fillna(0)
    
dim_soil = TSO.shape
TSO_new = TSO*0
    
TSO_new = TSO + ts_CC.fillna(0)
#===========================================================================
#                            apply soil moisture CC signal
#===========================================================================


# load file, containing climate change mrso factors
mrso_file_path = f"{args.input_dir_CC_mrso}/mrso_CC_{args.gcm_name}_September_ensmean_remapcon.nc_minus_1K"
file_mrso=xr.open_dataset(mrso_file_path)
# file_mrso=xr.open_dataset('mrso_CC_GFDL-ESM2M_October.nc_plus_3K')

mrso_CC = file_mrso.isel(time=0, bnds=0) # [0,0,0] removes the coordinates time, lat, lon

# extract volume fraction of condensed water in soil pores
W_SO_REL = file_cas.W_SO_REL # ratio of volume fraction of soil moisture to pore volume [1]


mrso_CC_da = mrso_CC['mrso'].fillna(0)

# Perform the operation
W_SO_REL_new = W_SO_REL * mrso_CC_da

print('Climate change signals added!')

#===========================================================================
#                            save output
#===========================================================================


file_cas_new = xr.open_dataset(args.cas_filename)

file_cas_new['T'] = file_cas_new['T'] * 0 + T_new.values
file_cas_new['QV'] = file_cas_new['QV'] * 0 + QV_new.values
file_cas_new['PS'] = file_cas_new['PS'] * 0 + SP_new.values
file_cas_new['W_SO_REL'] = file_cas_new['W_SO_REL'] * 0 + W_SO_REL_new.values
file_cas_new['T_SKIN'] = file_cas_new['T_SKIN'] * 0 + TS_new.values
file_cas_new['T_SO'] = file_cas_new['T_SO'] * 0 + TSO_new.values


#file_cas_new['T_SKIN'] = file_cas_new['T_SKIN'].transpose('time', 'lat', 'lon')
#file_cas_new['T_SO'] = file_cas_new['T_SO'].transpose('time', 'soil1', 'lat', 'lon')
#file_cas_new['W_SO_REL'] = file_cas_new['W_SO_REL'].transpose('time', 'soil1', 'lat', 'lon')
#file_cas_new['PS'] = file_cas_new['PS'].transpose('time', 'lat', 'lon')


filename_output = args.cas_filename
output_file_path = Path(args.output_dir_cas) / filename_output

file_cas_new.to_netcdf(output_file_path)


print('cas-file adjusted!')
