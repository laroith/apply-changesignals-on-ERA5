#!/bin/bash 
#SBATCH --job-name=CREATE_COUNTERFACTUAL_ts_sst_test
#SBATCH --time=00:10:00
#SBATCH -N 4
#SBATCH --ntasks-per-node=128   
#SBATCH --ntasks-per-core=1
#SBATCH --partition=zen3_0512
#SBATCH --qos=zen3_0512_devel
#SBATCH -A p72281

echo "Current working directory: $(pwd)"

# Ensure the output directory exists
echo "Ensuring output directory ${4} exists..."
mkdir -p ${4}

# Define variables
GCM_NAME=$2
INPUT_DIR_CAS=$3
OUTPUT_DIR_CAS=$4
SST_FILE_PATH=$5

# Find all files matching the pattern given as the first argument
echo "Looking for CAS files in ${INPUT_DIR_CAS} with pattern $1"
FILES=$(find ${INPUT_DIR_CAS} -maxdepth 1 -name "$1")
echo "Found files:"
echo "${FILES}"

# Loop through each found file and process it
for FILE in ${FILES}
do
    OUTPUT_FILE="${OUTPUT_DIR_CAS}/$(basename ${FILE})"
    
    if [ -f "${OUTPUT_FILE}" ]; then
        echo "Output file ${OUTPUT_FILE} already exists. Skipping..."
        continue
    fi
    
    echo "Processing file: ${FILE}"
    python apply_ts_sst.py --model_name=${GCM_NAME} --cas_input_dir=${INPUT_DIR_CAS} --sst_file_path=${SST_FILE_PATH} --output_dir=${OUTPUT_DIR_CAS}
done

