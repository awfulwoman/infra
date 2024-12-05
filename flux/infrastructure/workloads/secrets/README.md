# Sealed Secrets

See: <https://fluxcd.io/flux/guides/sealed-secrets/#encrypt-secrets>

The [public key](pub-sealed-secrets.pem) is intentionally stored here. It allows sealing of secrets that can be unselaed only by the private key living in the cluster.

## Generate plain secret

```bash
kubectl -n default create secret generic basic-auth \
--from-literal=user=admin \
--from-literal=password=change-me \
--dry-run=client \
-o yaml > basic-auth.yaml
```

## Generated sealed secret

```bash
kubeseal --format=yaml --cert=pub-sealed-secrets.pem \
< basic-auth.yaml > basic-auth-sealed.yaml
```

## Remove the unsealed secret

```bash
rm basic-auth.yaml
```
