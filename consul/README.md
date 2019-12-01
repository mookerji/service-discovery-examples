docker inspect --format "{{json .State.Health }}" consul_proxy_1  | jq . | less
