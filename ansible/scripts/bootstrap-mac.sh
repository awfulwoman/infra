#!/bin/bash

# Install Homebrew
which brew
if [[ $? != 0 ]] ; then
  # Install Homebrew if not installed
  NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# Make sure Homebrew envvars are present
if ! grep -Fxq "HOMEBREW_PREFIX=" $HOME/.zprofile ; then
  echo "Adding homebrew to user path."
  (echo; echo 'eval "$(/usr/local/bin/brew shellenv)"') >> /Users/charlie/.zprofile
  eval "$(/usr/local/bin/brew shellenv)"
fi

# Install latest python3
which python3
if [[ $? != 0 ]] ; then
  brew install python@3.11
fi


# Install Ansible)
which ansible
if [[ $? != 0 ]] ; then
  brew install ansible
fi





