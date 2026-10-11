#############################################################################
# ZONES
# Define name server zones that are to be managed (e.g. example.com)
#############################################################################
{% if (infra_publicresources_hetzner_domain is iterable) and (infra_publicresources_hetzner_domain | length > 0) %}
{% for item in infra_publicresources_hetzner_domain %}
{% if (item.domain is defined) and (item.id is defined) %}

resource "hcloud_zone" "{{ item.id }}" {
  name = "{{ item.domain }}"
  mode = "primary"
}

{% endif %}
{% endfor %}
{% endif %}


#############################################################################
# ZONE RECORDS
# Records are grouped by (hostname, type) into rrsets since Hetzner requires
# all records sharing the same zone/name/type to be in a single resource.
#############################################################################
{% if (infra_publicresources_hetzner_domain is iterable) and (infra_publicresources_hetzner_domain | length > 0) %}
{% for item in infra_publicresources_hetzner_domain %}

{% if item.domain is defined and item.records is defined %}
{% set ns = namespace(seen=[]) %}
{% for record in item.records if record.type is defined and record.value is defined %}
{% set hostname = record.hostname | default('@') %}
{% set rrset_key = hostname ~ '|' ~ record.type %}
{% if rrset_key not in ns.seen %}
{% set ns.seen = ns.seen + [rrset_key] %}
{% set rrset_id = item.id ~ '_' ~ (hostname | replace('.', '_') | replace('@', 'root') | replace('-', '_')) ~ '_' ~ (record.type | lower) %}

