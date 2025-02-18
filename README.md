#!/bin/bash

# Prompt user for tag key to filter
read -p "Enter the tag key to filter: " TAG_KEY

# Get a list of all S3 buckets
BUCKETS=$(aws s3api list-buckets --query "Buckets[].Name" --output text)

# Initialize a flag to check if any bucket matches
FOUND=false

echo -e "\nChecking S3 buckets for tag key: $TAG_KEY...\n"

# Loop through each bucket and check its tags
for BUCKET in $BUCKETS; do
    TAGS=$(aws s3api get-bucket-tagging --bucket "$BUCKET" --output json 2>/dev/null)

    if [[ $? -eq 0 && -n "$TAGS" ]]; then
        MATCH=$(echo "$TAGS" | jq -r ".TagSet[] | select(.Key == \"$TAG_KEY\")")

        if [[ -n "$MATCH" ]]; then
            echo "Bucket: $BUCKET"
            echo "$TAGS" | jq -r '.TagSet[] | "- \(.Key): \(.Value)"'
            echo "----------------------------"
            FOUND=true
        fi
    fi
done

# If no matching buckets are found
if [ "$FOUND" = false ]; then
    echo "No S3 buckets found with the specified tag key."
fi