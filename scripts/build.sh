#!/bin/bash
set -e

# Build deployment.zip for Lambda deployment
# Run this script from the project root directory

BUILD_DIR=$(mktemp -d)

cp app/app.py app/run.sh app/requirements.txt "$BUILD_DIR/"
pip3 install -r app/requirements.txt -t "$BUILD_DIR/" --quiet
chmod +x "$BUILD_DIR/run.sh"

cd "$BUILD_DIR"
zip -r "$OLDPWD/deployment.zip" .

rm -rf "$BUILD_DIR"

echo "Built deployment.zip"
