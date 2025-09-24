#!/bin/bash

if [ ! -d "{{ script_share_personal_site_path }}/{{ script_share_personal_site_name }}/.git" ];
then
  echo "Cloning"
  git clone https://gitea.{{ domain_name }}/awfulwoman/personal-site {{ script_share_personal_site_path }}/{{ script_share_personal_site_name }}
else
  echo "Updating"
  cd {{ script_share_personal_site_path }}/{{ script_share_personal_site_name }}
  git checkout .
  git clean -f
  git pull
fi

echo "Clean up"
rm -rf {{ script_share_personal_site_path }}/{{ script_share_personal_site_name }}/public
rm -rf {{ script_share_personal_site_path }}/{{ script_share_personal_site_name }}/resources
rm -rf {{ script_share_personal_site_path }}/{{ script_share_personal_site_name }}/content
rm -rf {{ script_share_personal_site_path }}/{{ script_share_personal_site_name }}/.git

echo "Copy content"
mkdir {{ script_share_personal_site_path }}/{{ script_share_personal_site_name }}/content
rsync -a "{{ script_share_personal_site_path }}/dummycontent/" {{ script_share_personal_site_path }}/{{ script_share_personal_site_name }}/content

# ls -alh "{{ script_share_personal_site_path }}/dummycontent/*" {{ script_share_personal_site_path }}/{{ script_share_personal_site_name }}/content

cd {{ script_share_personal_site_path }}/{{ script_share_personal_site_name }}

# ls -alh .

git config --global init.defaultBranch main
git init .
git config user.email "github@{{ vault_olddomain_wc }}"
git config user.name "Charlie O'Hara"

echo "Gitting"
git add .
git commit -m "Auto Commit $(date +'%Y-%m-%dT%H:%M:%S%z')"
git remote add origin https://{{ vault_github_token_share_site }}@github.com/awfulwoman/personal-site
git push --set-upstream origin main --force
