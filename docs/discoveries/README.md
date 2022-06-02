# Discoveries

Discoveries that I've made.

![](https://media.giphy.com/media/SPZFhfUJjsJO0/giphy.gif)

<ul>
{% for page in site.collections.discoveries %}
  <li><a href="{{ page.url }}">{{ page.title }}</a></li>
{% endfor %}
</ul>