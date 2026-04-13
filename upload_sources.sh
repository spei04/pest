#!/usr/bin/env bash
# Uploads all files in sources/ to the Render server.
# Usage: UPLOAD_TOKEN=your-secret ./upload_sources.sh

set -e

TOKEN="${UPLOAD_TOKEN:?Error: UPLOAD_TOKEN env var is not set}"
BASE_URL="https://pest-7ij8.onrender.com"
SOURCES="/Users/serenapei/Downloads/pest/sources"

if [ ! -d "$SOURCES" ]; then
  echo "Error: sources directory not found at $SOURCES"
  exit 1
fi

total=0
failed=0

while IFS= read -r -d '' filepath; do
  subpath="${filepath#$SOURCES/}"
  echo "Uploading: $subpath"

  http_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/upload" \
    -H "Authorization: Bearer $TOKEN" \
    -F "subpath=$subpath" \
    -F "file=@$filepath")

  if [ "$http_code" = "200" ]; then
    total=$((total + 1))
  else
    echo "  FAILED (HTTP $http_code): $subpath"
    failed=$((failed + 1))
  fi
done < <(find "$SOURCES" -type f -print0)

echo ""
echo "Done. $total uploaded, $failed failed."
