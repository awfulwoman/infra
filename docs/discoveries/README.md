# Discoveries

Discoveries that I've made.

![](https://media.giphy.com/media/SPZFhfUJjsJO0/giphy.gif)

<ul>
{% for discovery in site.discoveries %}
    <li><a href="{{ discovery.url }}">{{ discovery.title }}</a> - {{ discovery.date }}</li>
{% endfor %}
</ul>