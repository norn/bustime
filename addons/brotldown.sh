#!/bin/bash

echo "Pre-compression of static files using brotli max level for nginx."

DIRECTORY="$1/bustime/static/"
cd "$DIRECTORY" || exit

# Iterate through files of the form *.js, *.css, and *.json
find . -type f \( -name '*.js' -o -name '*.css' -o -name '*.json' -o -name '*.patch' \) | while read -r file; do
    # Define the name of the output file
    output="${file}.br"

    # Check if the compressed file already exists
    if [ ! -f "$output" ]; then
        # Compress the file using Brotli at quality level 11
        brotli -q 11 -o "$output" "$file"
        ls -la "$output" "$file"
    fi
done

echo ""
echo "Compression of all files is completed."
