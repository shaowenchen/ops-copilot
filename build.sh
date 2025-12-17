#!/bin/bash

echo "Building ops-copilot..."

# Initialize go module if needed
if [ ! -f "go.sum" ]; then
    echo "Initializing go module..."
    go mod download
    go mod tidy
fi

# Build the binary
echo "Compiling..."
go build -o ops-copilot main.go

if [ $? -eq 0 ]; then
    echo "Build successful! Binary created: ops-copilot"
    echo "You can test it with: ./ops-copilot version"
else
    echo "Build failed!"
    exit 1
fi
