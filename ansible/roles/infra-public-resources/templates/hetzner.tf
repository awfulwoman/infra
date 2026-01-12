#############################################################################
# ZONES
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
{% for record in item.records if record.type is defined and record.value is defined and record.type == record.type and (record.hostname | default('@')) == hostname %}
    {% if record.type == "TXT" %}
    { value = provider::hcloud::txt_record("{{ record.value }}") }{{ "," if not loop.last }}
    {% elif record.type in ["MX", "SRV"] and record.priority is defined %}
    { value = "{{ record.priority }} {{ record.value }}" }{{ "," if not loop.last }}
    {% else %}
    { value = "{{ record.value }}" }{{ "," if not loop.last }}
    {% endif %}
{% endfor %}
            ]
{% for record in item.records if record.type == record.type and (record.hostname | default('@')) == hostname and record.ttl is defined %}
{% if loop.first %}

  ttl = {{ record.ttl }}
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
}

{% endif %}
{% endfor %}


#############################################################################
# RESERVED IPS
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

{% endif %}
{% endfor %}


#############################################################################
# FIREWALLS
#############################################################################
{% if infra_publicresources_digitalocean_firewall is defined %}
{% for firewall in infra_publicresources_digitalocean_firewall %}
{% if firewall.id is defined %}

resource "hcloud_firewall" "{{ firewall.id }}" {
  name = "{{ firewall.id }}"

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
    source_ips = [
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
