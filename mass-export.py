import os
import json
import requests
from pprint import pprint
from time import sleep
import argparse
from sys import argv
import pickle
import urllib3
from datetime import datetime
from pathlib import Path

example_text = """
    This tool helps you to export folders, dashboards and data sources from a grafana instance.
"""

parser = argparse.ArgumentParser(
    description="Grafana datasource importer",
    epilog=example_text,
    formatter_class=argparse.RawDescriptionHelpFormatter,
)

parser.add_argument("--location", dest="location", help="The location to save the dump, file or folder. (pointing to a folder will automaticly set a time and url specific name)")
parser.add_argument("--secret", dest="secret", help="grafana_session=# cookie or glsa_## Service account token")
parser.add_argument("--url", dest="url", help="The grafana URL: https://grafana.local")
parser.add_argument("--tag", dest="tag", help="The tag you want to include in your dump")
parser.add_argument(
    "--output", dest="out_format", default="pickle", help="Output format: json pickle(default)"
)

parser.set_defaults(verbose=False)
args = parser.parse_args()

if len(argv) < 7:
    parser.print_help()
    exit(0)

url = args.url

def login(session, secret):
    session.cookies.clear()
    session.headers.clear()
    session.headers.update({
        'User-Agent': 'Python grafana backup client',
        'Accept': 'application/json',
        "Content-Type": "application/json",
        "X-Disable-Provenance": "true"
    })

    # set auth headers
    if secret.startswith("glsa_") or secret.startswith("ey"):  
        session.headers.update({
            "Authorization": f"Bearer {secret}"
        })
    elif secret.startswith("grafana_session="):
        session.headers.update(
            {
                "Cookie": secret,
            }
        )

    # Check the connection if ssl fail disable ssl checks and try again and check status code
    try:
        r = s.get(f"{url}/api/access-control/user/permissions")
    except requests.exceptions.SSLError:
        s.verify = False
        urllib3.disable_warnings()
        r = s.get(f"{url}/api/access-control/user/permissions")
    if r.status_code != 200:
        print("Grafana connection not available")
        exit(1)
    print("Connection established")

s = requests.Session()
login(s, args.secret)

# TODO export plugin list (include version tags) for comparison after import

# fetch all folders including id 0 for general
folders = []
r = s.get(f"{url}/api/folders")
for id in [x["id"] for x in r.json()] + [0]:
    r = s.get(f"{url}/api/folders/id/{id}")
    folders.append(r.json())
print(f"Found: {len(folders)} folders")

# remove empty folders

# fetch all dashboards (max 5000)
dashboards = []
tag_query = ""
if args.tag:
    tag_query = f"&tag={args.tag}"

r = s.get(f"{url}/api/search?limit=5000{tag_query}")
for uid in [x["uid"] for x in r.json()]:
    r = s.get(f"{url}/api/dashboards/uid/{uid}")
    dashboards.append(r.json())
print(f"Found: {len(dashboards)} dashboards")

def add_folder_uid_to_dashlist_panel(dashlist_panel):
    folder_id = dashlist_panel['options']['folderId']
    if folder_id != 0:
        try:
            folder_uid = [folder['uid'] for folder in folders if folder['id'] == folder_id][0]
        except IndexError:
            print(f"Dashlist panel transformer: folder with id: {folder_id} not found keeping the current id")
            return dashlist_panel
        dashlist_panel['options']['folderUid'] = folder_uid
        del dashlist_panel['options']['folderId']

    return dashlist_panel

# find all folderId references and replace with folder Uid for better portability 
# test with: home_dashboard KCEL

def add_folder_uid_to_dashlist_panels(obj):
    if isinstance(obj, list):
        return [add_folder_uid_to_dashlist_panels(i) for i in obj]
    elif isinstance(obj, dict):
        if 'type' in obj and obj['type'] == 'dashlist':
            # do work on dashlist_panel
            return add_folder_uid_to_dashlist_panel(obj)
        else:
            return {k: add_folder_uid_to_dashlist_panels(v) for k, v in obj.items()}
    else:
        return obj

dashboards = add_folder_uid_to_dashlist_panels(dashboards)

def nobackup_panel(obj):
    if isinstance(obj, dict):
        if 'description' in obj and obj['description'] is not None and "NOBACKUP" in obj['description']:
            return True
    return False

def remove_nobackup_panels(obj):
    if isinstance(obj, list):
        return [remove_nobackup_panels(i) for i in obj if not nobackup_panel(i) ]
    elif isinstance(obj, dict):
        return {k: remove_nobackup_panels(v) for k, v in obj.items()}
    else:
        return obj

dashboards = remove_nobackup_panels(dashboards)


# fetch all datasources
datasources = []
r = s.get(f"{url}/api/datasources")
for uid in [x["uid"] for x in r.json()]:
    r = s.get(f"{url}/api/datasources/uid/{uid}")
    datasources.append(r.json())
print(f"Found: {len(datasources)} datasources")


# fetch all alert rules
alertrules = []
rules = s.get(f"{url}/api/ruler/grafana/api/v1/rules").json()
for folder in rules:
    for x in rules[folder]:
        for y in x['rules']:
            uid = y['grafana_alert']['uid']
            alertrules.append(s.get(f"{url}/api/v1/provisioning/alert-rules/{uid}").json())
print(f"Found: {len(alertrules)} alertrules")



# write pickle / json
grafana_backup = {"folders": folders, "dashboards": dashboards, "datasources": datasources, "alertrules": alertrules }

# if location is folder choose output name automaticly
if os.path.isdir(args.location):
    timestamp = datetime.now().isoformat()
    # Folder from location input + server base url + timestamp + output format
    output_file = Path(args.location, f'{args.url.split("://")[1]}_{timestamp}.{args.out_format}'.replace(":",""))
else:
    output_file = Path(args.location)

if args.out_format == "pickle":
    with output_file.open(mode="wb") as f:
        pickle.dump(grafana_backup, f)
elif args.out_format == "json":
    with output_file.open(mode="w") as f:
        json.dump(grafana_backup, f, indent=4)
