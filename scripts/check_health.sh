#!/bin/bash
echo "Checking API health..."
curl -s https://api.tokenbudget.com/health | python3 -m json.tool
echo ""
echo "Checking frontend..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://tokenbudget.com)
echo "Frontend status: $STATUS"
echo ""
echo "Health check complete"
