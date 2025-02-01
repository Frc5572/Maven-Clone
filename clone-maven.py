import requests
import functools
import datetime
import os
from packaging.version import parse
import argparse
import itertools

YEAR = datetime.datetime.now().year
YEAR_1 = YEAR + 1
PRE_RELEASE = datetime.datetime.now().month > 9
LAST_YEAR = datetime.datetime.now().month < 2
VENDOR_DEP_MARKETPLACE_URL = (
    "https://frcmaven.wpi.edu/artifactory/vendordeps/vendordep-marketplace"
)
HASH_ARR = ["", "md5", "sha1", "sha256", "sha512"]


def loadFileFromUrl(url: str) -> list | dict:
    response = requests.get(url)
    if response.ok:
        file = response.json()
        return file
    return None


def compareVersions(item1: str, item2: str):
    verstion1 = item1.get("version")
    verstion2 = item2.get("version")
    if parse(verstion1) < parse(verstion2):
        return -1
    elif parse(verstion1) > parse(verstion2):
        return 1
    else:
        return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="Maven Cloner",
        description="Clones FRC Maven Repositories",
        epilog="Text at the bottom of help",
    )
    parser.add_argument(
        "dep_uuid",
        default="",
        type=str,
        help=f"UUID of the dependency to download. See {VENDOR_DEP_MARKETPLACE_URL}/{YEAR}.json for a list.",
    )
    parser.add_argument(
        "-d",
        "--directory",
        default="./maven",
        help="Directory to download the libraries to. Defaults to './maven'",
    )
    args = parser.parse_args()
    root_dir = args.directory.rstrip("/")
    years = [YEAR]
    if LAST_YEAR:
        years.append(YEAR - 1)
        years.append(f"{YEAR}beta")
    if PRE_RELEASE:
        years.append(f"{YEAR_1}beta")
    run_once = True
    for year in years:
        manifestURL = f"{VENDOR_DEP_MARKETPLACE_URL}/{year}.json"
        onlineDeps = loadFileFromUrl(manifestURL)
        if onlineDeps is None:
            continue
        vendor_versions = [x for x in onlineDeps if x.get("uuid", "") == args.dep_uuid]
        if len(vendor_versions) == 0:
            continue
        if run_once:
            print(f"========== {vendor_versions[0].get('name', '')} ==========")
            run_once = False
        vendor_versions.sort(key=functools.cmp_to_key(compareVersions), reverse=True)
        for vendor in vendor_versions:
            url = vendor.get("path", "")
            if not url.startswith("http"):
                url = f"{VENDOR_DEP_MARKETPLACE_URL}/{url}"
            vendor = loadFileFromUrl(url)
            if vendor is None:
                continue
            mavenURLs: list[str] = vendor.get("mavenUrls", [])
            if len(mavenURLs) == 0:
                continue
            mavenURL = mavenURLs[0].rstrip("/")
            javaDeps = vendor.get("javaDependencies", [])
            jniDeps = vendor.get("jniDependencies", [])
            for dep in javaDeps:
                version: str = dep.get("version", "")
                groupId: str = dep.get("groupId", "")
                artifactId: str = dep.get("artifactId", "")
                groupPath = groupId.replace(".", "/")
                meta = requests.get(
                    f"{mavenURL}/{groupPath}/{artifactId}/maven-metadata.xml"
                )
                print(f"Downloading {artifactId} ({version})")
                os.makedirs(
                    f"{root_dir}/{groupPath}/{artifactId}/{version}", exist_ok=True
                )
                for ext, hash in itertools.product(["pom", "jar"], HASH_ARR):
                    file_path = f"{groupPath}/{artifactId}/{version}/{artifactId}-{version}.{ext}"
                    if hash != "":
                        file_path = f"{file_path}.{hash}"
                    with open(f"{root_dir}/{file_path}", mode="wb") as f:
                        jar = requests.get(
                            f"{mavenURL}/{file_path}", allow_redirects=True
                        )
                        if jar.ok:
                            f.write(jar.content)
            for dep in jniDeps:
                version: str = dep.get("version", "")
                groupId: str = dep.get("groupId", "")
                artifactId: str = dep.get("artifactId", "")
                validPlatforms: str = dep.get("validPlatforms", [])
                groupPath = groupId.replace(".", "/")
                artifactDir = f"{root_dir}/{groupPath}/{artifactId}"
                meta = requests.get(
                    f"{mavenURL}/{groupPath}/{artifactId}/maven-metadata.xml"
                )
                print(f"Downloading {artifactId} ({version})")
                os.makedirs(
                    f"{root_dir}/{groupPath}/{artifactId}/{version}", exist_ok=True
                )
                for hash in HASH_ARR:
                    file_path = f"{groupPath}/{artifactId}/{version}/{artifactId}-{version}.pom"
                    if hash != "":
                        file_path = f"{file_path}.{hash}"
                    with open(f"{root_dir}/{file_path}", mode="wb") as f:
                        zip = requests.get(
                            f"{mavenURL}/{file_path}", allow_redirects=True
                        )
                        if zip.ok:
                            f.write(zip.content)
                for platform, hash in itertools.product(validPlatforms, HASH_ARR):
                    file_path = f"{groupPath}/{artifactId}/{version}/{artifactId}-{version}-{platform}.zip"
                    if hash != "":
                        file_path = f"{file_path}.{hash}"
                    with open(f"{root_dir}/{file_path}", mode="wb") as f:
                        zip = requests.get(
                            f"{mavenURL}/{file_path}", allow_redirects=True
                        )
                        if zip.ok:
                            f.write(zip.content)