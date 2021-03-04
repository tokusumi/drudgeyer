#!/bin/sh -e
set -x

isort drudgeyer tests scripts 
sh ./scripts/format.sh