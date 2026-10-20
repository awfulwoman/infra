# Immich

A self-hosted photo and video management solution.

* [Homepage](https://immich.app)
* [Github](https://github.com/immich-app/immich)

## OAuth login (Authentik)

OAuth settings come from `templates/immich-config.json.j2` (mounted via `IMMICH_CONFIG_FILE`). This makes the whole Admin > Settings UI read-only; only `oauth` is set, the rest stays at Immich defaults. Change settings in the template, not the UI.

- `autoRegister` is off: a user with no matching Immich account fails to log in instead of getting an empty duplicate. Create the Immich user first.
- First OAuth login matches the Immich account by **email**, so the Immich email must equal the Authentik user's email. After that the stable Authentik user ID is stored. Alternatively, link from Account Settings while logged in with a password.
- Password login stays on as a fallback if Authentik is down.
