# See: https://github.com/hashicorp/consul-template#configuration-file-format

consul {
  address = "registry:8500"
  retry {
    enabled = true
    attempts = 12
    backoff = "250ms"
    max_backoff = "1m"
  }
}

log_level = "info"

wait {
  min = "5s"
  max = "10s"
}

template {
  source = "/consul-template/config/proxy.ctmpl"
  destination = "/consul-template/data/proxy.yaml"
  create_dest_dirs = true
  command = "curl -X POST --fail --silent --show-error --connect-timeout 5 --max-time 10 --retry 5 --retry-delay 1 --retry-max-time 40 --retry-connrefuse http://proxy/_hooks/reload/config"
  command_timeout = "60s"
  perms = 0600
  backup = true
  wait {
    min = "2s"
    max = "10s"
  }
}
