#cloud-config
users:
    - name: ${name}
      sudo: ['ALL=(ALL) NOPASSWD:ALL']
      groups: ['wheel']
      ssh_authorized_keys:
        - ${authorized_key}
