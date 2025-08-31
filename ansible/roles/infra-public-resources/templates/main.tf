{% for project in infra_domains_projects %}
{% if project.id is defined %}
# Ensure all DO projects exist

resource "digitalocean_project" "{{ project.id }}" {
  name        = "{{ project.name }}"
  description = "{{ project.description }}"
  purpose     = "Web Application"
  environment = "Production"
}
{% endif %}

{% if project.resources is defined %}
# Ensure each domain zone is in the appropriate project

resource "digitalocean_project_resources" "{{ project.id }}" {
  project = digitalocean_project.{{ project.id }}.id
  resources = [
    {% for resource in project.resources %}
    digitalocean_domain.{{ resource }}.urn{{ "," if not loop.last }}
    {% endfor %}
  ]
}

{% endif %}
{% endfor %}



{% if (infra_domains_domains is iterable) and (infra_domains_domains | length > 0) %}
# Ensure all domain zones are registered with Digital Ocean
{% for item in infra_domains_domains %}
{% if (item.domain is defined) and (item.id is defined) %}

resource "digitalocean_domain" "{{ item.id }}" {
   name = "{{ item.domain }}"
}
{% endif %}
{% endfor %}
{% endif %}



{% if (infra_domains_domains is iterable) and (infra_domains_domains | length > 0) %}
# Ensure all records for domains exist
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
