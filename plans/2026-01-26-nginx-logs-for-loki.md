# Plan: Nginx Logs for Loki/Grafana (awfulwoman composition)

**Date:** 2026-01-26
**Status:** Draft
**Host:** vm-awfulwoman-hetzner

## Overview

Configure Nginx in the `awfulwoman` composition to output JSON-formatted access logs with structured data that Loki can efficiently index and Grafana can visualize.

## Current State

- Nginx uses standard Combined Log Format (`main`)
- Logs go to `/var/log/nginx/access.log` inside container
- Docker captures logs and sends to stdout
- Promtail with Docker SD collects logs from container
- Labels available: `host`, `container_name=awfulwoman`, `composition=awfulwoman`, `job=docker`

## Proposed Changes

### 1. Configure Nginx JSON Logging

Update `ansible/roles/composition-awfulwoman/templates/nginx.conf` to add JSON log format:

```nginx
http {
    # Existing log format (keep for compatibility)
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    # New JSON log format for Loki
    log_format json_combined escape=json
    '{'
        '"time_local":"$time_local",'
        '"remote_addr":"$remote_addr",'
        '"remote_user":"$remote_user",'
        '"request":"$request",'
        '"request_method":"$request_method",'
        '"request_uri":"$request_uri",'
        '"server_protocol":"$server_protocol",'
        '"status":$status,'
        '"body_bytes_sent":$body_bytes_sent,'
        '"request_time":$request_time,'
        '"upstream_response_time":"$upstream_response_time",'
        '"http_referer":"$http_referer",'
        '"http_user_agent":"$http_user_agent",'
        '"http_x_forwarded_for":"$http_x_forwarded_for",'
        '"host":"$host"'
    '}';

    # Use JSON format for access logs
    access_log /var/log/nginx/access.log json_combined;
    error_log  /var/log/nginx/error.log notice;
}
```

### 2. Update Promtail Pipeline (Optional Enhancement)

While Promtail with Docker SD will automatically collect the logs, we can optionally add a specific pipeline for Nginx containers to extract additional labels.

Update `ansible/roles/system-promtail/templates/promtail-config.yaml.j2`:

```yaml
scrape_configs:
  - job_name: docker
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
        refresh_interval: 5s

    relabel_configs:
      # ... existing relabel configs ...

    pipeline_stages:
      # Parse JSON log format
      - json:
          expressions:
            output: log
            stream: stream

      # For Nginx containers, parse the log JSON
      - match:
          selector: '{container_name="awfulwoman"}'
          stages:
            - json:
                expressions:
                  method: request_method
                  status: status
                  request_time: request_time
                  path: request_uri
                  user_agent: http_user_agent

            # Extract labels for filtering
            - labels:
                method:
                status:

            # Parse request_time as number
            - template:
                source: request_time
                template: '{{ if .request_time }}{{ .request_time }}{{ else }}0{{ end }}'

            # Keep full log line
            - output:
                source: output

      # Default handling for non-Nginx containers
      - match:
          selector: '{container_name!="awfulwoman"}'
          stages:
            - labels:
                stream:
            - output:
                source: output
```

### 3. Create Grafana Dashboard

Create `ansible/roles/composition-grafana/files/dashboards/nginx-web-traffic.json` with panels:

**Overview Panels:**
- Total requests (5m)
- Error rate (4xx, 5xx)
- Average response time
- Requests per second timeline

**Traffic Analysis:**
- Requests by HTTP method (GET, POST, etc.)
- Requests by status code (200, 404, 500, etc.)
- Top 10 requested paths
- Top 10 referrers

**Performance:**
- Response time histogram
- Slowest requests (>1s)
- Response time by path

**Security/Monitoring:**
- 4xx errors (client errors) timeline
- 5xx errors (server errors) timeline
- Failed requests log stream
- Non-200 status codes table

**Sample LogQL Queries:**

```logql
# Total requests (5m)
sum(count_over_time({container_name="awfulwoman"} [5m]))

# Error rate
sum(rate({container_name="awfulwoman"} | json | status >= 400 [5m]))
/
sum(rate({container_name="awfulwoman"} [5m]))

# Requests by status code
sum by (status) (count_over_time({container_name="awfulwoman"} | json [5m]))

# Average response time
avg_over_time({container_name="awfulwoman"}
  | json
  | request_time != ""
  | unwrap request_time [5m])

# Top 10 paths
topk(10,
  sum by (path) (count_over_time({container_name="awfulwoman"}
    | json
    | path != "" [1h])))

# 5xx errors
{container_name="awfulwoman"} | json | status >= 500

# Slow requests
{container_name="awfulwoman"}
  | json
  | request_time > 1.0
  | line_format "{{.request_method}} {{.request_uri}} - {{.request_time}}s"
```

### 4. Add Dashboard to Grafana Role

Update `ansible/roles/composition-grafana/tasks/main.yaml`:

```yaml
- name: "Copy Nginx dashboards"
  become: true
  ansible.builtin.copy:
    src: "dashboards/{{ item }}"
    dest: "{{ composition_config }}/provisioning/dashboards/infrastructure/{{ item }}"
    owner: "{{ ansible_user }}"
    group: "{{ ansible_user }}"
    mode: "0774"
  loop:
    - nginx-web-traffic.json
```

## Benefits

1. **Structured Data:** JSON logs are machine-readable and eliminate complex regex parsing
2. **Rich Labels:** HTTP method, status code directly available as labels for fast filtering
3. **Performance Metrics:** Request time allows tracking slow endpoints
4. **Better Queries:** LogQL can directly query JSON fields without parsing
5. **Grafana Visualizations:** Easier to create charts, tables, and alerts from structured data

## Considerations

1. **Log Volume:** JSON logs are slightly larger than combined format (acceptable trade-off)
2. **Backward Compatibility:** Keep error logs in standard format
3. **Privacy:** Consider whether to log user agents, IPs based on privacy requirements
4. **Retention:** Ensure Loki's 30-day retention handles increased log volume

## Implementation Steps

1. Update `nginx.conf` template with JSON log format
2. Deploy updated config to vm-awfulwoman-hetzner
3. Verify JSON logs appearing in Loki
4. (Optional) Update Promtail pipeline for label extraction
5. Create Nginx traffic dashboard
6. Deploy dashboard to Grafana
7. Test queries and visualizations

## Testing

```bash
# Check Nginx container logs are JSON
ssh vm-awfulwoman-hetzner "docker logs awfulwoman --tail 5"

# Query Loki for awfulwoman logs
curl -G "https://loki.ewwww.eu/loki/api/v1/query" \
  --data-urlencode 'query={container_name="awfulwoman"}' \
  --data-urlencode 'limit=5' | jq

# Test JSON parsing
curl -G "https://loki.ewwww.eu/loki/api/v1/query" \
  --data-urlencode 'query={container_name="awfulwoman"} | json | status >= 400' \
  --data-urlencode 'limit=5' | jq
```

## Future Enhancements

- Add GeoIP parsing for `remote_addr` to show traffic by country
- Create alerts for high error rates or slow response times
- Log sampling for very high-traffic sites
- Add custom fields (e.g., session ID, request ID for tracing)

## References

- [Nginx Log Format Documentation](https://nginx.org/en/docs/http/ngx_http_log_module.html#log_format)
- [Grafana Loki JSON Stage](https://grafana.com/docs/loki/latest/send-data/promtail/stages/json/)
- [LogQL Queries](https://grafana.com/docs/loki/latest/query/)
