import requests
import json
from pathlib import Path
# from xml.dom import minidom
import xmltodict
import datetime
import os
import itertools
import re
# from packaging.version import parse
import argparse

YEAR = datetime.datetime.now().year
YEAR_1 = YEAR + 1
YEAR_REGEX = rf"^v?({YEAR}|{YEAR_1}|{str(YEAR)[2:]}|{str(YEAR_1)[2:]})\."

PRE_RELEASE = datetime.datetime.now().month > 9 or datetime.datetime.now().month < 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
                    prog='Maven Cloner',
                    description='Clones FRC Maven Repositories',
                    epilog='Text at the bottom of help')
    parser.add_argument('directory', default="./maven",help="Directory to download the libraries to. Defaults to './maven'")
    parser.add_argument('-c', '--cache', action='store_true', dest="cache", help="If set, the tool will not download files if the repo was last updated within the last X hours. X is set by --cache-timeout, defaults to 12 hours")
    parser.add_argument('--cache-timeout', dest="cache_timeout", type=int, default=12, help="Cache timeout. If --cache is set, repos will not download if they haven't been updated within the last X hours. Defaults to 12 hours")
    # parser.add_argument('--pre-release', action='store_true', dest="pre_release", help="Whether to download pre-release files")

    args = parser.parse_args()
    root_dir = args.directory.rstrip("/")
    _dir = Path.cwd().joinpath("vendordeps")
    CACHE_TIME = datetime.datetime.now() - datetime.timedelta(hours=args.cache_timeout)
    for file in _dir.glob("*.json"):
        with file.open(mode="r", encoding="utf-8") as f:
            vendor: dict = json.load(f)
            mavenURLs: list[str] = vendor.get("mavenUrls", [])
            if len(mavenURLs) == 0:
                continue
            print(f"========== {vendor.get('name', '')} ==========")
            mavenURL = mavenURLs[0].rstrip("/")
            javaDeps = vendor.get("javaDependencies", [])
            jniDeps = vendor.get("jniDependencies", [])
            for dep in javaDeps:
                groupId: str = dep.get("groupId","")
                artifactId: str = dep.get("artifactId","")
                groupPath = groupId.replace(".","/")
                artifactDir = f"{root_dir}/{groupPath}/{artifactId}"
                meta = requests.get(f"{mavenURL}/{groupPath}/{artifactId}/maven-metadata.xml")
                metaDict = xmltodict.parse(meta.text.lstrip())
                # print(meta.text)
                lastUpdated = metaDict.get("metadata",{}).get("versioning",{}).get("lastUpdated","")
                if args.cache and os.path.exists(artifactDir) and lastUpdated != "": 
                    updated = datetime.datetime.strptime(lastUpdated, '%Y%m%d%H%M%S')
                    if updated < CACHE_TIME:
                        continue
                try:
                    versionsRaw = metaDict.get("metadata",{}).get("versioning",{}).get("versions").get("version")
                    if isinstance(versionsRaw, str):
                        versionsRaw = [versionsRaw]
                    versions = [x for x in versionsRaw if re.match(YEAR_REGEX, x)]
                except Exception:
                    versions = []
                for version, ext in itertools.product(versions, ['pom','jar']):
                    dir = f"{artifactDir}/{version}"
                    os.makedirs(dir, exist_ok=True)
                    print(f"Downloading {artifactId}-{version}")
                    with open(f"{dir}/{artifactId}-{version}.{ext}", mode="wb") as f:
                        jar = requests.get(f"{mavenURL}/{groupPath}/{artifactId}/{version}/{artifactId}-{version}.{ext}", allow_redirects=True)
                        if jar.ok:
                            f.write(jar.content)
            for dep in jniDeps:
                groupId: str = dep.get("groupId","")
                artifactId: str = dep.get("artifactId","")
                validPlatforms: str = dep.get("validPlatforms",[])
                groupPath = groupId.replace(".","/")
                artifactDir = f"{root_dir}/{groupPath}/{artifactId}"
                meta = requests.get(f"{mavenURL}/{groupPath}/{artifactId}/maven-metadata.xml")
                metaDict = xmltodict.parse(meta.text.lstrip())
                lastUpdated = metaDict.get("metadata",{}).get("versioning",{}).get("lastUpdated","")
                if args.cache and os.path.exists(artifactDir) and lastUpdated != "": 
                    updated = datetime.datetime.strptime(lastUpdated, '%Y%m%d%H%M%S')
                    if updated < CACHE_TIME:
                        continue
                try:
                    versionsRaw = metaDict.get("metadata",{}).get("versioning",{}).get("versions").get("version")
                    if isinstance(versionsRaw, str):
                        versionsRaw = [versionsRaw]
                    versions = [x for x in versionsRaw if re.match(YEAR_REGEX, x)]
                except Exception:
                    versions = []
                for version in versions:
                    dir = f"{artifactDir}/{version}"
                    os.makedirs(dir, exist_ok=True)                            
                    print(f"Downloading {artifactId}-{version}")
                    with open(f"{dir}/{artifactId}-{version}.pom", mode="wb") as f:
                        zip = requests.get(f"{mavenURL}/{groupPath}/{artifactId}/{version}/{artifactId}-{version}.pom", allow_redirects=True)
                        if zip.ok:
                            f.write(zip.content)
                    for platform in validPlatforms:
                        with open(f"{dir}/{artifactId}-{version}-{platform}.zip", mode="wb") as f:
                            zip = requests.get(f"{mavenURL}/{groupPath}/{artifactId}/{version}/{artifactId}-{version}-{platform}.zip", allow_redirects=True)
                            if zip.ok:
                                f.write(zip.content)