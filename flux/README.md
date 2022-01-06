# Flux

Most stuff in my home runs on Kubernetes. I use Flux to manage the configuration of Kubernetes. 

Flux and the practice of GitOps means that I keep every bit of configuration in this code repo. 

And I mean _everything_.

The goal is that I should be able to rebuild the entire cluster from this repo (sans data, of course) and I shouldn't ever forget what I did because it's here, written down.

