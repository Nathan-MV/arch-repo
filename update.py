import os
import re
import requests
import hashlib
import glob
from tqdm import tqdm
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

https = "https://"
for filepath in glob.glob(os.path.join("packages", "**", "PKGBUILD")):
    print(filepath)
    with open(filepath, "r") as f:
        contents = f.read()
    if source_match := re.search(r'source=\("(https?://(?:www\.)?(github|gitlab).com/[^\n]*")\)', contents):
        full_source = source_match[1].split("/")
        source = "/".join(full_source[2:3])

        print(full_source)
        print(source)
    else:
        print("source didnt match")
        break

    if re.search(r"(gitlab|github).com", source):
        author = full_source[3]
        print(author)
    else:
        print("author didnt match")
        break

    if pkg_name_match := re.search(r"(pkgname|pkgbase)=([^\n]*)", contents):
        pkg_name = pkg_name_match[2]
        print(pkg_name + "\n")
    else:
        print("pkgname didnt match")
        break

    if re.search(r"gitlab.com", source):
        response = requests.get(f"{https}{source}/api/v4/projects/{author}%2F{pkg_name}/releases")
    elif re.search(r"github.com", source):
        response = requests.get(f"{https}api.{source}/repos/{author}/{pkg_name}/releases")
    else:
        print("no api response")
        break

    response.raise_for_status()
    tag = response.json()[0]["tag_name"]
    if tag != re.search(r"pkgver=(.*)", contents)[1]:
        os.chdir(os.path.dirname(filepath))
        if re.search(r"gitlab.com", source):
            url = f"{https}{source}/{author}/{pkg_name}/-/archive/{tag}/{pkg_name}-{tag}.tar.gz"
        elif re.search(r"github.com", source):
            url = f"{https}{source}/{author}/{pkg_name}/archive/refs/tags/{tag}.tar.gz"
        else:
            print("no tar.gz found")
            break
        if not os.path.exists(f"{pkg_name}-{tag}.tar.gz"):
            download_file(url, f"{pkg_name}-{tag}.tar.gz")
        with open(f"{pkg_name}-{tag}.tar.gz", "rb") as f:
            pkg_hash = hashlib.sha256(f.read()).hexdigest()
        with open("PKGBUILD", "w") as f:
            f.write(re.sub(r"pkgver=(.*)", f"pkgver={tag}", re.sub(r"sha256sums=\('(.*)'\)", f"sha256sums=('{pkg_hash}')", contents)))
            print(f"PKGBUILD updated to {tag} for {pkg_name}")
    else:
        print("No updates found for the PKGBUILD's.")
        continue
    os.chdir("../../")
