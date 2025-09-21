# Ensure all DO projects exist
{% for project in infra_publicresources_projects %}
{% if project.id is defined %}
resource "digitalocean_project" "{{ project.id }}" {
  name        = "{{ project.name }}"
  description = "{{ project.description }}"
  purpose     = "Web Application"
  environment = "Production"
}
{% endif %}


# Ensure each domain zone is in the appropriate project
{% if project.resources is defined %}
resource "digitalocean_project_resources" "{{ project.id }}" {
  project = digitalocean_project.{{ project.id }}.id
  resources = [
    {% for resource in project.resources %}
    {{ resource }}.urn{{ "," if not loop.last }}
    {% endfor %}
  ]
}
{% endif %}
{% endfor %}


# Ensure all domain zones are registered with Digital Ocean
{% if (infra_publicresources_domains is iterable) and (infra_publicresources_domains | length > 0) %}
{% for item in infra_publicresources_domains %}
{% if (item.domain is defined) and (item.id is defined) %}

resource "digitalocean_domain" "{{ item.id }}" {
  name = "{{ item.domain }}"
  {% if item.ipaddress is defined %}
  {% if item.ipaddress is ansible.utils.ip_address %}
  ip_address = "{{ item.ipaddress }}"
  {% else %}
  ip_address = {{ item.ipaddress }}
  {% endif %}
  {% endif %}
}
{% endif %}
{% endfor %}
{% endif %}


# Ensure all records for domains exist
{% if (infra_publicresources_domains is iterable) and (infra_publicresources_domains | length > 0) %}
{% for item in infra_publicresources_domains %}
{% if item.domain is defined %}
{% for record in item.records %}
{% if (item.domain is defined ) 
   and (record.id is defined) 
   and (record.type is defined) 
   and (record.value is defined) %}

resource "digitalocean_record" "{{ record.id }}" {
  domain = digitalocean_domain.{{ item.id }}.id
  type   = "{{ record.type }}"
  name   = "{{ record.hostname | default('@') }}"
  value  = "{{ record.value }}"
  {% if record.priority is defined -%}
  priority = {{ record.priority }}
  {% endif -%}
  {% if record.ttl is defined -%}
  ttl = {{ record.ttl }}
  {% endif -%}
}
{% endif %}
{% endfor %}
{% endif %}
{% endfor %}
{% endif %}


# Ensure Block storage exists
{% for volume in infra_publicresources_volumes %}
{% if volume.id is defined %}

resource "digitalocean_volume" "{{ volume.id }}" {
  region = "{{ volume.region }}"
  name = "{{ volume.name }}"
  size = {{ volume.size }}
}
{% endif %}
{% endfor %}

# Ensure SSH keys exist
{% for key in github_keys_list %}

resource "digitalocean_ssh_key" "githubkey{{ loop.index }}" {
  name       = "Github Key {{ loop.index }}"
  public_key = "{{ key }}"
}
{% endfor %}

# Ensure all Droplets exist
{% for droplet in infra_publicresources_droplets %}
{% if droplet.id is defined %}

resource "digitalocean_droplet" "{{ droplet.id }}" {
  image  = "{{ droplet.image }}"
  name   = "{{ droplet.name }}"
  region = "{{ droplet.region }}"
  size   = "{{ droplet.size }}"
  monitoring = true
  user_data = file("{{ infra_publicresources_terraform_working_dir }}/cloud-init.yaml")
  ssh_keys = [
{% for key in github_keys_list %}
    digitalocean_ssh_key.githubkey{{ loop.index }}.fingerprint{{ "," if not loop.last }}
{% endfor %}
  ]
  {% if droplet.volumes is defined -%}
  volume_ids = [
    {% for volume in droplet.volumes %}
    digitalocean_volume.{{ volume }}.id{{ "," if not loop.last }}
    {% endfor %}
  ]
  {% endif -%}
  {% if droplet.tags is defined %}
  tags = [
    {% for tag in droplet.tags %}
    "{{ tag }}"{{ "," if not loop.last }}
    {% endfor %}
  ]
  {% endif %}
}

{% endif %}
{% endfor %}

# Ensure all Reserved IPs exist
{% for reservedip in infra_publicresources_reservedips %}
{% if reservedip.id is defined %}

resource "digitalocean_reserved_ip" "{{ reservedip.id }}" {
  region = "{{ reservedip.region }}"
}
{% endif %}
{% endfor %}


{% for ipassignment in infra_publicresources_reservedip_assignments %}
{% if ipassignment.id is defined %}

resource "digitalocean_reserved_ip_assignment" "{{ ipassignment.id }}" {
  ip_address = digitalocean_reserved_ip.{{ ipassignment.reservedip }}.ip_address
  droplet_id = digitalocean_droplet.{{ ipassignment.droplet }}.id
}
{% endif %}
{% endfor %}

{% if infra_publicresources_digitalocean_firewalls is defined %}
{% for firewall in infra_publicresources_digitalocean_firewalls %}
{% if firewall.id is defined %}

resource "digitalocean_firewall" "{{ firewall.id }}" {
  name = "{{ firewall.id }}"
  
  {% if firewall.tags is defined %}
  tags = [
    {% for tag in firewall.tags %}
    "{{ tag }}"{{ "," if not loop.last }}
    {% endfor %}
  ]
  {% endif %}

  {% if firewall.inbound is defined %}
  {% for inbound in firewall.inbound %}
  inbound_rule {
    protocol = "{{ inbound.protocol }}"
    {% if inbound.port_range is defined %}
    port_range = "{{ inbound.port_range }}"
    {% endif %}

    {% if inbound.ip_addresses is defined %}
    source_addresses = [
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
  outbound_rule {
    protocol = "{{ outbound.protocol }}"
    {% if outbound.port_range is defined %}
    port_range = "{{ outbound.port_range }}"
    {% endif %}

    {% if outbound.ip_addresses is defined %}
    destination_addresses = [
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
