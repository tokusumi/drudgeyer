# Drudgeyer

[![Tests](https://github.com/tokusumi/drudgeyer/actions/workflows/test.yaml/badge.svg)](https://github.com/tokusumi/drudgeyer/actions/workflows/test.yaml)
[![codecov](https://codecov.io/gh/tokusumi/drudgeyer/branch/main/graph/badge.svg?token=fZoZJLYCla)](https://codecov.io/gh/tokusumi/drudgeyer)

(Currently under early developments.)

Simple lightweight training scheduler (job queue) for ML in on-premise/cloud.

features (in the future):

* Ease of setup
* Low resources (low scalability) queue
* Executing shell command
* Support for on-premise and cloud environments

## Roadmap

* [x] Add file logger
* [ ] Add DB (SQLite3), Redis Queue
* [ ] Add registration task with dependency directory
* [ ] Add notifier (slack, line notify, sidekiq)
* [ ] Add documentation
* [ ] Make worker daemon process 
* [x] Add Test CI (GitHub Action)
