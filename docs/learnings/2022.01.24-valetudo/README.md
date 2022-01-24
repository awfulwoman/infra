# Rooting a Dreame L10 Pro robot vacuumn cleaner and installing Valetudo

So, we needed a new robot vacuumn cleaner after Trevor (a constantly mispronouned [Tesvor X500](https://www.tesvor.com/de/tesvor-x500-saugroboter.html)) developed silicon brainrot and started freaking out whenever he saw shadows on the floor. 

![](https://img.buzzfeed.com/buzzfeed-static/static/2019-09/25/18/asset/550dab955e80/anigif_sub-buzz-1002-1569437884-7.gif)

His replacement - Derek (a deliberately misnamed [Dreame L10 Pro](https://www.amazon.de/-/en/gp/product/B08ZS6MZ4R/ref=ppx_yo_dt_b_search_asin_title?ie=UTF8&th=1)) - is much much more advanced than poor Trevor. However, it still suffers from the fatal disease of all robot vacuumn cleaners: cloud connectivity.

I don't know about you fine folk, but I don't want something that travels freely around my home and that has cameras on board having unmonitored access to the internet.

In fact a hacker gave a presentation at Defcon 29 and found that one of the developers on the Dreame robots had installed a backdoor that allowed access to any Dreame machine.

<img alt="" src="https://user-images.githubusercontent.com/74922321/150783256-447a5d4c-d194-4c4c-a85e-dd4af4df9f4b.png">

[Watch the video where he shows all this dark magic](https://www.youtube.com/watch?v=EWqFxQpRbv8&t=1525s).

But what if you could sever that awful cloud connectivity link? I mean, Derek would be an amazing machine even if I had to trigger him manually. But thankfully I don't have to do that, as the same hacker developer who discovered the privacy breaches found a way to patch the onboard version of Linux (yes, my vaccumn cleaner runs Linux) and to stop it phoning out to the internet. And in fact he's enabled the machine to work _completely locally_, allowing it to be controlled via a UI, a Swagger interface, or MQTT, all from you local network.

Now THAT'S what I wanted.

So I purchased a [CP2104-based USB-to-UART device](https://www.amazon.de/gp/product/B01CYBHM26/ref=ppx_yo_dt_b_asin_image_o07_s00?ie=UTF8&psc=1) that allowed me to connect cables from my laptop to the debug port on Derek and _fuck with his mind_.

Or, to put it another way, to view the boot process over a serial port, log in via the easily guessable root password, and install things on there that make it stick to my LAN.

View the full guide on [Valetudo.cloud](https://valetudo.cloud) and try it out yourself if you have a compatible robot vacuumn cleaner! 

