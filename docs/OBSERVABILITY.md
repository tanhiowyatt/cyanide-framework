# Observability Guide

Cyanide supports a comprehensive observability stack, including **Structured Logging**, **Prometheus** for metrics, and **OpenTelemetry** for distributed tracing.

## 0. Structured Logging (JSON)

Cyanide uses a custom multi-file logging system located in `src/cyanide/logger.py`. All events are recorded as structured JSON, making them easy to parse and analyze with tools like ClickHouse, ELK, or DuckDB.

### Log Directories
By default, logs are stored in `var/log/cyanide/`. You can change this in `cyanide.cfg`.

### Log Files
*   **`cyanide-server.json`**: System events, service startup/shutdown, and critical errors.
*   **`cyanide-fs.json`**: Hacker activity, including:
    *   Auth attempts (user/pass).
    *   Command input (raw and analyzed).
    *   TTY session events.
    *   File quarantine events.
*   **`cyanide-ml.json`**: Detailed internal "thoughts" of the ML engine and its final verdicts.
*   **`cyanide-stats.json`**: Periodic snapshots (60s interval) of the entire system state.

### TTY Replays
Interactive SSH/Telnet sessions are recorded in two formats:
1.  **JSONL**: Direct data stream for easy reading.
2.  **Timing + TypeScript**: Standard format for the `scriptreplay` utility, allowing you to watch the attack in real-time as it happened.

---

## 1. Metrics (Prometheus)

The project Cyanide includes a built-in HTTP server for health checks, metrics, and log access. By default, it listens on port `9090`.

### Endpoints
*   **`/metrics`**: Prometheus-compatible text format. Includes both core stats and ML metrics.
*   **`/stats`**: Full system state as a raw JSON object (useful for custom web UIs).
*   **`/health`**: Returns `200 OK` if the core SSH/Telnet services are running.
*   **`/logs`**: Interactive log browser. Allows listing and viewing files in the honeypot log directory (e.g., `/logs/cyanide.json`, `/logs/tty/`).

### Prometheus Metrics

Cyanide exposes the following metrics on `:9090/metrics`:

| Metric | Type | Description |
|--------|------|-------------|
| `cyanide_active_sessions` | Gauge | Currently active SSH/Telnet sessions |
| `cyanide_total_sessions_total` | Counter | Total connections since startup |
| `cyanide_unique_attackers_total` | Counter | Total unique attacker IP addresses |
| `cyanide_uptime_seconds` | Counter | Honeypot uptime in seconds |
| `cyanide_auth_success_total` | Counter | Successful login attempts |
| `cyanide_auth_failures_total` | Counter | Failed login attempts |
| `cyanide_protocols_total` | Counter | Connections per protocol (ssh/telnet) |
| `cyanide_honeytoken_hits_total` | Counter | Filesystem access to sensitive paths |
| `cyanide_file_ops_total` | Counter | File operations (read, write, delete) |
| `cyanide_traffic_bytes_in_total` | Counter | Total inbound traffic in bytes |
| `cyanide_traffic_bytes_out_total` | Counter | Total outbound traffic in bytes |
| `cyanide_command_not_found_total` | Counter | Count of "command not found" errors |
| `cyanide_malware_scans_total` | Counter | Total files scanned by VT/ML |
| `cyanide_malicious_files_total` | Counter | Total malicious files detected |

---

## 2. Distributed Tracing (OpenTelemetry)

Cyanide uses **OpenTelemetry (OTel)** to track request flow across internal services (e.g., from an SSH command to an ML verdict).

### Implementation Details
Tracing is handled in `src/cyanide/core/telemetry.py`. It initializes a `TracerProvider` and can export data via OTLP (gRPC) to any compatible collector.

### Span Lifecycle
1.  **Connection Setup**: A span starts when a user connects (e.g., `ssh_connection_setup`).
2.  **Command Execution**: Each command triggers an `analyze_command` span.
3.  **Attributes**: Every span is enriched with contextual metadata:
    *   `net.peer.ip`: The attacker's source IP.
    *   `user.name`: The username used for login.
    *   `command.body`: The actual command string.
    *   `net.protocol.name`: SSH or Telnet.
    *   `session.id`: Unique identifier linking all events in a session.

### Configuration
Enable OTel in `configs/app.yaml`:
```yaml
otel:
  enabled: true
  exporter: otlp
  endpoint: http://jaeger:4318/v1/traces  # Jaeger OTLP port (usually 4317 or 4318)
```

### Viewing Traces (Jaeger)
We recommend running Jaeger as part of the Docker stack. You can then view the traces at `http://localhost:16686`.

---

## 3. Dashboards and Alerts

*   **Grafana**: You can find a sample dashboard in `deployments/monitoring/grafana-dashboard.json`.
*   **AlertManager**: Sample rules for critical "Honeytoken" alerts are in `deployments/monitoring/alerts.yml`.
