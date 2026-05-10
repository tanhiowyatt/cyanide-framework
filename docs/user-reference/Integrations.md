# SIEM & External Integrations

Cyanide is designed to be a high-fidelity data sensor. Instead of drowning you in noise, it provides structured, actionable intelligence that integrates seamlessly with modern security stacks.

---

### Supported Output Backends

Cyanide currently includes a wide variety of native output plugins:

*   **Databases**: SQLite, MySQL, PostgreSQL, MongoDB, RethinkDB.
*   **Analytics & SIEM**: Elasticsearch, Splunk (HEC), Syslog.
*   **Specialized Alerting**: Slack, Discord, Telegram.
*   **Threat Intelligence**: HPFeeds (Threat Intel), STIX 2.1 & MISP (Structured IOC reports).

---

## Technical Architecture

Every plugin operates in its own dedicated background thread with a thread-safe queue. This ensures that even if your Elasticsearch or Splunk server is slow, the framework session remains snappy for the attacker.

### Asynchronous Flow:
1.  **Queue**: A thread-safe queue with a default capacity of 10,000 events. If the queue fills up, events are dropped to prevent memory exhaustion.
2.  **Worker Loop**: A background loop pulls events from the queue and executes the-specific `write(event)` method.
3.  **Error Isolation**: If a database connection fails, the individual plugin thread will retry without impacting the main framework engine.

---

##  SIEM Data Schema

All exported events use a flat, searchable JSON structure.

| Field | Description | Example |
| :--- | :--- | :--- |
| `eventid` | Category of the event. | `CRITICAL_ALERT`, `command.input`, `auth` |
| `src_ip` | The attacker's source IP. | `1.2.3.4` |
| `is_malicious` | ML Engine's verdict. | `true` |
| `session` | Unique session trace ID. | `dfa1-423b-88...` |

---

## SIEM Alerting Manifest (Example Rules)

Use these logic blocks to build high-fidelity alerts in **Elasticsearch (Kibana)** or **Splunk**.

### 1. The "Red Phone" (Critical)
**Trigger**: Attacker touches a honeytoken.
*   **Logic**: `eventid: "CRITICAL_ALERT"`
*   **Action**: PagerDuty / Slack. This indicates a human attacker exploring the system.

### 2. Payload Extraction (High)
**Trigger**: Attacker attempts to download a file or URL.
*   **Logic**: `eventid: "ioc_extracted"`
*   **Search**: Look for `wget`, `curl`, or `ftp` in `command.input`.

### 3. Successful Intrusion (Medium)
**Trigger**: Valid credentials guessed.
*   **Logic**: `eventid: "auth" AND success: true`

---

##  Creating a Custom Plugin
For specialized needs (e.g., calling an internal API), you can write a custom plugin:
1.  **Code**: Create `src/cyanide/output/my_plugin.py` inheriting from `OutputPlugin`.
2.  **Logic**: Implement the `write(self, event)` method.
3.  **Enable**: Add `my_plugin: { enabled: true }` to your `outputs` config.

---

## Quick Integration: Webhooks (Slack)

To get real-time alerts via Slack, add these environment variables:

### Slack
```bash
CYANIDE_OUTPUT_SLACK_ENABLED=true
CYANIDE_OUTPUT_SLACK_WEBHOOK_URL="https://hooks.slack.com/services/XXXX/YYYY/ZZZZ"
```

### Discord
Discord integration uses Webhooks for alerts and an optional Bot Token for the `/report` command.

```bash
CYANIDE_OUTPUT_DISCORD_ENABLED=true
CYANIDE_OUTPUT_DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
# Optional: Required only for /report command
CYANIDE_OUTPUT_DISCORD_BOT_TOKEN="your_bot_token"
CYANIDE_OUTPUT_DISCORD_REPORT_CHANNEL_ID="target_channel_id"
```

> [!IMPORTANT]
> To use the `/report` command in Discord, you **must** provide a dedicated Bot Token and Channel ID. The Webhook alone cannot listen for messages.

### Telegram
Telegram uses a single Bot Token for both alerts and interactive commands.

```bash
CYANIDE_OUTPUT_TELEGRAM_ENABLED=true
CYANIDE_OUTPUT_TELEGRAM_TOKEN="123456:ABC..."
CYANIDE_OUTPUT_TELEGRAM_CHAT_ID="987654321"
```

---

## Interactive Commands (/report)

Both Discord and Telegram support the `/report` command. When triggered by an authorized user (based on `chat_id` or `channel_id`), the framework will:
1.  Generate the latest STIX 2.1 and MISP IOC reports.
2.  Upload them as physical **file attachments** (bypassing platform character limits).

> [!NOTE]
> For **Discord**, the framework must be invited to the server as a Bot with message-reading permissions. For **Telegram**, simply send the command to your bot.

##  Batching and Spam Protection

Slack has strict rate limits and message length restrictions. To prevent being banned or losing events, Cyanide supports batching:

| Variable | Default | Description |
| :--- | :--- | :--- |
| `CYANIDE_OUTPUT_*_BATCH_SIZE` | `1` | Number of events to bundle into a single message. |
| `CYANIDE_OUTPUT_*_BATCH_TIMEOUT` | `2.0` | Max seconds to wait before sending a partial batch. |
| `CYANIDE_OUTPUT_*_MAX_CONTENT_LENGTH`| *Platform Dependent* | Max character length before splitting/truncating messages. |

> [!NOTE]
> Default limit: Slack (4000).

> [!TIP]
> Combine Webhooks with **Honeytokens** for a zero-noise alerting system. You will only get a notification when someone actually tries to read your "secrets."

---
<p align="center">
  <i>Revision: 1.0 - May 2026 - Cyanide Framework</i>
</p>
