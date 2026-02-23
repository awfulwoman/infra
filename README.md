# My Home Infra

Hello, good evening, etc. Welcome to the repo where I keep all my home infrastructure.

Yes indeed, *everything* I have on my home infra is controlled by this repo.

Most of it is Ansible, as it's great for configuring individual machines, but you'll find some Terraform, Kubernetes, and ESPhome configs in there as well.

Credentials are stored in this repo, encrypted.

I access everything though Tailscale, which is an annoying dependency. But I keep the integration as light as possible so that I can detach my infra from them when they inevitably turn evil.

## Installation

Not sure why you'd want to install this, as it's my home infra. But hey, knock yourself out.

## Getting a host machine up and running

```bash
# Clone repo
git clone git@github.com:awfulwoman/infra.git /opt/repos/infra

# Install supporting packages
cd /opt/repos/infra
pip3 install -r requirements.txt

# To activate auto loading of resources when entering the directory
apt install direnv -y
direnv allow /opt/repos/infra
```

## LLM Disclaimer

Yeah, I'm currently using [Claude Code](https://claude.ai/code) to write portions of this infrastructure repo. I'm not entirely comfortable doing so, as the push for "AI" is a wanking contest between Silicon Valley pricks and their techbro worshippers. It rides rampant over creativity, art, and all things that require a soul.

But I _do_ see uses for LLMs in the non-creative space of everyday coding. No, not the original stuff that happens at the low level of the development ecosystem. But at the high end, where code is just a tool to achieve other goals... yes, I think it's useful.

Claude seems better than the other AI shite companies. They aren't treating it like heroin, and charge realistic rates for what you get. The session limitations, even on the paid plans, have the effect of dampening the addiction cycle that other AIs seem intent on promoting. Obviously they're still bastards - they're a capitalist megacorp. They don't have mu interests at heart.

But that's the rub isn't it? I can use a tool and still understand how damn dangerous it is. If I use a chainsaw I respec that it's useful, but acknowledge that it can severely fuck things up if given out at a toddlers birthday party.

What was my point? I don't know now. But nevertheless, Claude has proved useful for writing informative and detailed commit messages, and has forced me to start documenting everything here.

I'm using Claude as progressive enhancement of skills. I will not use Claude unless I understand the underlying codebase and technology first. Claude is useful for doing arduous tasks that I would not otherwise engage in. I assume at all times that CLaude could disappear in a heartbeat, and that I could lose it as a tool (for that is all an LLM is: a useful tool).

And finally, this will be an unpopular view: Claude is an accessibility aid. I could not otherwise do the stuff I've done with it due to ADHD and dyslexia. Go look at the commit log before 20th December 2026 if you don't believe me.

Anyway, laters.
