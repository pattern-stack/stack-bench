#!/usr/bin/env bash
set -euo pipefail

# Upload an image to a GitHub PR/issue comment using browser session cookies.
# Uses playwright-cli for session auth + GitHub's internal upload API.
#
# Usage: ./scripts/gh-attach-image.sh <pr-number> <image-path> [body-text]
# Example: ./scripts/gh-attach-image.sh 74 screenshots/01-full-view.png "Here's the screenshot"
#
# Prerequisites:
#   - playwright-cli (npm install -g @playwright/cli)
#   - gh CLI (authenticated)
#   - Session saved via: npx playwright open --save-storage=~/.config/gh-attach/session.json https://github.com/login

PR_NUMBER="${1:?Usage: gh-attach-image.sh <pr-number> <image-path> [body-text]}"
IMAGE_PATH="${2:?Usage: gh-attach-image.sh <pr-number> <image-path> [body-text]}"
BODY_TEXT="${3:-}"

SESSION_FILE="${XDG_CONFIG_HOME:-$HOME/.config}/gh-attach/session.json"
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)

if [[ ! -f "$SESSION_FILE" ]]; then
  echo "No session file found at $SESSION_FILE" >&2
  echo "Run: npx playwright open --save-storage=$SESSION_FILE https://github.com/login" >&2
  exit 1
fi

if [[ ! -f "$IMAGE_PATH" ]]; then
  echo "Image not found: $IMAGE_PATH" >&2
  exit 1
fi

IMAGE_NAME=$(basename "$IMAGE_PATH")
IMAGE_SIZE=$(stat -f%z "$IMAGE_PATH" 2>/dev/null || stat -c%s "$IMAGE_PATH" 2>/dev/null)
CONTENT_TYPE="image/png"
if [[ "$IMAGE_NAME" == *.jpg ]] || [[ "$IMAGE_NAME" == *.jpeg ]]; then
  CONTENT_TYPE="image/jpeg"
fi

cleanup() {
  playwright-cli close >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "Uploading $IMAGE_NAME ($IMAGE_SIZE bytes) to PR #$PR_NUMBER..." >&2

# Step 1: Open headless browser, load session, navigate to PR
playwright-cli kill-all >/dev/null 2>&1 || true
playwright-cli open "https://github.com/$REPO/pull/$PR_NUMBER" >/dev/null 2>&1
playwright-cli state-load "$SESSION_FILE" >/dev/null 2>&1
playwright-cli goto "https://github.com/$REPO/pull/$PR_NUMBER" >/dev/null 2>&1
sleep 2

# Step 2: Extract upload context from the page
# playwright-cli eval wraps output in quotes and adds extra lines — extract JSON
RAW_CONTEXT=$(playwright-cli eval "JSON.stringify({repoId: document.querySelector('file-attachment').getAttribute('data-upload-repository-id'), csrf: document.querySelector('file-attachment input[data-csrf]').value})" 2>&1)
UPLOAD_CONTEXT=$(echo "$RAW_CONTEXT" | grep '^"' | head -1 | sed 's/^"//;s/"$//' | sed 's/\\"/"/g')

REPO_ID=$(echo "$UPLOAD_CONTEXT" | python3 -c "import sys,json; print(json.loads(sys.stdin.read())['repoId'])")
CSRF_TOKEN=$(echo "$UPLOAD_CONTEXT" | python3 -c "import sys,json; print(json.loads(sys.stdin.read())['csrf'])")

# Step 3: Extract cookies from session file for curl
COOKIES=$(python3 << 'PYEOF'
import json, os
path = os.path.expanduser(os.environ.get("XDG_CONFIG_HOME", "~/.config") + "/gh-attach/session.json")
with open(path) as f:
    data = json.load(f)
cookies = "; ".join(f"{c['name']}={c['value']}" for c in data.get("cookies", []) if "github.com" in c.get("domain", ""))
print(cookies)
PYEOF
)

# Step 4: Get upload policy (presigned S3 URL)
POLICY_RESPONSE=$(curl -s "https://github.com/upload/policies/assets" \
  -H "Cookie: $COOKIES" \
  -H "GitHub-Verified-Fetch: true" \
  -H "X-Requested-With: XMLHttpRequest" \
  -F "name=$IMAGE_NAME" \
  -F "size=$IMAGE_SIZE" \
  -F "content_type=$CONTENT_TYPE" \
  -F "repository_id=$REPO_ID" \
  -F "authenticity_token=$CSRF_TOKEN")

# Parse the policy response
UPLOAD_URL=$(echo "$POLICY_RESPONSE" | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(d['upload_url'])")
ASSET_URL=$(echo "$POLICY_RESPONSE" | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(d['asset']['href'])")

# Build S3 upload form fields from policy
FORM_FIELDS=$(echo "$POLICY_RESPONSE" | python3 << 'PYEOF'
import sys, json
d = json.loads(sys.stdin.read())
for k, v in d.get("form", {}).items():
    print(f"{k}\t{v}")
PYEOF
)

# Step 5: Upload file to S3
CURL_ARGS=()
while IFS=$'\t' read -r key val; do
  [[ -n "$key" ]] && CURL_ARGS+=(-F "$key=$val")
done <<< "$FORM_FIELDS"
CURL_ARGS+=(-F "file=@$IMAGE_PATH")

HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$UPLOAD_URL" "${CURL_ARGS[@]}")
if [[ "$HTTP_STATUS" != "204" && "$HTTP_STATUS" != "200" ]]; then
  echo "S3 upload failed with HTTP $HTTP_STATUS" >&2
  exit 1
fi

echo "Image uploaded: $ASSET_URL" >&2

# Step 6: Post comment with the image
if [[ -z "$BODY_TEXT" ]]; then
  COMMENT_BODY="![${IMAGE_NAME}](${ASSET_URL})"
else
  COMMENT_BODY=$(echo "$BODY_TEXT" | sed "s|<!-- gh-attach:IMAGE -->|![${IMAGE_NAME}](${ASSET_URL})|g")
  # If no placeholder found, append image
  if [[ "$COMMENT_BODY" == "$BODY_TEXT" ]] && [[ "$BODY_TEXT" != *"gh-attach"* ]]; then
    COMMENT_BODY="${BODY_TEXT}

![${IMAGE_NAME}](${ASSET_URL})"
  fi
fi

COMMENT_URL=$(gh pr comment "$PR_NUMBER" --body "$COMMENT_BODY")
echo "Done! $COMMENT_URL" >&2
