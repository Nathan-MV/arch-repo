#!/bin/bash
set -e

# Clone the arch-repo git repository
git clone https://github.com/Nathan-MV/arch-repo.git

# Loop through all PKGBUILD files in arch-repo/packages
for pkgbuild in ./arch-repo/packages/**/PKGBUILD; do
  if grep -q "url=https://gitlab.com/" "$pkgbuild"; then
    echo "Found a PKGBUILD file with a GitLab source URL: $pkgbuild"
    dir=$(dirname "$pkgbuild")
    echo "dir run success"
    gitlab_url=$(grep "url=https://gitlab.com/" "$pkgbuild" | cut -d "'" -f 2)
    echo "gitlab_url run success"
    user_and_project=$(echo "$gitlab_url" | sed 's/.*gitlab.com\///')
    echo "user_and_project run success"
    user=$(echo "$user_and_project" | cut -d '/' -f 1)
    echo "user run success"
    project=$(echo "$user_and_project" | cut -d '/' -f 2)
    echo "project run success"
    cd "$dir"
    echo "cd dir run success"
    TAG=$(curl -s "https://gitlab.com/api/v4/projects/$user%2F$project/releases" | jq -r '.[0].tag_name')
    echo "TAG curl run success"
    if [ -n "$TAG" ] && [ "$TAG" != "$(grep pkgver PKGBUILD | awk -F= '{print $2}')" ]; then
      echo "Found a new release on GitLab: $TAG"
      PKGURL=$(curl -s "https://gitlab.com/api/v4/projects/$user%2F$project/releases/tags/$TAG" | jq -r '.assets[0].browser_download_url')
      echo "PKGURL run success"
      PKGHASH=$(curl -sL "$PKGURL" | sha256sum | awk '{print $1}')
      echo "PKGHASH run success"
      sed -i "s/pkgver=.*/pkgver=$TAG/" PKGBUILD
      echo "sed run success"
      sed -i "s/sha256sums=.*/sha256sums=('$PKGHASH')/" PKGBUILD
      echo "sed run success"
      makepkg --printsrcinfo > .SRCINFO
      echo "SRCINFO run success"
      git add PKGBUILD .SRCINFO
      echo "git add run success"
      git commit -m "Update $(basename $(pwd)) to version $TAG"
      echo "git commit run success"
      git push origin main
      echo "git push run success"
    else
      echo "No updates found on GitLab or the PKGBUILD file is already up-to-date."
    fi
    cd -
  fi
done

# Cleanup
rm -rf arch-repo

echo "Script execution completed."
