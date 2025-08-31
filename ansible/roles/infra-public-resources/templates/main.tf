# Ensure all DO projects exist
{% for item in infra_domains_projects %}
{% if item.id is defined %}

resource "digitalocean_project" "{{ item.id }}" {
  name        = "{{ item.name }}"
  description = "{{ item.description }}"
  purpose     = "Web Application"
  environment = "Production"
}
{% endif %}
{% endfor %}

# Ensure all domain zones are registered with Digital Ocean
{% if (infra_domains_domains is iterable) and (infra_domains_domains | length > 0) %}
{% for item in infra_domains_domains %}
{% if (item.domain is defined) and (item.id is defined) %}

resource "digitalocean_domain" "{{ item.id }}" {
   name = "{{ item.domain }}"
}
{% endif %}
{% endfor %}
{% endif %}

# Ensure each domain zone is in the appropriate project
# resource "digitalocean_project_resources" "infra_domains" {
#  project = digitalocean_project.xxxx.id
#  resources = [
#    digitalocean_domain.rumblestrut_org.urn
#  ]
# }

# Ensure all records for domains exist
{% if (infra_domains_domains is iterable) and (infra_domains_domains | length > 0) %}
{% for item in infra_domains_domains %}
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

# Ensure all Droplets exist
# resource "digitalocean_droplet" "host_public" {
#   image  = "ubuntu-22-10-x64"
#   name   = "host-public"
#   region = "fra1"
#   size   = "s-1vcpu-1gb"
# }
