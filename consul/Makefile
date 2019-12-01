.PHONY: run
run:
	@docker-compose --compatibility up --build --remove-orphans

.PHONY: format
format:
	@find . -type f -name "*.py" | xargs yapf --in-place


.PHONY: clean
clean:
	@docker-compose --compatibility down -v

.PHONY: login
login:
	@docker exec -it  consul_proxy_1 /bin/bash
