#!/bin/sh -e
set -x

autoflake --remove-all-unused-imports --recursive --in-place drudgeyer tests scripts --exclude=__init__.py
black drudgeyer tests scripts
isort drudgeyer tests scripts
