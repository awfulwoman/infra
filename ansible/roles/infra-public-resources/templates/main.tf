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
    digitalocean_domain.{{ resource }}.urn{{ "," if not loop.last }}
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
  region                  = "{{ volume.region }}"
  name                    = "{{ volume.name }}"
  size                    = {{ volume.size }}
}
{% endif %}
{% endfor %}

# Ensure all Droplets exist
{% for droplet in infra_publicresources_droplets %}
{% if droplet.id is defined %}

resource "digitalocean_droplet" "{{ droplet.id }}" {
  image  = "{{ droplet.image }}"
  name   = "{{ droplet.name }}"
  region = "{{ droplet.region }}"
  size   = "{{ droplet.size }}"
  {% if droplet.volumes is defined -%}
  volume_ids = [
    {% for volume in droplet.volumes %}
    digitalocean_volume.{{ volume }}.id{{ "," if not loop.last }}
    {% endfor %}
  ]
  {% endif -%}
}
{% endif %}
{% endfor %}
