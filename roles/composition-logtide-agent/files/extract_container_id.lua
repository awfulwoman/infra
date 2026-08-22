-- Extract container ID and name from Docker log filepath
-- Path format: /var/lib/docker/containers/CONTAINER_ID/CONTAINER_ID-json.log
-- The container name is not part of the path, so it is read from the
-- config.v2.json file that Docker keeps next to the log file.

local name_cache = {}

local function lookup_container_name(container_id)
    local cached = name_cache[container_id]
    if cached ~= nil then
        return cached or nil
    end

    local name = nil
    local path = "/var/lib/docker/containers/" .. container_id .. "/config.v2.json"
    local file = io.open(path, "r")
    if file then
        local content = file:read("*a")
        file:close()
        if content then
            name = content:match('"Name"%s*:%s*"/([^"]+)"')
        end
    end

    name_cache[container_id] = name or false
    return name
end

function extract_container_id(tag, timestamp, record)
    local filepath = record["filepath"]

    if filepath then
        local container_id = filepath:match("/var/lib/docker/containers/([^/]+)/")

        if container_id then
            record["container_id"] = container_id
            record["container_short_id"] = container_id:sub(1, 12)
            record["container_name"] = lookup_container_name(container_id)
                or record["container_short_id"]
        end
    end

    return 1, timestamp, record
end
