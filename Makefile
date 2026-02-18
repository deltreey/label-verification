APP_NAME := label-verification
EXPORT_DIR := export
PYTHON := uv run python
ENVFILE ?= .env

.PHONY: build dev test

# Load .env file
ifneq (,$(wildcard $(ENVFILE)))
  include $(ENVFILE)
  export $(shell sed 's/=.*//' $(ENVFILE))
endif


build:
	docker build .

dev:
	$(PYTHON) main.py

test:
	$(PYTHON) -m pytest tests