# Protein Plate — small helpers.
#
# `make build` regenerates the site from data/ + templates/. `make preview`
# rebuilds it and serves it on the dev port. `make deploy` runs the same server
# as an always-on systemd service on port 9002.

SERVICE := proteinplate
UNIT    := deploy/$(SERVICE).service

EDITOR_SERVICE := proteinplate-editor
EDITOR_UNIT    := deploy/$(EDITOR_SERVICE).service

.PHONY: help build preview deploy undeploy status logs edit deploy-editor undeploy-editor

help:  ## show this list
	@grep -E '^[a-z]+:.*?## ' $(MAKEFILE_LIST) | awk -F':.*?## ' '{printf "  make %-10s %s\n", $$1, $$2}'

build:  ## rebuild docs/ from data/ + templates/
	.venv/bin/python generate.py

preview:  ## serve the dev preview on http://simon-dev.rebecchi.uk:8090
	.venv/bin/python serve.py

deploy:  ## install/refresh the always-on site service and start it
	sudo cp $(UNIT) /etc/systemd/system/$(SERVICE).service
	sudo systemctl daemon-reload
	sudo systemctl enable --now $(SERVICE)
	sudo systemctl restart $(SERVICE)
	@sudo systemctl --no-pager --lines=0 status $(SERVICE) | head -6

undeploy:  ## stop the site service and remove it
	-sudo systemctl disable --now $(SERVICE)
	sudo rm -f /etc/systemd/system/$(SERVICE).service
	sudo systemctl daemon-reload

status:  ## is the site service running?
	@sudo systemctl --no-pager --lines=0 status $(SERVICE) | head -6

logs:  ## follow the site service's log
	sudo journalctl -u $(SERVICE) -f

edit:  ## run the editing page in the foreground (http://simon-dev.rebecchi.uk:9003)
	.venv/bin/python editor.py

deploy-editor:  ## install/refresh the editing page service and start it
	sudo cp $(EDITOR_UNIT) /etc/systemd/system/$(EDITOR_SERVICE).service
	sudo systemctl daemon-reload
	sudo systemctl enable --now $(EDITOR_SERVICE)
	sudo systemctl restart $(EDITOR_SERVICE)
	@sudo systemctl --no-pager --lines=0 status $(EDITOR_SERVICE) | head -6

undeploy-editor:  ## stop the editing page and remove its service
	-sudo systemctl disable --now $(EDITOR_SERVICE)
	sudo rm -f /etc/systemd/system/$(EDITOR_SERVICE).service
	sudo systemctl daemon-reload
