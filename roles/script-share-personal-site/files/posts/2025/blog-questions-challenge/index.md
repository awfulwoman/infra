---
title: Blog Questions Challenge, aka chain letters for nerds
date: "2025-02-06T20:12:39+0100"
tags:
  - selfhosting
  - hugo
  - blogging
  - markdown
---

There's a wee trend going around called "Blog Questions Challenge". You answer a bunch of pre-defined questions on your blog, and then tag some more people to do the same.

This is near enough to the concept of a chain letter to make me flip the proverbial bird and storm out. However, after a refreshing cup of tea, and a therapeutic smashing of small tchotchkes, I came to see the value in it. Therefore thank you to Remy for [tagging me on Mastodon](https://indieweb.social/@rem@front-end.social/113956597719639710) and in his [own post on this very theme](https://remysharp.com/2025/02/06/blog-questions-challenge).

## Why did you start blogging in the first place?

I'm not sure if what I do can be called "blogging", as that implies some kind of commitment and regular cadence. But random writing on the WWW began for me back in the 90s on Geocities. As a young queer trapped in Northern England this new "web" thing allowed me to express the new and quite exciting feelings that I had, and to experiment with showing that off to the world. Or at least that part of the world that did not contain my family. (If you're guessing then yes, it certainly was in the [West Hollywood district](https://www.geocities.ws/server2/homestead/westhollywood/) of Geocities).

## What platform are you using to manage your blog and why did you choose it? Have you blogged on other platforms before?

I'm using [Hugo](https://gohugo.io) to write this blog. It's a static site generator, a way of generating a full site from a bunch of [Markdown](https://www.markdownguide.org) files. Thankfully these SSGs took over from the database and code behemoths that we used to use.

I host it all myself, because my latest incarnation is as a self-hosting nerd. I write the markdown, commit it to a [Gitea instance](https://about.gitea.com) that runs on my private home server, itself located on my own little network. This does some checks, strips privacy-destroying location info from any images, builds the site to HTML, and then rsyncs it up to a Digital Ocean droplet out on the wild internet which hosts the actual site. You might see it as overly complex, but it's what's happening behind the scenes on every other provider - and I learnt a lot by building it myself.

I've followed a lot of [Indieweb](https://indieweb.org) concepts in building this site. That means using content types for everything - [notes](https://indieweb.org/note), [posts](https://indieweb.org/post), [bookmarks](https://indieweb.org/bookmark), [quotes](https://indieweb.org/quotation), [likes](https://indieweb.org/like), etc. It also means incorporating microformats into the HTML to allow other Indieweb sites to interact with it (somewhat more) easily.

## How do you write your posts? For example, in a local editing tool, or in a panel/dashboard that’s part of your blog?

I write everything in VScode on my laptop, as it's just a Markdown file that I'm editing. I've got some shonky bash scripts that create shortform items such as notes and bookmarks for me.

I like sitting on the sofa and writing on the laptop. It's a moment of focussed peace that I rarely attain (which of course begs the question of why I'm not doing this more often...).

Having said that, I'd like to get [IndieKit](https://getindiekit.com) up and running so that I can post things on the go. I really like the idea of writing notes on the go and posting them there and then. It's what I use my Mastodon account for more than anything - venting the thoughts out of my head into the vacuum of the void (aka your feed). But for longer form words it's good to have a nice comfy spot, with a cup of tea to hand, to write out my latest brain thoughts.

## When do you feel most inspired to write?

Sadly, when I'm angry. I cannot abide stupidity (which might look to the outside observer like anyone who doesn't think like I do (perish the thought)) and when I come across it I'm compelled to rant about it. This does tend to lend anything I write a certain... _ascerbic_ nature. But apparently people find that entertaining.

## Do you publish immediately after writing, or do you let it simmer a bit as a draft?

I publish these words as soon as I've written them. This is the nature of being Charlie - everything is immediate or it simply doesn't exist. This is the curse of severe ADHD.

After words are written I will look at them obsessively for the next day, looking for errors of grammar, spelling and thought. These errors will be ruthlessly expunged as soon as they are discovered, all history of them erased. Except in the git repo that contains these words. Which you can't access because I don't publish it. Yah boo sucks.

## What’s your favourite post on your blog?

Undoudetly the one about [React](https://awfulwoman.com/posts/react/). It was pure vitriol and [free writing](https://en.wikipedia.org/wiki/Free_writing). It also came across a little like those timelines that you get in Pater F Hamilton books - which I imagine that he uses to bump the word count to even more excessive levels.

## Any future plans for your blog? Maybe a redesign, a move to another platform, or adding a new feature?

As Remy noted in his tag, this is about the zillionth domain and blog that I've maintained. However, despite going through several domain names, I have in fact kept the content that I wrote since ~2013, which isn't bad.

Unlike the cool kids that can maintain domain names over decades, I have been cursed with several life events that have forced me to change the domains that I used. All but one of those I still own, so I really should get around to putting up redirects from those old domains and URLs to here.

I have absolutely no doubt that I will change the platofmr that I used at some point. Change is the only constant in life. But I do know that anything I use will always have a simple text file at the heart of it.

# Next

What do I do now? [peers at previous blogs]

Oh, it looks like I have to tag others. Okay. Er, how about [Aegir](https://aegir.org), who posts lovely photo blogs, [Felipe](https://ftrc.blog), a friend who writes about his adventures in Berlin, and [Patrick](https://www.splintered.co.uk), who is a miserable cunt and who this act of tagging will annoy. 🖕
