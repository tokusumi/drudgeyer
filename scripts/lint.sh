#!/usr/bin/env bash

set -e
set -x

mypy drudgeyer
flake8 drudgeyer tests
black drudgeyer tests --check
isort drudgeyer tests scripts --check-only