import os
import json
import requests
from pprint import pprint
from time import sleep
import argparse
from sys import argv
import pickle
import urllib3

example_text = """
    This tool helps you to import folders, dashboards and data sources to a grafana instance.
"""

parser = argparse.ArgumentParser(
    description="Grafana importer",
    epilog=example_text,
    formatter_class=argparse.RawDescriptionHelpFormatter,
)

parser.add_argument("--location", dest="location", help="The location of the dump")
parser.add_argument("--secret", dest="secret", help="grafana_session=## cookie, glsa_## Service account token or apikey")
parser.add_argument("--url", dest="url", help="The grafana URL: https://grafana.local")
parser.add_argument("--format", dest="format", help="the dump format: pickle of json")
parser.add_argument("--override", default=False, dest="override", help="remove all dashboards and folders before importing", action="store_true")
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

def get_current_state():
    datasources = s.get(f"{url}/api/datasources").json()
    folders = s.get(f"{url}/api/folders").json()
    dashboards = s.get(f"{url}/api/search?limit=5000").json()
    alertrules = s.get(f"{url}/api/ruler/grafana/api/v1/rules")

    # alert rule api is ugly
    alertrules = []
    r = s.get(f"{url}/api/ruler/grafana/api/v1/rules")
    for folder in r.json():
        for x in r.json()[folder]:
            for y in x['rules']:
                alertrules.append(y['grafana_alert']['uid'])
    return datasources, folders, dashboards, alertrules

# pull current state
current_datasources, current_folders, current_dashboards, current_alertrules = get_current_state()

# if override is active
if args.override:
    # delete all the resources
    for uid in [x["uid"] for x in current_dashboards]:
        print(f"DELETE {url}/api/dashboards/uid/{uid}")
        s.delete(f"{url}/api/dashboards/uid/{uid}")
    for uid in [x["uid"] for x in current_folders]:
        print(f"DELETE {url}/api/folders/{uid}")
        s.delete(f"{url}/api/folders/{uid}")
   #No support for migrating datasource passwords, so not using this for now
   #for uid in [x["uid"] for x in current_datasources]:
   #    print(f"DELETE {url}/api/datasources/uid/{uid}")
   #    s.delete(f"{url}/api/datasources/uid/{uid}")
    print(f"deleted all resources at: {url}")
    # reset current state
    current_datasources, current_folders, current_dashboards = [],[],[]

# load the pickle / json dump
if args.format == "pickle":
    with open(args.location, "rb") as f:
        grafana_backup = pickle.load(f)
elif args.format == "json":
    with open(args.location, "r") as f:
        grafana_backup = json.load(f)


# import all datasources
for backup_datasource in grafana_backup["datasources"]:
    if backup_datasource["uid"] in [f["uid"] for f in current_datasources]:
        # found a uid match
        continue
    s.post(f"{url}/api/datasources", data=json.dumps(backup_datasource))


for backup_folder in grafana_backup["folders"]:
    if backup_folder["id"] == 0:
        # skip general folder because we can't create it as it already exists
        continue
    if backup_folder["uid"] in [f["uid"] for f in current_folders]:
        # found a uid match
        continue
    if backup_folder["title"] in [f["title"] for f in current_folders]:
        # found a title match, get the current folder and edit the uid and put it back into grafana
        current_id = [f["id"] for f in current_folders if f["title"] == backup_folder["title"] ][0]
        merge = s.get(f"{url}/api/folders/id/{current_id}").json()
        current_uid = merge['uid']
        merge["uid"] = backup_folder["uid"]
        r = s.put(f"{url}/api/folders/{current_uid}", data=json.dumps(merge))
        print(f"merged {backup_folder['title']}")
        continue
    # no matches, post a new folder from the backup
    s.post(f"{url}/api/folders", data=json.dumps(backup_folder))
    print(f"imported {backup_folder['title']}")

current_datasources, current_folders, current_dashboards, current_alertrules = get_current_state()
def add_folder_id_to_dashlist_panel(dashlist_panel):
    if 'folderUid' in dashlist_panel['options']:
        folder_uid = dashlist_panel['options']['folderUid']
        folder_id = [folder['id'] for folder in current_folders if folder['uid'] == folder_uid][0]
        dashlist_panel['options']['folderId'] = folder_id
    return dashlist_panel

def add_folder_id_to_dashlist_panels(obj):
    if isinstance(obj, list):
        return [add_folder_id_to_dashlist_panels(i) for i in obj]
    elif isinstance(obj, dict):
        if 'type' in obj and obj['type'] == 'dashlist':
            # do work on dashlist_panel
            return add_folder_id_to_dashlist_panel(obj)
        else:
            return {k: add_folder_id_to_dashlist_panels(v) for k, v in obj.items()}
    else:
        return obj

grafana_backup["dashboards"] = add_folder_id_to_dashlist_panels(grafana_backup["dashboards"])

for backup_dashboard in grafana_backup["dashboards"]:
    # if dash-lock true manipulate dashboard to locked befor importing

    
    if backup_dashboard["dashboard"]["uid"] in [f["uid"] for f in current_dashboards]:
        # found a uid match
        continue
    if backup_dashboard["dashboard"]["title"] in [f["title"] for f in current_dashboards]:
        # found a title match, get the current folder and edit the uid and put it back into grafana
        current_uid = [f["uid"] for f in current_dashboards if f["title"] == backup_dashboard["dashboard"]["title"] ][0]
        merge = s.get(f"{url}/api/dashboards/uid/{current_uid}").json()
        del merge["dashboard"]["id"]
        merge["dashboard"]["uid"] = backup_dashboard["dashboard"]["uid"]
        merge['overwrite'] = True
        r = s.put(f"{url}/api/dashboards/db", data=json.dumps(merge))
        print(r.json())
        print(f"Merged {backup_dashboard['dashboard']['title']}")
        continue
    # no matches, post a new dashboard from the backup
    dashboard_request_body = {}
    dashboard_request_body['dashboard'] = backup_dashboard['dashboard']
    dashboard_request_body['folderUid'] = backup_dashboard["meta"]['folderUid']
    # remove the old ID to trigger creation of a new one
    dashboard_request_body['dashboard']['id'] = None
    s.post(f"{url}/api/dashboards/db", data=json.dumps(dashboard_request_body))


# TODO check plugin diff and display mismatches to the user

keep_list = ['condition', 'data', 'execErrState', 'folderUID','noDataState', 'orgID', 'ruleGroup', 'title', 'uid', 'for']

# import all alerts 
for backup_alertrule in grafana_backup["alertrules"]:
    if backup_alertrule["uid"] in current_alertrules:
        # found a uid match
        s.delete(f"{url}/api/v1/provisioning/alert-rules/{backup_alertrule['uid']}")
        # continue
    backup_alertrule = {k: v for k, v in backup_alertrule.items() if k in keep_list}
    s.post(f"{url}/api/v1/provisioning/alert-rules", data=json.dumps(backup_alertrule))


print("import completed")