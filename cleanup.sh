#!/bin/bash

# Create target directories if they don't exist
mkdir -p results log raw raw/hosts raw/urls

# Function to organize files in a given directory
organize_files() {
  local dir=$1
  for file in "$dir"/*; do
    if [[ -f $file ]]; then
      # Skip files that do not contain an underscore
      if [[ $file != *_* ]]; then
        continue
      fi

      if [[ $file == *labeled.txt ]]; then
        mv "$file" results/
      elif [[ $file == *.log ]]; then
        mv "$file" log/
      elif [[ $file == *.txt ]]; then
        mv "$file" raw/
      fi
    fi
  done
}

# Perform cleanup in the main directory
organize_files .

# Perform cleanup in raw/hosts and raw/urls directories
organize_files raw/hosts
organize_files raw/urls

echo "Files have been organized."