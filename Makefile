.PHONY: verify test up down

verify:
	bash scripts/verify.sh

test:
	bash scripts/test.sh

up:
	docker compose up --build -d

down:
	docker compose down
