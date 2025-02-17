import xarray as xr
import numpy as np
from scipy.spatial import cKDTree
import argparse
from pathlib import Path
import glob

"""
This script processes CAS files to update T_SKIN values based on conditions
related to sea surface temperatures (SST), land fraction, and climate change signals.

Arguments:
- --model_name: Name of the climate model for the CC signal file.
- --cas_input_dir: Directory containing the CAS files to process.
- --sst_file_path: Full path to the SST file.
- --output_dir: Directory where the modified CAS files will be saved.

The script modifies T_SKIN values based on ocean, land, and mixed conditions,
interpolating SST values where necessary.

Example use:
python apply_CC_cas.py --model_name=MODEL_NAME --cas_input_dir=/path/to/cas_files --sst_file_path=/path/to/sst_file.nc --output_dir=/path/to/output_dir
"""


def process_file(cas_file_path, sst_file_path, cc_signal_file_path, output_dir):
    print(cc_signal_file_path)
    file_cas_original = xr.open_dataset(cas_file_path)
    file_cas = file_cas_original.isel(time=0)
    ts = file_cas['T_SKIN']
    fr_land = file_cas['FR_LAND']
    tso = file_cas['T_SO']

    file_cc = xr.open_dataset(cc_signal_file_path, engine='netcdf4')
    file_cc = file_cc.isel(time=0)
    file_cc_new = file_cc['ts']
    
    dim = ts.shape 
    ts_new = np.zeros(dim)

    ts_new = ts + file_cc_new.fillna(0)
    
    dim_soil = tso.shape
    tso_new = np.zeros(dim_soil)
    
    tso_new = tso + file_cc_new.fillna(0)
    
    
    print("Climate change signal loaded!")

    sst_clim = xr.open_dataset(sst_file_path)
    sst = sst_clim['sst'].fillna(0) + 273.15
    sst = sst.isel(time=0)
    
    print("SST loaded!")

    

    ocean_condition_no_sst = np.isfinite(fr_land) & (fr_land <= 0.05) & (sst == 273.15)
    valid_sst_mask = (fr_land <= 0.05) & (sst > 273.15)

    valid_positions = np.array(np.where(valid_sst_mask)).T
    invalid_positions = np.array(np.where(ocean_condition_no_sst)).T

    if not len(invalid_positions):
        interpolated_sst = np.copy(sst.values)
    else:
        tree = cKDTree(valid_positions)
        distances, indices = tree.query(invalid_positions)
        interpolated_sst = np.copy(sst.values)
        for idx, pos in enumerate(invalid_positions):
            valid_pos = valid_positions[indices[idx]]
            interpolated_sst[tuple(pos)] = sst.values[tuple(valid_pos)]

    interpolated_sst_da = xr.DataArray(np.expand_dims(interpolated_sst, axis=-1), 
                                       dims=['lat', 'lon', 'time'],
                                       coords={'lat': file_cas['T_SKIN'].coords['lat'], 
                                               'lon': file_cas['T_SKIN'].coords['lon'],
                                               'time': [file_cas_original['time'].values[0]]})

    ts_mixed = (interpolated_sst_da.isel(time=0) * (1 - fr_land) + ts_new * fr_land)
    
    ocean_condition = np.isfinite(sst) & (fr_land <= 0.05)
    land_condition = np.isfinite(ts_new) & (fr_land >= 0.95)
    mixed_condition = np.isfinite(ts_new) & np.isfinite(interpolated_sst_da.isel(time=0)) & (fr_land > 0.05) & (fr_land < 0.95) & (sst > 273.15)
    soil_condition = np.isfinite(tso_new) & (tso_new >= 100)
    
    file_cas_new=xr.open_dataset(cas_file_path)
    
    # Apply updates conditionally using xarray's where method
    file_cas_new['T_SKIN'] = xr.where(ocean_condition, interpolated_sst_da.isel(time=0), file_cas_new['T_SKIN'], keep_attrs=True)
    file_cas_new['T_SKIN'] = xr.where(land_condition, ts_new, file_cas_new['T_SKIN'], keep_attrs=True)
    file_cas_new['T_SKIN'] = xr.where(mixed_condition, ts_mixed, file_cas_new['T_SKIN'], keep_attrs = True)
    file_cas_new['T_SKIN'] = xr.where(ocean_condition_no_sst, interpolated_sst_da.isel(time=0), file_cas_new['T_SKIN'], keep_attrs=True)
    file_cas_new['T_SO'] = xr.where(soil_condition, tso_new, file_cas_new['T_SO'], keep_attrs=True)
    
    output_file_path = Path(output_dir) / cas_file_path.name
    file_cas_new.to_netcdf(output_file_path)

def main():
    parser = argparse.ArgumentParser(description='Process SST and CC signal files.')
    parser.add_argument('--model_name', required=True, help='Model name for the CC signal file.')
    parser.add_argument('--cas_input_dir', required=True, help='Input directory for CAS files.')
    parser.add_argument('--sst_file_path', required=True, help='Full path to the SST file.')
    parser.add_argument('--output_dir', required=True, help='Output directory for modified CAS files.')
    args = parser.parse_args()

    cc_signal_file_path = Path(args.cas_input_dir) / f'ts_{args.model_name}_remapcon.nc_minus_1K'
    cas_files = glob.glob(f'{args.cas_input_dir}/cas*[0-9].nc')

    for cas_file in cas_files:
        process_file(Path(cas_file), Path(args.sst_file_path), cc_signal_file_path, Path(args.output_dir))

if __name__ == "__main__":
    main()
