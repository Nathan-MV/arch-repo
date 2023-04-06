import os
import re
import requests
import shutil
import subprocess
import hashlib
import glob
import concurrent.futures

def download_file(url, filepath):
    with requests.get(url, stream=True) as response, open(filepath, "wb") as f:
        shutil.copyfileobj(response.raw, f)

updated_pkgs = set()
for filepath in glob.glob("packages/**/PKGBUILD", recursive=True):
    with open(filepath, "r") as f:
        contents = f.read()
    if url_match := re.search(r"url=(https://gitlab.com/[^\n]*)", contents):
        gitlab_url = url_match[1]
        user, project = gitlab_url.split("/")[-2:]
        os.chdir(os.path.dirname(filepath))
        response = requests.get(f"https://gitlab.com/api/v4/projects/{user}%2F{project}/releases")
        response.raise_for_status()
        tag = response.json()[0]["tag_name"]
        if tag != re.search(r"pkgver=(.*)", contents)[1]:
            url = f"https://gitlab.com/{user}/{project}/-/archive/{tag}/{project}-{tag}.tar.gz"
            response = requests.head(url)
            response.raise_for_status()
            pkg_url = response.headers["ETag"]
            pkg_hash = ""
            if os.path.exists(f"{project}-{tag}.tar.gz"):
                with open(f"{project}-{tag}.tar.gz", "rb") as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                if file_hash == pkg_url:
                    pkg_hash = file_hash
            if not pkg_hash:
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(download_file, url, f"{project}-{tag}.tar.gz")
                    future.result()
                with open(f"{project}-{tag}.tar.gz", "rb") as f:
                    pkg_hash = hashlib.sha256(f.read()).hexdigest()
            with open("PKGBUILD", "w") as f:
                f.write(re.sub(r"pkgver=(.*)", f"pkgver={tag}", re.sub(r"sha256sums=\('(.*)'\)", f"sha256sums=('{pkg_hash}')", contents)))
            updated_pkgs.add(project)
        else:
            print(f"No updates found on GitLab or the PKGBUILD file is already up-to-date for {project}.")
        os.chdir("../../../")

if updated_pkgs:
    print(f"Updated PKGBUILD files for: {', '.join(updated_pkgs)}")
else:
    print("No updates found on GitLab or all PKGBUILD files are already up-to-date.")
