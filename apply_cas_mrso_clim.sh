#!/bin/bash 
#SBATCH --job-name=CREATE_COUNTERFACTUAL_FORCING_MIROC6
#SBATCH --time=72:00:00
#SBATCH -N 1
#SBATCH --ntasks-per-node=128   
#SBATCH --ntasks-per-core=1
#SBATCH --partition=zen3_0512
#SBATCH --qos=zen3_0512
#SBATCH -A p72281

#conda activate pyenv


# Print the current working directory
echo "Current working directory: $(pwd)"

# set the number of processors
  NPX=8
  NPY=16
  NCORES=$(( ${NPX} * ${NPY} ))

#GCM_NAME=$2
INPUT_DIR_CAS=$2
OUTPUT_DIR_CAS=$3


# Ensure the output directory exists
echo "Ensuring output directory ${OUTPUT_DIR_CAS} exists..."
mkdir -p ${OUTPUT_DIR_CAS}

# Find all files that match the given pattern in the first argument, only in the current directory
echo "Looking for files in ${INPUT_DIR_CAS} matching pattern $1, without descending into subdirectories"
FILES=$(find $INPUT_DIR_CAS -maxdepth 1 -name "$1")
echo "Found files:"
echo "${FILES}"

# Loop through each file and process it with the Python script
for FILE in $FILES
do
    OUTPUT_FILE="${OUTPUT_DIR_CAS}/$(basename $FILE)"
    
    # Check if the output file already exists
    if [ -f "$OUTPUT_FILE" ]; then
        echo "Output file $OUTPUT_FILE already exists. Skipping..."
        continue # Skip the rest of the loop and move to the next file
    fi
    
    echo "Processing file: $FILE"
    python /gpfs/data/fs72281/lar/change_temp/CC_signals_Laurenz/apply_soil_moisture_clim.py "$FILE" $INPUT_DIR_CAS $OUTPUT_DIR_CAS 
done

# Change directory to the output directory where the processed files are
cd ${OUTPUT_DIR_CAS}

# Print the directory you're working in now
echo "Now working in directory: $(pwd)"

# Loop through each .nc file in the output directory
for ff in $(ls cas*.nc); do 
  file=$(basename ${ff})
  echo "Appending variables from original file to: ${file}"

  # Determine the original file path
  original_file="/gpfs/data/fs72281/lar/change_temp/CC_signals_Laurenz/${file:0:3}2023${file:7}"

  # Append variables from the original file
  ncks -A -v akm,bkm,time_bnds,soil1_bnds "${original_file}" "${file}"
done

