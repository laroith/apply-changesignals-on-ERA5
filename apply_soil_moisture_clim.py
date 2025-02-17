import xarray as xr
import sys
import numpy as np
from scipy import interpolate
import argparse
from pathlib import Path
import pandas as pd

# Set up argument parsing
parser = argparse.ArgumentParser(description="Process CAS files with given parameters.")
parser.add_argument("cas_filename", help="Filename of the CAS-file")
#parser.add_argument("gcm_name", help="Name of the GCM (e.g., MIROC6, EC-Earth3)")
parser.add_argument("input_dir_cas", help="Input directory")
parser.add_argument("output_dir_cas", help="Output directory")
#parser.add_argument("input_dir_CC_mrso", help="Input directory containing the climate change signals")

# Parse arguments
args = parser.parse_args()

print(f"Opening CAS file: {args.cas_filename}")
#print(f"Climate change signals will be read from: {args.input_dir_CC_mrso}/CC_{args.gcm_name}_3D_remapcon_TS_TSKIN.nc_minus_1K")

# Now you can use args.cas_filename, args.gcm_name, args.input_dir, and args.output_dir in your script

mrso_climatology_file_path = "/gpfs/data/fs72281/lar/change_temp/CC_signals_Laurenz/climatology_remapcon.nc"

# open cas-file, to be modified
file_cas=xr.open_dataset(args.cas_filename)


# open file containing CC profiles and select by month and day
mrso_CC = xr.open_dataset(mrso_climatology_file_path)

# Define the soil1 coordinate
soil1_depths = [0.035, 0.175, 0.64, 1.945]

# Stack the data variables into a single DataArray with a new 'soil1' coordinate
mrso_stacked = xr.concat(
    [mrso_CC['swvl1'], mrso_CC['swvl2'], mrso_CC['swvl3'], mrso_CC['swvl4']],
    dim=pd.Index(soil1_depths, name='soil1')
)

# extract volume fraction of condensed water in soil pores
W_SO_REL = file_cas.W_SO_REL # ratio of volume fraction of soil moisture to pore volume [1]


# Convert 'soil1' coordinate in mrso_regridded to float32
mrso_stacked = mrso_stacked.assign_coords(soil1=mrso_stacked['soil1'].astype('float32'))

# Convert volume fraction to W_SO_REL=VW_SO/0.472
mrso_stacked_rel = mrso_stacked / 0.472


#===========================================================================
#                            save output
#===========================================================================


file_cas_new = xr.open_dataset(args.cas_filename)
condition = np.isfinite(mrso_stacked_rel) & (mrso_stacked_rel > 0)
 

file_cas_new['W_SO_REL'] = xr.where(condition, mrso_stacked_rel, W_SO_REL, keep_attrs=True)

file_cas_new['W_SO_REL'] = file_cas_new['W_SO_REL'].transpose('time', 'soil1', 'lat', 'lon')

filename_output = args.cas_filename
output_file_path = Path(args.output_dir_cas) / filename_output

file_cas_new.to_netcdf(output_file_path)


print('cas-file adjusted!')
