import xarray as xr
from pathlib import Path
import argparse
import glob

def process_file(cas_file_path, output_dir):
    # Open the CAS dataset
    file_cas = xr.open_dataset(cas_file_path)

    # Modify T_SKIN where FR_LAND <= 0.05
    ts = file_cas['T_SKIN'] - 1.3
    fr_land = file_cas['FR_LAND']
    file_cas['T_SKIN'] = xr.where(fr_land <= 0.05, ts, file_cas['T_SKIN'], keep_attrs=True)

    # Prepare output file path and save the modified file
    output_file_path = Path(output_dir) / Path(cas_file_path).name
    file_cas.to_netcdf(output_file_path)
    print(f"Processed and saved: {output_file_path}")

def main():
    parser = argparse.ArgumentParser(description='Process CAS files and adjust T_SKIN values.')
    parser.add_argument('--input_dir', required=True, help='Directory containing CAS files to process.')
    parser.add_argument('--output_dir', required=True, help='Directory to save the modified CAS files.')
    parser.add_argument('--file_pattern', default='cas*.nc', help='Pattern to match CAS files (e.g., "cas*.nc").')
    args = parser.parse_args()

    # Find all CAS files matching the pattern in the input directory
    cas_files = glob.glob(f"{args.input_dir}/{args.file_pattern}")

    # Process each file
    for cas_file in cas_files:
        process_file(cas_file, args.output_dir)

if __name__ == "__main__":
    main()

