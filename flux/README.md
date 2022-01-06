# Flux

Most stuff in my home runs on Kubernetes (k3s specifically) and I use Flux to manage the configuration of all the kubes in the netes.

Flux and the practice of GitOps means that I keep every bit of configuration in this code repo. 

And I mean _every bit_.

To the extent that I should be able to rebuild the entire cluster from this repo (sans data, of course). Madness, you say? Who knoes. But I know that I shouldn't ever forget what I did to my home infra because it's here, written down.

