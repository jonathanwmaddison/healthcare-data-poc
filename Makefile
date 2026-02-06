.PHONY: generate verify run services clean

generate:
	python3 scripts/generate.py

verify:
	python3 scripts/verify.py

run:
	python3 scripts/run.py --agent anthropic --all-tasks

services:
	docker-compose up -d

clean:
	rm -rf results/benchmark_runs/*
