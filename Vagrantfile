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
  $script_nvm = <<-SCRIPT_NVM
  echo "#########################################"
  echo "# NVM SETUP"
  echo "#########################################"
  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
  export NVM_DIR="$HOME/.nvm"
  [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
  nvm install --lts
  nvm alias default lts/*
  SCRIPT_NVM

  $script_claude = <<-SCRIPT_CLAUDE
  echo "#########################################"
  echo "# CLAUDE SETUP"
  echo "#########################################"
  curl -fsSL https://claude.ai/install.sh | bash
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> $HOME/.bashrc
  SCRIPT_CLAUDE

  $script_user = <<-SCRIPT_USER
  echo "#########################################"
  echo "# CUSTOMISE USER"
  echo "#########################################"
  echo "cd #{workspace_path}" >> $HOME/.bashrc
  SCRIPT_USER
  
  # The weird indentation is, sadly, important here
  # https://stackoverflow.com/a/75320225
  $script_ssh_agent = <<-'SCRIPT_SSHAGENT'
    cat >> $HOME/.bashrc << 'EOF'
if [ ! -f ~/.ssh_reminder_shown ]; then
  eval "$(ssh-agent -s)" > /dev/null
  echo "==> SSH agent started. Add your key:"
  ssh-add ~/.ssh/id_ed25519 && touch ~/.ssh_reminder_shown
fi
EOF
  SCRIPT_SSHAGENT

  # Run defined scripts
  config.vm.provision "shell", inline: $script_nvm, privileged: false
  config.vm.provision "shell", inline: $script_claude, privileged: false
  config.vm.provision "shell", inline: $script_user, privileged: false
  config.vm.provision "shell", inline: $script_ssh_agent, privileged: false

  # Copy over credentials to working VM
  config.vm.provision "file", source: "~/.gitconfig", destination: ".gitconfig"
  config.vm.provision "file", source: "~/.ssh/id_ed25519", destination: ".ssh/id_ed25519"
  config.vm.provision "file", source: "~/.ssh/id_ed25519.pub", destination: ".ssh/id_ed25519.pub"
  config.vm.provision "file", source: "~/.claude.json", destination: ".claude.json"
  config.vm.provision "file", source: "~/.claude/CLAUDE.md", destination: ".claude/CLAUDE.md"
  config.vm.provision "file", source: "~/.claude/settings.json", destination: ".claude/settings.json"
  config.vm.provision "file", source: "/opt/ansible/.vaultpassword", destination: "/opt/ansible/.vaultpassword"

end
