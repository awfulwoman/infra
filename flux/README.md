# Flux CD

[Flux](https://fluxcd.io/flux/) is a GitOps tool for managing Kubernetes clusters. Everything running in the cluster is defined in this section of the repo.

## Structure

The Flux components are broken up into [apps](apps/), [clusters](clusters/). and [infrastructure](infrastructure/).

The primary cluster is called "workloads". I really need a better name than that, but it serves for now.

## Local Dependencies

The following local tools are needed to make use of Flux.

### Kubernetes Control

```bash
brew install kubectl
```

### Flux CD

```bash
brew install fluxcd/tap/flux
```

Then export completions to your shell.

```bash
. <(flux completion zsh)
```

### Kubernetes Secrets

[Kubeseal](https://github.com/bitnami-labs/sealed-secrets) allows secrets to be stored in a public git repo.

```bash
brew install kubeseal
```

## Bootstrapping

Generate a Github token that has access to the repo, and export it to a local env var.

```bash
export GITHUB_TOKEN=<gh-token>
```

Then bootstrap Flux into the cluster.

```bash
flux bootstrap github \  
  --token-auth \
  --owner=awfulwoman \
  --repository=infra \
  --branch=main \
  --path=flux/clusters/workloads \
  --personal
```

Flux _should_ then generate the cluster from there.
