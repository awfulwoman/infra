# Ensure all DO projects exist
{% for item in infra_domains_projects %}

resource "digitalocean_project" "{{ item.name | lower }}" {
  name        = "{{ item.name }}"
  description = "{{ item.description }}"
  purpose     = "Web Application"
  environment = "Production"
}
{% endfor %}

# Ensure all domain zones are registered with Digital Ocean
{% for item in infra_domains_domains %}

resource "digitalocean_domain" "{{ item.domain }}" {
   name = "{{ item.domain }}"
}
{% endfor %}


# Ensure each domain zone is in the appropriate project
# resource "digitalocean_project_resources" "infra_domains" {
#  project = digitalocean_project.xxxx.id
#  resources = [
#    digitalocean_domain.rumblestrut_org.urn
#  ]
# }

# Ensure all records for domains exist
{% for item in infra_domains_domains %}
{% for record in item.records %}

resource "digitalocean_record" "root" {
  domain = "{{ item.domain }}"
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
{% endfor %}
{% endfor %}


# Ensure all Droplets exist
# resource "digitalocean_droplet" "host_public" {
#   image  = "ubuntu-22-10-x64"
#   name   = "host-public"
#   region = "fra1"
#   size   = "s-1vcpu-1gb"
# }
