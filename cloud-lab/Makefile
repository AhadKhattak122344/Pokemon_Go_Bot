COMPOSE = docker compose
ifeq ($(PROFILE),nested-virt)
COMPOSE += -f docker-compose.yml -f docker-compose.kvm.yml
endif

.PHONY: build up smoke down test
build:
	$(COMPOSE) build
up:
	$(COMPOSE) up -d --wait --wait-timeout 1900 emulator
smoke:
	$(COMPOSE) run --rm lab smoke
down:
	$(COMPOSE) down --remove-orphans
test:
	$(COMPOSE) run --rm --no-deps --entrypoint python lab -m pytest
