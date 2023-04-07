#!/bin/env python3

# cli input handling
import argparse, sys

# http session
import requests

# data write and load
import os, pickle, json
from pathlib import Path

# dynamic timestamped names
from datetime import datetime


def cli_arguments():
    """
    Uses Argparse to get user input returns a Namespace object:
    Namespace(command='export', location='/tmp/', secret='glsa_.....', url='https://grafana....', tag=None, data_format='pickle')
    """
    # create the top-level parser
    parser = argparse.ArgumentParser()

    # create sub-parsers for the sub-commands
    subparsers = parser.add_subparsers(dest="command", required=True)

    ## import command argument parsing
    import_parser = subparsers.add_parser("import", help="Grafana importer")
    import_parser.add_argument(
        "--location", dest="location", required=True, help="The location of the dump"
    )
    import_parser.add_argument(
        "--secret",
        dest="secret",
        required=True,
        help="grafana_session=## cookie, glsa_## Service account token or apikey",
    )
    import_parser.add_argument(
        "--url",
        dest="url",
        required=True,
        help="The grafana URL: https://grafana.local",
    )
    import_parser.add_argument(
        "--format",
        dest="data_format",
        default="pickle",
        help="Dump format: json pickle(default)",
    )
    import_parser.add_argument(
        "--override",
        default=False,
        dest="override",
        help="remove everything before importing",
        action="store_true",
    )

    ## export command argument parsing
    export_parser = subparsers.add_parser("export", help="Grafana exporter")
    export_parser.add_argument(
        "--location",
        dest="location",
        required=True,
        help="The location to save the dump, file or folder. (pointing to a folder will automaticly set a time and url specific name)",
    )
    export_parser.add_argument(
        "--secret",
        dest="secret",
        required=True,
        help="grafana_session=## cookie, glsa_## Service account token or apikey",
    )
    export_parser.add_argument(
        "--url",
        dest="url",
        required=True,
        help="The grafana URL: https://grafana.local",
    )
    export_parser.add_argument(
        "--tag", dest="tag", help="The tag you want to include in your dump"
    )
    export_parser.add_argument(
        "--format",
        dest="data_format",
        default="pickle",
        help="Dump format: json pickle(default)",
    )

    # parse the command-line arguments and show help also for subcommands if argument list < 2
    return parser.parse_args(args=None if sys.argv[2:] else sys.argv[1:2] + ["--help"])


def login(url, secret):
    """Returns a requests session which can communicate with the grafana instance."""
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": "DashMove",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Disable-Provenance": "true",
        }
    )

    # set auth headers
    if secret.startswith("glsa_") or secret.startswith("ey"):
        s.headers.update({"Authorization": f"Bearer {secret}"})
    elif secret.startswith("grafana_session="):
        s.headers.update(
            {
                "Cookie": secret,
            }
        )

    # Check the connection if ssl fails, disable ssl checks, try again and check status code.
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
    return s


def get_current_state(s, url, tag=False):
    """
    Returns the current objects in the connected grafana instance. (mostly metadata)
    It doesn't download all the data inside the objects: datasources, folders, dashboards and alertrules.
    Use the fetch_ functions to get all the data inside those objects.
    Use tag to filter dashboards based on that tag.
    """
    tag_query = f"&tag={tag}" if tag else ""
    datasources = s.get(f"{url}/api/datasources").json()
    folders = s.get(f"{url}/api/folders").json()
    dashboards = s.get(f"{url}/api/search?limit=5000{tag_query}").json()

    alertrules = []
    rules = s.get(f"{url}/api/ruler/grafana/api/v1/rules").json()
    for folder in rules:
        for x in rules[folder]:
            for y in x["rules"]:
                alertrules.append(y["grafana_alert"])

    return datasources, folders, dashboards, alertrules


def fetch_datasources(s, url, datasources_list):
    datasources = []
    for uid in [x["uid"] for x in datasources_list]:
        r = s.get(f"{url}/api/datasources/uid/{uid}")
        datasources.append(r.json())
    return datasources


def fetch_folders(s, url, folder_list):
    folders = []
    for id in [x["id"] for x in folder_list] + [0]:
        r = s.get(f"{url}/api/folders/id/{id}")
        folders.append(r.json())
    return folders


def fetch_dashboards(s, url, dashboard_list):
    dashboards = []
    for uid in [x["uid"] for x in dashboard_list]:
        r = s.get(f"{url}/api/dashboards/uid/{uid}")
        dashboards.append(r.json())
    return dashboards


def fetch_alertrules(s, url, alertrules_list):
    alertrules = []
    for uid in [x["uid"] for x in alertrules_list]:
        r = s.get(f"{url}/api/v1/provisioning/alert-rules/{uid}")
        alertrules.append(r.json())
    return alertrules


def write_to_filesystem(grafana_backup, location, data_format, url):
    # if location is folder choose output name automaticly
    if os.path.isdir(location):
        timestamp = datetime.now().isoformat(timespec="minutes")
        # Folder from location input + server base url + timestamp + output format
        output_file = Path(
            location,
            f'{url.split("://")[1]}_{timestamp}.{data_format}'.replace(":", ""),
        )
    else:
        output_file = Path(location)

    print(f"\nWriting backup to: {output_file}")

    if data_format == "pickle":
        with output_file.open(mode="wb") as f:
            pickle.dump(grafana_backup, f)
    elif data_format == "json":
        with output_file.open(mode="w") as f:
            json.dump(grafana_backup, f, indent=4)


def add_folder_uid_to_dashlist_panel(dashlist_panel):
    """Add folder Uid reference to dashlist panels in backup to be able to reconstruct on import."""
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


def add_folder_uid_to_dashlist_panels(obj):
    """Find all dashlist panels in backup and add uid pointer to make dashlists portable."""
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


def nobackup_panel(obj):
    """Check if object has NOBACKUP flag set in description """
    if isinstance(obj, dict):
        if 'description' in obj and obj['description'] is not None and "NOBACKUP" in obj['description']:
            return True
    return False


def remove_nobackup_panels(obj):
    """Remove NOBACKUP objects from the backup"""
    if isinstance(obj, list):
        return [remove_nobackup_panels(i) for i in obj if not nobackup_panel(i) ]
    elif isinstance(obj, dict):
        return {k: remove_nobackup_panels(v) for k, v in obj.items()}
    else:
        return obj

if __name__ == "__main__":
    # cli_arguments will sys.exit() on non valid input / help
    args = cli_arguments()
    s = login(args.url, args.secret)
    datasources, folders, dashboards, alertrules = get_current_state(
        s, args.url, args.tag
    )
    print(f"Found: {len(datasources)} datasources")
    print(f"Found: {len(folders)} folders")
    print(f"Found: {len(dashboards)} dashboards")
    print(f"Found: {len(alertrules)} alertrules")

    # pull in full backup data not just metadata
    datasources = fetch_datasources(s, args.url, datasources)
    folders = fetch_folders(s, args.url, folders)
    dashboards = fetch_dashboards(s, args.url, dashboards)
    alertrules = fetch_alertrules(s, args.url, alertrules)

    # add uid to dashlist panels for portability
    dashboards = add_folder_uid_to_dashlist_panels(dashboards)

    # remove panels with NOBACKUP in the description from the dashboard backup
    dashboards = remove_nobackup_panels(dashboards)

    grafana_backup = {
        "folders": folders,
        "dashboards": dashboards,
        "datasources": datasources,
        "alertrules": alertrules,
    }

    write_to_filesystem(grafana_backup, args.location, args.data_format, args.url)
