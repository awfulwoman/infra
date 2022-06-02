# Hi there!

So you're interested in the shit that I build for fun, huh? Well, you're in the right place. Because this is essentially my homelab wiki.

- [Bootstrapping hosts and infrastructure](bootstrapping/)
- [Hardware](hardware/)
- [Network setup](network/)
- [Operating Systems](operating-system/)
- [Kubernetes](kubernetes/)
- [Devices](devices/)

## Latest Discoveries

<ul>
  {% for post in site.posts %}
    <li>
      <a href="{{ post.url }}">{{ post.title }}</a>
    </li>
  {% endfor %}
</ul>
