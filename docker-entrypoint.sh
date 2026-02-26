#!/bin/sh
set -e

if [ -f /etc/build-info ]; then
  echo "=== Image build info ==="
  cat /etc/build-info
  echo "========================"
fi

echo  "=== Testing ssh key ==="
ssh -T git@github.com || [ $? -eq 1 ]

echo "Run command: $@"
exec "$@"
