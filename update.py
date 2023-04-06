import os
import re
import requests
import hashlib
import glob
from tqdm import tqdm
import git
from contextlib import closing

def download_file(url: str, filepath: str) -> None:
    with requests.Session() as session, closing(session.get(url, stream=True)) as response:
        response.raise_for_status()
        file_size = int(response.headers.get("content-length", 0))
        chunk_size = 4 * 1024 * 1024  # 4 MB chunks
        with open(filepath, "wb") as f, tqdm(total=file_size, unit="B", unit_scale=True, desc=filepath) as progress_bar:
            for chunk in response.iter_content(chunk_size=chunk_size):
                f.write(chunk)
                progress_bar.update(len(chunk))

for filepath in glob.glob(os.path.join("packages", "**", "PKGBUILD")):
    print(filepath)
    with open(filepath, "r") as f:
        contents = f.read()
    if url_match := re.search(r"url=(https://gitlab.com/[^\n]*)", contents):
        gitlab_url = url_match[1]
        parts = gitlab_url.split("/", 4)
        url = "/".join(parts[:-2])
        user, project = parts[-2:]
        os.chdir(os.path.dirname(filepath))
        repo = git.Repo(search_parent_directories=True)
        gitlab_url = f"{url}/{user}/{project}.git"
        tag = repo.git.ls_remote(gitlab_url, "refs/tags/*", sort="-v:refname", exit_code=True).split("\n")[0].split("refs/tags/")[1]
        print(f"New version found: {tag}")
        if tag != re.search(r"pkgver=(.*)", contents)[1]:
            url = f"{url}/{user}/{project}/-/archive/{tag}/{project}-{tag}.tar.gz"
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
            print("No updates found for the PKGBUILD's.")
        os.chdir("../../")
