# Installing the Kubernetes infrastructure and apps

```
flux bootstrap github \ 
  --context=homeautomation \ 
  --owner=whalecoiner \
  --repository=k8s-at-home \
  --branch=main \
  --personal=true \
  --private=false \
  --path=flux/clusters/homeautomation \
  --reconcile=true
```