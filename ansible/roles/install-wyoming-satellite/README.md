Ansible Wyoming Satellite Role
=========

 This is an ansible role for building a wyoming satellite based on this
 tutorial https://github.com/rhasspy/wyoming-satellite/blob/master/docs/tutorial_2mic.md

Requirements
------------

A built wyoming satellite with the two mic hat.

Role Variables
--------------
These are the variables. These can be overridden using group or host
vars or passed in from your playbook when using this role.
```yaml
mic_auto_gain: 4
mic_command: "arecord -D plughw:CARD=seeed2micvoicec,DEV=0 -r 16000 -c 1 -f S16_LE -t raw"
mic_noise_suppression: 2
mic_volume: 1
satellite_name: Wyoming Satellite
snd_command: "aplay -D plughw:CARD=seeed2micvoicec,DEV=0 -r 22050 -c 1 -f S16_LE -t raw"
user: "{{ ansible_user_id }}"
threshold: 0.9
wyoming_openwakeword_dir: "/home/{{ user }}/wyoming-openwakeword"
wyoming_satellite_dir: "/home/{{ user }}/wyoming-satellite"
wake_word: "hey jarvis"
```

Example Playbook
----------------

    - hosts: satellites
      roles:
         - { role: wyoming-satellite, mic_auto_gain: 5 }

License
-------

BSD

Author Information
------------------

Daniel Nolan https://danielnolan.com
