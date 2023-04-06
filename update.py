import os
import re
import requests
import hashlib
import glob
from tqdm import tqdm

def download_file(url, filepath):
    session = requests.Session()
    with session.get(url, stream=True) as response:
        response.raise_for_status()
        file_size = int(response.headers.get("content-length", 0))
        chunk_size = 4 * 1024 * 1024  # 1 MB chunks
        with open(filepath, "wb") as f, tqdm(total=file_size, unit="B", unit_scale=True, desc=filepath) as progress_bar:
            downloaded = 0
            for chunk in response.iter_content(chunk_size=chunk_size):
                f.write(chunk)
                downloaded += len(chunk)
                progress_bar.update(len(chunk))

for filepath in glob.glob(os.path.join("packages", "**", "PKGBUILD")):
    print(filepath)
    with open(filepath, "r") as f:
        contents = f.read()
    if url_match := re.search(r"url=(https://gitlab.com/[^\n]*)", contents):
        gitlab_url = url_match[1]
        user, project = gitlab_url.split("/")[-2:]
        os.chdir(os.path.dirname(filepath))
        response = requests.get(f"https://gitlab.com/api/v4/projects/{user}%2F{project}/releases")
        response.raise_for_status()
        tag = response.json()[0]["tag_name"]
        print(f"New version detected: {tag}")
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
                download_file(url, f"{project}-{tag}.tar.gz")
                with open(f"{project}-{tag}.tar.gz", "rb") as f:
                    pkg_hash = hashlib.sha256(f.read()).hexdigest()
            with open("PKGBUILD", "w") as f:
                f.write(re.sub(r"pkgver=(.*)", f"pkgver={tag}", re.sub(r"sha256sums=\('(.*)'\)", f"sha256sums=('{pkg_hash}')", contents)))
                print(f"PKGBUILD updated to {tag} for {project}")
        else:
            print(f"No updates found on GitLab or the PKGBUILD file is already up-to-date for {project}.")
        os.chdir("../../")
