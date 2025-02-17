#!/bin/bash 
#SBATCH --job-name=CREATE_COUNTERFACTUAL_sst
#SBATCH --time=02:00:00
#SBATCH -N 1
#SBATCH --ntasks-per-node=128   
#SBATCH --ntasks-per-core=1
#SBATCH --partition=zen3_0512
#SBATCH --qos=zen3_0512
#SBATCH -A p72281



# Ensure both input and output directories are provided
if [ "$#" -lt 3 ]; then
    echo "Usage: $0 <file_pattern> <input_dir> <output_dir>"
    exit 1
fi

# Define the input parameters
FILE_PATTERN=$1
INPUT_DIR=$2
OUTPUT_DIR=$3

# Ensure the output directory exists
echo "Creating output directory if it doesn't exist: ${OUTPUT_DIR}"
mkdir -p ${OUTPUT_DIR}

# Run the Python script to process files
echo "Processing files with pattern ${FILE_PATTERN} in directory ${INPUT_DIR}"
python reduce_sst.py --input_dir=${INPUT_DIR} --output_dir=${OUTPUT_DIR} --file_pattern="${FILE_PATTERN}"

echo "Processing complete!"
