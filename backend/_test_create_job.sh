#!/usr/bin/env bash
set -e
API=https://vajans-backend-production.up.railway.app
TOKEN=$(curl -s -X POST "$API/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"officer","password":"vajans2024"}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
echo "TOKEN_LEN=${#TOKEN}"
echo "===CREATE JOB==="
curl -s -i -X POST "$API/api/v1/jobs/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"title":"test2","created_by":"procurement.officer","metadata":{"tender_ref":"test2/ai","description":"second eval"}}'
