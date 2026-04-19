# My Home Infra

Hello, good evening, etc. Welcome to the repo where I keep all my home infrastructure.

Yes indeed, *everything* I have on my home infra is controlled by this repo.

Most of it is Ansible, as it's great for configuring individual machines, but you'll find some Terraform, Kubernetes, and ESPhome configs in there as well.

Credentials are stored in this repo, encrypted.

I access everything though Tailscale, which is an annoying dependency. But I keep the integration as light as possible so that I can detach my infra from them when they inevitably turn evil.

![host-homebrain - Core Playbook](https://healthchecks.io/b/2/fa63155e-40e1-4f59-9279-8d975b73378f.svg)
![host-malcolm - Core Playbook](https://healthchecks.io/b/2/7cfa55ac-9a06-4f4a-b726-0c6cc569dae8.svg)
![host-sites - Core Playbook](https://healthchecks.io/b/2/7a8d9d9b-f5fb-4299-bc98-c206ba518c75.svg)
![host-storage - Core Playbook](https://healthchecks.io/b/2/3ac8d7ea-5f57-4572-8a06-64d5f15c9877.svg)
![host-pikvm - Core Playbook](https://healthchecks.io/b/2/b974756a-0733-4c2d-8f64-b4466c3cd0ca.svg)

## Installation

Not sure why you'd want to install this, as it's my home infra. But hey, knock yourself out.

## Setting up the control plane

```bash
# Clone repo
git clone git@github.com:awfulwoman/infra.git

# Install supporting Python packages
cd infra
python -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt

# To activate auto loading of resources when entering the directory
apt install direnv -y
direnv allow .
```

## LLM Disclaimer

Yeah, I'm currently using [Claude Code](https://claude.ai/code) to write portions of this infrastructure repo. I'm not entirely comfortable doing so, as the push for "AI" is a wanking contest between Silicon Valley pricks and their techbro worshippers. It rides rampant over creativity, art, and all things that require a soul.

But I _do_ see uses for LLMs in the non-creative space of everyday coding. No, not the original stuff that happens at the low level of the development ecosystem. But at the high end, where code is just a tool to achieve other goals... yes, I think it's useful.

Claude seems better (this is relative) than the other AI shite companies. The session limitations, even on the paid plans, have the (unintended) effect of dampening the addiction cycle that other AIs seem intent on promoting. Obviously they're still bastards - they're a capitalist megacorp. They don't have my interests at heart - no megacorp does under late-stage capitalism possibly can.

But there's the rub, ain't it? I can use a tool and still understand how damn dangerous it is. If I use a chainsaw I can acknowledge that it's useful, while _at the same time_ understanding that it can severely fuck things up if handed out at a kiddies birthday party.

What was my point? Oh, I don't know now. But nevertheless, Claude has proved useful for writing informative and detailed commit messages, and has forced me to start documenting everything here.

I'm using Claude as progressive enhancement of skills. I will not use Claude unless I understand the underlying codebase and technology first. Claude is useful for doing arduous tasks that I would not otherwise find the executive function to engage in. I assume at all times that CLaude could disappear in a heartbeat, and that I could lose it as a tool (for that is all an LLM is: a useful tool).

And finally, this will be an unpopular view: Claude is an accessibility aid. I could not otherwise do the stuff I've done with it due to ADHD and dyslexia. Go look at the commit log before 20th December 2025 if you don't believe me.

Anyway, laters.
