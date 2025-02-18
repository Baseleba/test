#!/bin/bash

# Get a list of all S3 buckets
BUCKETS=$(aws s3api list-buckets --query "Buckets[].Name" --output text)

# Check if any buckets exist
if [[ -z "$BUCKETS" ]]; then
    echo "No S3 buckets found in this AWS account."
    exit 1
fi

echo -e "\nFetching tags for all S3 buckets...\n"

# Loop through each bucket and get its tags
for BUCKET in $BUCKETS; do
    echo "Bucket: $BUCKET"
    
    # Fetch tags for the bucket
    TAGS=$(aws s3api get-bucket-tagging --bucket "$BUCKET" --output json 2>/dev/null)

    # Check if the bucket has tags
    if [[ $? -eq 0 && -n "$TAGS" ]]; then
        echo "$TAGS" | jq -r '.TagSet[] | "- \(.Key): \(.Value)"'
    else
        echo "  No tags found."
    fi

    echo "----------------------------"
done