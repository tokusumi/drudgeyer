# Drudgeyer

(Currently under early developments.)

Simple lightweight training scheduler (job queue) for ML in on-premise/cloud.

features (in the future):

* Ease of setup
* Low resources (low scalability) queue
* Executing shell command
* Support for on-premise and cloud environments

## Roadmap

* [ ] Add log logger
* [ ] Add DB (SQLite3), Redis Queue
* [ ] Add registration task with dependency directory
* [ ] Add notifier (slack, line notify, sidekiq)
* [ ] Add documentation
* [ ] Fix Ctrl-C problem for asyncio.sleep
* [ ] Make worker daemon process 
* [ ] Add Test
