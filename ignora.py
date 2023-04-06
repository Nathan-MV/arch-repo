import os
import re
import requests
import subprocess
import hashlib


class Update:
    def __init__(self, url=None, path=None, filename=None):
        self.url = url
        self.path = path
        self.filename = filename

    def clone(self):
        if not os.path.exists(self.path):
            subprocess.check_call(["git", "clone", self.url])

    def get_filepath(self):
        for root, dirs, files in os.walk(self.path):
            for f in files:
                if f == self.filename:
                    return os.path.join(root, f)
        raise FileNotFoundError(f"{self.filename} not found in {self.path}")

    def get_file_contents(self):
        with open(self.get_filepath()) as file:
            return file.read()

    def has_gitlab_source(self):
        contents = self.get_file_contents().lower()
        return "gitlab.com" in contents

    def get_gitlab_type(self):
        if self.has_gitlab_source():
            contents = self.get_file_contents()
            if self.has_pkgbuild():
                return re.findall(r"url=(https://gitlab.com/[^\n]*)", contents)[0]

    def get_gitlab_user(self):
        user_and_project = self.get_gitlab_type().split("/")[-2:]
        return user_and_project[0]

    def get_gitlab_project(self):
        user_and_project = self.get_gitlab_type().split("/")[-2:]
        return user_and_project[1]

    def get_gitlab_release_json(self):
        if self.has_gitlab_source():
            response = requests.get(
                f"https://gitlab.com/api/v4/projects/{self.get_gitlab_user()}%2F{self.get_gitlab_project()}/releases"
            )
            response.raise_for_status()
            return response.json()

    def get_latest_gitlab_release_tag(self):
        if self.has_gitlab_source():
            TAG = self.get_gitlab_release_json()[0]["tag_name"]
            if TAG != re.findall(r"pkgver=(.*)", self.get_file_contents())[0]:
                return TAG

    def get_pkgurl_etag(self):
        response = self.get_gitlab_release()
        response.raise_for_status()
        return response.headers["ETag"]

    def get_local_etag(self):
        file_name = (
            f"{self.get_gitlab_project()}-{self.get_latest_gitlab_release_tag()}.tar.gz"
        )
        target_path = os.path.join(os.path.dirname(self.get_filepath()), file_name)
        if os.path.exists(target_path):
            with open(target_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()

    # The purpose of comparing the URL ETag with the local ETag in this code is to check if the local copy of the file matches the latest version available on the server.
    def compare_pkgurl_and_local_etag(self):
        local_etag = self.get_local_etag()
        if local_etag == self.get_pkgurl_etag():
            return local_etag

    def get_gitlab_release(self):
        url = f"https://gitlab.com/{self.get_gitlab_user()}/{self.get_gitlab_project()}/-/archive/{self.get_latest_gitlab_release_tag()}/{self.get_gitlab_project()}-{self.get_latest_gitlab_release_tag()}.tar.gz"
        response = requests.get(url)
        response.raise_for_status()
        return response

    def download_pkg(self):
        if not self.get_local_etag():
            file_name = f"{self.get_gitlab_project()}-{self.get_latest_gitlab_release_tag()}.tar.gz"
            target_path = os.path.join(os.path.dirname(self.get_filepath()), file_name)
            with open(target_path, "wb") as f:
                f.write(self.get_gitlab_release().content)
            print(f"{file_name} downloaded successfully")
        else:
            print("PKG already exists")

    def update_pkgbuild_file(self):
        filepath = self.get_filepath()
        with open(filepath, "r") as f:
            contents = f.read()
        # Arch Linux - Pacman
        if self.has_pkgbuild():
            contents = re.sub(
                r"pkgver=(.*)",
                f"pkgver={self.get_latest_gitlab_release_tag()}",
                contents,
            )
            contents = re.sub(
                r"sha256sums=\('(.*)'\)",
                f"sha256sums=('{self.compare_pkgurl_and_local_etag()}')",
                contents,
            )

        target_path = os.path.join(os.path.dirname(self.get_filepath()), self.filename)
        with open(target_path, "w") as f:
            f.write(contents)

        print(f"Updated {filepath} file")

    def update_package(self):
        if self.get_latest_gitlab_release_tag():
            self.download_pkg()
            self.update_pkgbuild_file()
        else:
            print(
                "No updates found on GitLab or the PKGBUILD file is already up-to-date."
            )

    def has_pkgbuild(self):
        return self.filename == "PKGBUILD"


if __name__ == "__ignora__":
    update = Update(
        "https://github.com/Nathan-MV/arch-repo.git", "arch-repo", "PKGBUILD"
    )
    update.clone()
    update.update_package()
