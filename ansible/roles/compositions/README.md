# Compositions

Orchestrate Docker Compose applications. Creates a shared Docker bridge network, provisions ZFS datasets for each composition, and dynamically includes the appropriate `composition-*` roles to a host via the `compositions` list variable.

## Example

```yaml
compositions:
  - music-assistant
  - freshrss
```
