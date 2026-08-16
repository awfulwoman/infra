-- Map syslog priority/severity to log level and apply timezone correction.
-- RFC 3164 timestamps carry no timezone; SYSLOG_TZ_OFFSET (hours from UTC) corrects them.

local tz_offset_hours = tonumber(os.getenv("SYSLOG_TZ_OFFSET")) or 0
local tz_offset_seconds = tz_offset_hours * 3600

function map_syslog_level(tag, timestamp, record)
    local pri = tonumber(record["pri"])

    if pri then
        local severity = pri % 8
        local level_map = {
            [0] = "emergency",
            [1] = "alert",
            [2] = "critical",
            [3] = "error",
            [4] = "warning",
            [5] = "notice",
            [6] = "info",
            [7] = "debug"
        }
        record["level"] = level_map[severity] or "info"
    else
        record["level"] = "info"
    end

    local adjusted_timestamp = timestamp - tz_offset_seconds
    record["time"] = os.date("!%Y-%m-%dT%H:%M:%SZ", adjusted_timestamp)

    if record["host"] and record["host"] ~= "-" then
        record["hostname"] = record["host"]
    end

    if not record["service"] and record["ident"] and record["ident"] ~= "-" then
        record["service"] = record["ident"]
    elseif not record["service"] and record["hostname"] then
        record["service"] = record["hostname"]
    else
        record["service"] = "syslog"
    end

    record["pri"] = nil
    record["ident"] = nil
    record["host"] = nil

    return 1, adjusted_timestamp, record
end
