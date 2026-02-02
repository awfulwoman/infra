# This Vagrantfile is used to wrap a VM around instances of Claude Code.
# This enables Claude to be run with much more relaxed permissions,
# without worrying about it going mental and trashing your laptop or leaking
# personal info.

# Define variables
vm_name = File.basename(Dir.getwd)
workspace_path = "/workspace-#{vm_name}"

# Configure VM
Vagrant.configure("2") do |config|
  config.vm.box = "bento/ubuntu-24.04"
  config.vm.box_version = "202510.26.0"

  config.vm.synced_folder ".", workspace_path, type: "virtualbox"

  config.vm.provider "virtualbox" do |vb|
    vb.memory = "4096"
    vb.cpus = 2
    vb.gui = false
    vb.name = vm_name
    vb.customize ["modifyvm", :id, "--audio", "none"]
    vb.customize ["modifyvm", :id, "--usb", "off"]
  end

  # Provision system as root
  config.vm.provision "shell", inline: <<-SHELL
    export DEBIAN_FRONTEND=noninteractive

    echo "#########################################"
    echo "# APT INSTALL"
    echo "#########################################"
    apt update
    apt install -y docker.io git unzip jq curl gh wget htop ansible

    echo "#########################################"
    echo "# APT UPGRADE"
    echo "#########################################"
    apt upgrade -y

    echo "#########################################"
    echo "# USER SETUP"
    echo "#########################################"
    usermod -aG docker vagrant
    chown -R vagrant:vagrant #{workspace_path}

    echo "#########################################"
    echo "# ANSIBLE VAULT SETUP"
    echo "#########################################"
    mkdir -p /opt/ansible
    chown vagrant:vagrant /opt/ansible
  SHELL
end


# Provision system as vagrant user
Vagrant.configure("2") do |config|
  # Copy over credentials to working VM
  config.vm.provision "file", source: "~/.gitconfig", destination: ".gitconfig"
  config.vm.provision "file", source: "~/.ssh/id_ed25519", destination: ".ssh/id_ed25519"
  config.vm.provision "file", source: "~/.ssh/id_ed25519.pub", destination: ".ssh/id_ed25519.pub"
  config.vm.provision "file", source: "~/.claude.json", destination: ".claude.json"
  config.vm.provision "file", source: "~/.claude/CLAUDE.md", destination: ".claude/CLAUDE.md"
  config.vm.provision "file", source: "~/.claude/settings.json", destination: ".claude/settings.json"
  config.vm.provision "file", source: "/opt/ansible/.vaultpassword", destination: "/opt/ansible/.vaultpassword"

  # Install galaxy roles first
  config.vm.provision "shell", privileged: false, inline: <<-SHELL
    cd #{workspace_path}
    ansible-galaxy install -r ansible/meta/requirements.yaml --roles-path=/opt/ansible/galaxy/roles
  SHELL

  # Provision using Ansible
  config.vm.provision "shell", privileged: false, inline: <<-SHELL
    cd #{workspace_path}
    export ANSIBLE_ROLES_PATH=#{workspace_path}/ansible/roles:/opt/ansible/galaxy/roles
    ansible-playbook ansible/playbooks/virtual/vagrant-wrapper/core.yaml \
      -i ansible/inventory/hosts.yaml \
      --limit=vagrant-wrapper \
      -e "VAGRANT_WORKSPACE_PATH=#{workspace_path}"
  SHELL

end
