COMPOSE = docker compose -f config/docker/docker-compose.yml
ifeq ($(PROFILE),nested-virt)
COMPOSE += -f config/docker/docker-compose.kvm.yml
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
