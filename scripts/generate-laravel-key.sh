#!/bin/bash
# Generate a Laravel APP_KEY in the correct format: base64:<32 random bytes>
echo "base64:$(openssl rand -base64 32)"
