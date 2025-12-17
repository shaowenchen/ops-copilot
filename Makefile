.PHONY: build install clean test deps

build: deps
	go build -o ops-copilot main.go

install: deps
	go install

clean:
	rm -f ops-copilot

test: deps
	go test ./...

deps:
	go mod download
	go mod tidy
