#!/bin/bash

# Prompt user for tag key
read -p "Enter the tag key to filter: " TAG_KEY

# Get a list of all S3 buckets
BUCKETS=$(aws s3api list-buckets --query "Buckets[].Name" --output text)

# Initialize an empty array for matching buckets
MATCHING_BUCKETS=()

echo "Checking S3 buckets for tag key: $TAG_KEY..."

# Loop through each bucket and check its tags
for BUCKET in $BUCKETS; do
    TAGS=$(aws s3api get-bucket-tagging --bucket "$BUCKET" --output json 2>/dev/null)

    if [[ $? -eq 0 && -n "$TAGS" ]]; then
        MATCH=$(echo "$TAGS" | jq -r ".TagSet[] | select(.Key == \"$TAG_KEY\")")

        if [[ -n "$MATCH" ]]; then
            MATCHING_BUCKETS+=("$BUCKET")
        fi
    fi
done

# Display results
if [ ${#MATCHING_BUCKETS[@]} -gt 0 ]; then
    echo -e "\nBuckets with the tag key '$TAG_KEY':"
    for MATCH in "${MATCHING_BUCKETS[@]}"; do
        echo "- $MATCH"
    done
else
    echo -e "\nNo S3 buckets found with the specified tag key."
fi