resource "hcloud_zone_rrset" "{{ rrset_id }}" {
  zone = hcloud_zone.{{ item.id }}.name
  name = "{{ hostname }}"
  type = "{{ record.type }}"

  records = [
{% for r in item.records if r.type is defined and r.value is defined and r.type == record.type and (r.hostname | default('@')) == hostname %}
    {% if r.type == "TXT" %}
    { value = provider::hcloud::txt_record("{{ r.value }}") }{{ "," if not loop.last }}
    {% elif r.type in ["MX", "SRV"] and r.priority is defined %}
    { value = "{{ r.priority }} {{ r.value }}" }{{ "," if not loop.last }}
    {% else %}
    {% if '.ip_address' in r.value %}
    { value = {{ r.value | replace('infra_publicresources_', '') }} }{{ "," if not loop.last }}
    {% else %}
    { value = "{{ r.value }}" }{{ "," if not loop.last }}
    {% endif %}
    {% endif %}
{% endfor %}
            ]
{# An rrset can only have one TTL value (it applies to the whole set), so grab the first one found #}
{% for r in item.records if r.type == record.type and (r.hostname | default('@')) == hostname and r.ttl is defined %}
{% if loop.first %}

  ttl = {{ r.ttl }}
{% endif %}
{% endfor %}
}

{% endif %}
{% endfor %}
{% endif %}

{% endfor %}
{% endif %}


#############################################################################
# PUBLIC KEYS
# Public keys used to access compute instances
#############################################################################
{% for key in github_keys_list %}
resource "hcloud_ssh_key" "githubkey{{ loop.index }}" {
  name       = "Github Key {{ loop.index }}"
  public_key = "{{ key }}"
}
{% endfor %}


#############################################################################
# COMPUTE INSTANCES
#############################################################################
{% for server in infra_publicresources_hcloud_server %}
{% if server.id is defined %}

resource "hcloud_server" "{{ server.id }}" {
  name        = "{{ server.name }}"
  image       = "{{ server.image }}"
  server_type = "{{ server.size }}"
  location    = "{{ server.region }}"
  user_data = file("{{ infra_publicresources_terraform_working_dir }}/cloud-init.yaml")
  ssh_keys = [
{% for key in github_keys_list %}
    hcloud_ssh_key.githubkey{{ loop.index }}.id{{ "," if not loop.last }}
{% endfor %}
  ]
  public_net {
    ipv4_enabled = true
    ipv6_enabled = true
  }

  # ssh_keys and user_data only take effect when a server is created, but a
  # change to either forces a replacement. The key list comes from GitHub and
  # changes whenever a key is added there, so without this an unrelated apply
  # destroys the server.
  lifecycle {
    ignore_changes = [ssh_keys, user_data]
  }

{% if server.labels is defined %}
  labels = {
    {% for label in server.labels %}
    {% if label.value is defined %}
    "{{ label.key }}" : "{{ label.value }}"
    {% else %}
    "{{ label.key }}" : ""
    {% endif %}
    {% endfor %}
  }
{% endif %}

}

{% endif %}
{% endfor %}



#############################################################################
# BLOCK STORAGE VOLUMES
# Block-level storage - can be attached to compute as a drive
#############################################################################
{% if infra_publicresources_hcloud_volume is defined %}
{% for volume in infra_publicresources_hcloud_volume %}

resource "hcloud_volume" "{{ volume.id }}" {
  name = "{{ volume.name }}"
  size = {{ volume.size }}
  server_id = hcloud_server.{{ volume.server_id }}.id
  automount = false
}

{% endfor %}
{% endif %}

#############################################################################
# STORAGE BOXES
# File storage reached over SFTP. Used for the Offsite copy.
#############################################################################
{% for box in infra_publicresources_hcloud_storage_box | default([]) %}

variable "storage_box_{{ box.id }}_password" {
  type      = string
  sensitive = true
}

resource "hcloud_storage_box" "{{ box.id }}" {
  name             = "{{ box.name }}"
  storage_box_type = "{{ box.type }}"
  location         = "{{ box.region }}"
  password         = var.storage_box_{{ box.id }}_password

  access_settings = {
    reachable_externally = true
    ssh_enabled          = true
    samba_enabled        = false
    webdav_enabled       = false
    zfs_enabled          = true
  }

{% if box.snapshots is defined %}
  snapshot_plan = {
    hour          = {{ box.snapshots.hour }}
    minute        = {{ box.snapshots.minute }}
    max_snapshots = {{ box.snapshots.keep }}
  }

{% endif %}
  delete_protection = true

  # Replacing a Storage Box destroys everything in it.
  lifecycle {
    prevent_destroy = true
    ignore_changes  = [ssh_keys]
  }
}

{% for sub in box.subaccounts | default([]) %}
variable "storage_box_{{ box.id }}_{{ sub.id }}_password" {
  type      = string
  sensitive = true
}

resource "hcloud_storage_box_subaccount" "{{ box.id }}_{{ sub.id }}" {
  storage_box_id = hcloud_storage_box.{{ box.id }}.id
  name           = "{{ sub.id }}"
  home_directory = "{{ sub.home_directory }}"
  password       = var.storage_box_{{ box.id }}_{{ sub.id }}_password
{% if sub.description is defined %}
  description    = "{{ sub.description }}"
{% endif %}

  access_settings = {
    reachable_externally = true
    ssh_enabled          = true
    samba_enabled        = false
    webdav_enabled       = false
    readonly             = false
  }
}

output "storage_box_{{ box.id }}_{{ sub.id }}" {
  value = {
    host = hcloud_storage_box_subaccount.{{ box.id }}_{{ sub.id }}.server
    user = hcloud_storage_box_subaccount.{{ box.id }}_{{ sub.id }}.username
  }
}

{% endfor %}
{% endfor %}

#############################################################################
# FLOATING IPS
# Reserved IPs that don't change
#############################################################################
{% for reservedip in infra_publicresources_hcloud_floating_ip %}
{% if reservedip.id is defined %}

resource "hcloud_floating_ip" "{{ reservedip.id }}" {
  home_location = "{{ reservedip.region }}"
  type = "{{ reservedip.type }}"
}

{% endif %}
{% endfor %}


{% for ipassignment in infra_publicresources_hcloud_floating_ip_assignment %}
{% if ipassignment.id is defined %}

resource "hcloud_floating_ip_assignment" "{{ ipassignment.id }}" {
  floating_ip_id = hcloud_floating_ip.{{ ipassignment.reservedip }}.id
  server_id = hcloud_server.{{ ipassignment.server_id }}.id
}

# Reverse DNS for the floating IP
resource "hcloud_rdns" "{{ ipassignment.id }}" {
  floating_ip_id = "${hcloud_floating_ip.{{ ipassignment.reservedip }}.id}"
  ip_address     = "${hcloud_floating_ip.{{ ipassignment.reservedip }}.ip_address}"
  dns_ptr        = "{{ domainname_personal }}"
}

{% endif %}
{% endfor %}


#############################################################################
# FIREWALLS
# Cloud-level firewalls that protect resources behind them
#############################################################################
{% if infra_publicresources_hcloud_firewall is defined %}
{% for firewall in infra_publicresources_hcloud_firewall %}
{% if firewall.id is defined %}

resource "hcloud_firewall" "{{ firewall.id }}" {
  name = "{{ firewall.id }}"
{% if firewall.apply_to_label is defined %}
  apply_to {
    label_selector  = "{{ firewall.apply_to_label }}"
  }
{% endif %}

  {% if firewall.inbound is defined %}
  {% for inbound in firewall.inbound %}
  rule {
    direction = "in"
    protocol = "{{ inbound.protocol }}"
    {% if inbound.port_range is defined %}
    port = "{{ inbound.port_range }}"
    {% endif %}

    {% if inbound.ip_addresses is defined %}
    source_ips = [
      {% for ipaddress in inbound.ip_addresses %}
      "{{ ipaddress }}"{{ "," if not loop.last }}
      {% endfor %}
    ]
    {% endif %}

  }
  {% endfor %}
  {% endif %}

  {% if firewall.outbound is defined %}
  {% for outbound in firewall.outbound %}
  rule {
    direction = "out"
    protocol = "{{ outbound.protocol }}"
    {% if outbound.port_range is defined %}
    port = "{{ outbound.port_range }}"
    {% endif %}

    {% if outbound.ip_addresses is defined %}
    destination_ips = [
      {% for ipaddress in outbound.ip_addresses %}
      "{{ ipaddress }}"{{ "," if not loop.last }}
      {% endfor %}
    ]
    {% endif %}
  }
  {% endfor %}
  {% endif %}
}

{% endif %}
{% endfor %}
{% endif %}
