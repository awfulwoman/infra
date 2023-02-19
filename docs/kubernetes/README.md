# Kubernetes

After my cluster has been built with Ansible I can bootstrap it using the following command.

```
flux bootstrap github \
  --owner=whalecoiner \
  --repository=home \
  --branch=main \
  --personal=true \
  --private=false \
  --path=flux/clusters/home-automation \
  --reconcile=true
```

Flux will pull down this repo and deploy everything defined in `flux/clusters/homeautomation` to the home cluster. It will then monitor the repo for changes and if there's any flux config changes, it will deply those changes.
