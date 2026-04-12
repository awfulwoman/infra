# Home Assistant Configuration Files

For better or worse, Home assistant is normally configured through the UI. But there times when you don't want to do this, such as when you need to include secrets from your IaC repo, if the configuration is not yet possible in the UI, or - most likely - templates need to be built to handle complex situations.

The following files are (hopefully) not updated automatically by Home Assistant. ("Hopefully" as HA has a very weird legacy use of YAML as state storage for things like Automations and Scripts, and at times it can be hard to fathom what is editable and what isn't...)

* <configuration.yaml> - the main HA configuration.
* <template.yaml> - complex templates that can't live in the UI.
* <input_select.yaml> - my first ever "complex" automation, if I recall. Retained here for nostalgia more than anything.
* <secrets.yaml> - nothing here yet.
