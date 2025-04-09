#!/bin/bash
# filepath: /Users/jacky/workspaces/deledao/cwcm/chinese_classifier_paralell/cleanup.sh

# Create target directories if they don't exist
mkdir -p results log raw

# Move files with specific extensions to their respective folders
for file in *; do
  if [[ $file == *labeled.txt ]]; then
    mv "$file" results/
  elif [[ $file == *.log ]]; then
    mv "$file" log/
  elif [[ $file == *.txt ]]; then
    mv "$file" raw/
  fi
done

echo "Files have been organized."