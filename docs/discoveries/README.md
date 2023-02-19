# Discoveries

Discoveries that I've made.

![](https://media.giphy.com/media/SPZFhfUJjsJO0/giphy.gif)

<ul>
  {% for post in site.posts %}
    <li>
      <a href="{{ post.url }}">{{ post.title }}</a>
    </li>
  {% endfor %}
</ul>