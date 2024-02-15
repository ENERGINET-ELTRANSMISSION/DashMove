#!/bin/env python3

# cli input handling
import argparse, sys

# http session
import requests

# handle broken ssl
import urllib3

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
    print(f"\nConnection established with: {url}")
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
        r = s.get(f"{url}/api/dashboards/uid/{uid}").json()
        
        # check if dashboard is a folder, dot not include folder in dashboard backup
        if "isFolder" in r['meta'] and r['meta']["isFolder"] is True:
            continue
        
        dashboards.append(r)
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

    print(f"\nWriting backup to: {output_file} \n")

    if data_format == "pickle":
        with output_file.open(mode="wb") as f:
            pickle.dump(grafana_backup, f)
    elif data_format == "json":
        with output_file.open(mode="w") as f:
            json.dump(grafana_backup, f, indent=4)


def add_folder_uid_to_dashlist_panel(dashlist_panel, folders):
    """Add folder Uid reference to dashlist panels in backup to be able to reconstruct on import."""
    # main input validation if this pannel has a folderId
    if "folderId" not in dashlist_panel["options"]:
        return dashlist_panel
    
    # check if folderId is set to 0 (root folder)
    folder_id = dashlist_panel["options"]["folderId"]
    if folder_id == 0:
        return dashlist_panel
    
    # try to match the folderId to a folderUid
    try:
        folder_uid = [
            folder["uid"] for folder in folders if folder["id"] == folder_id
        ][0]
    except IndexError:
        print(
            f"Dashlist panel transformer: folder with id: {folder_id} not found keeping the current id"
        )
        return dashlist_panel

    # add the folderUid to the panel
    dashlist_panel["options"]["folderUid"] = folder_uid
    # remove the folderId
    del dashlist_panel["options"]["folderId"]
    # return the panel
    return dashlist_panel


def add_folder_uid_to_dashlist_panels(dashboards, folders):
    """Recursive fuction to find all dashlist panels in backup and add uid pointer to make dashlists portable."""
    if isinstance(dashboards, list):
        return [add_folder_uid_to_dashlist_panels(i, folders) for i in dashboards]
    elif isinstance(dashboards, dict):
        if "type" in dashboards and dashboards["type"] == "dashlist":
            # do work on dashlist_panel
            return add_folder_uid_to_dashlist_panel(dashboards, folders)
        else:
            return {
                k: add_folder_uid_to_dashlist_panels(v, folders)
                for k, v in dashboards.items()
            }
    else:
        return dashboards


def add_folder_id_to_dashlist_panel(dashlist_panel, current_folders):
    if "folderUid" in dashlist_panel["options"]:
        folder_uid = dashlist_panel["options"]["folderUid"]
        folder_id = [
            folder["id"] for folder in current_folders if folder["uid"] == folder_uid
        ][0]
        dashlist_panel["options"]["folderId"] = folder_id
    return dashlist_panel


def add_folder_id_to_dashlist_panels(obj, current_folders):
    if isinstance(obj, list):
        return [add_folder_id_to_dashlist_panels(i, current_folders) for i in obj]
    elif isinstance(obj, dict):
        if "type" in obj and obj["type"] == "dashlist":
            # do work on dashlist_panel
            return add_folder_id_to_dashlist_panel(obj, current_folders)
        else:
            return {
                k: add_folder_id_to_dashlist_panels(v, current_folders)
                for k, v in obj.items()
            }
    else:
        return obj


def nobackup_panel(obj):
    """Check if object has NOBACKUP flag set in description"""
    if isinstance(obj, dict):
        if (
            "description" in obj
            and obj["description"] is not None
            and "NOBACKUP" in obj["description"]
        ):
            return True
    return False


def remove_nobackup_panels(obj):
    """Remove NOBACKUP objects from the backup"""
    if isinstance(obj, list):
        return [remove_nobackup_panels(i) for i in obj if not nobackup_panel(i)]
    elif isinstance(obj, dict):
        return {k: remove_nobackup_panels(v) for k, v in obj.items()}
    else:
        return obj


def dash_export(args, s):
    # get current state
    datasources, folders, dashboards, alertrules = get_current_state(
        s, args.url, args.tag
    )
    print(
        f"""
        Found: {len(datasources)} datasources
        Found: {len(folders)} folders
        Found: {len(dashboards)} dashboards
        Found: {len(alertrules)} alertrules
        """
    )

    # pull in full backup data not just metadata
    datasources = fetch_datasources(s, args.url, datasources)
    folders = fetch_folders(s, args.url, folders)
    dashboards = fetch_dashboards(s, args.url, dashboards)
    alertrules = fetch_alertrules(s, args.url, alertrules)

    # add uid to dashlist panels for portability
    dashboards = add_folder_uid_to_dashlist_panels(dashboards, folders)

    # remove panels with NOBACKUP in the description from the dashboard backup
    dashboards = remove_nobackup_panels(dashboards)

    grafana_backup = {
        "folders": folders,
        "dashboards": dashboards,
        "datasources": datasources,
        "alertrules": alertrules,
    }

    write_to_filesystem(grafana_backup, args.location, args.data_format, args.url)


def dash_purge(s, url, datasources, folders, dashboards, alertrules):
    # delete all the resources
    for uid in [x["uid"] for x in dashboards]:
        print(f"DELETE {url}/api/dashboards/uid/{uid}")
        s.delete(f"{url}/api/dashboards/uid/{uid}")
    for uid in [x["uid"] for x in folders]:
        print(f"DELETE {url}/api/folders/{uid}")
        s.delete(f"{url}/api/folders/{uid}")
    # Alert rules get deleted if you delete the folder
    #for uid in [x["uid"] for x in folders]:
    #    print(f"DELETE {url}/api/folders/{uid}")
    #    s.delete(f"{url}/api/folders/{uid}")
    # for uid in [x["uid"] for x in current_datasources]:
    #    print(f"DELETE {url}/api/datasources/uid/{uid}")
    #    s.delete(f"{url}/api/datasources/uid/{uid}")
    # TODO add alertrule purge
    print(f"deleted all resources at: {url}")


def load_backup_file(location, data_format):
    if data_format == "pickle":
        with open(location, "rb") as f:
            grafana_backup = pickle.load(f)
    elif data_format == "json":
        with open(location, "r") as f:
            grafana_backup = json.load(f)
    return grafana_backup


def import_datasources(s, url, datasources_import, datasources_current):
    for datasource in datasources_import:
        if datasource["uid"] in [f["uid"] for f in datasources_current]:
            # found a uid match
            continue
        s.post(f"{url}/api/datasources", data=json.dumps(datasource))
        print(f"Imported datasource: {datasource['name']}")
    return s.get(f"{url}/api/datasources").json()


def import_folders(s, url, folders_import, folders_current):
    for backup_folder in folders_import:
        if backup_folder["id"] == 0:
            # skip general folder because we can't create it as it already exists by deafult
            continue
        if backup_folder["uid"] in [f["uid"] for f in folders_current]:
            # found a uid match
            continue
        # disabled, beacause it could trigger unwanted bahaviour
        # this does help if you want to continue a migration you started by hand
        # TODO feature toggle
        # if backup_folder["title"] in [f["title"] for f in current_folders]:
        #     # found a title match, get the current folder and edit the uid and put it back into grafana
        #     current_id = [f["id"] for f in current_folders if f["title"] == backup_folder["title"] ][0]
        #     merge = s.get(f"{url}/api/folders/id/{current_id}").json()
        #     current_uid = merge['uid']
        #     merge["uid"] = backup_folder["uid"]
        #     r = s.put(f"{url}/api/folders/{current_uid}", data=json.dumps(merge))
        #     print(f"merged {backup_folder['title']}")
        #     continue
        # no matches, post a new folder from the backup
        s.post(f"{url}/api/folders", data=json.dumps(backup_folder))
        print(f"Imported folder: {backup_folder['title']}")
    return s.get(f"{url}/api/folders").json()


def import_dashboards(s, url, dashboards_import, dashboards_current):
    for backup_dashboard in dashboards_import:
        if backup_dashboard["dashboard"]["uid"] in [
            f["uid"] for f in dashboards_current
        ]:
            # found a uid match


        keep_fields = [
            "description",
            "parentUid",
            "title",
            "uid"
        ]

        backup_folder = {k: v for k, v in backup_folder.items() if k in keep_fields}

            continue
        # disabled, beacause it could trigger unwanted bahaviour
        # this does help if you want to continue a migration you started by hand
        # TODO feature toggle
        # if backup_dashboard["dashboard"]["title"] in [f["title"] for f in dashboards_current]:
        #     # found a title match, get the current folder and edit the uid and put it back into grafana
        #     current_uid = [f["uid"] for f in dashboards_current if f["title"] == backup_dashboard["dashboard"]["title"] ][0]
        #     merge = s.get(f"{url}/api/dashboards/uid/{current_uid}").json()
        #     del merge["dashboard"]["id"]
        #     merge["dashboard"]["uid"] = backup_dashboard["dashboard"]["uid"]
        #     merge['overwrite'] = True
        #     r = s.put(f"{url}/api/dashboards/db", data=json.dumps(merge))
        #     print(r.json())
        #     print(f"Merged {backup_dashboard['dashboard']['title']}")
        #     continue
        # no matches, post a new dashboard from the backup
        dashboard_request_body = {}
        dashboard_request_body["dashboard"] = backup_dashboard["dashboard"]
        dashboard_request_body["folderUid"] = backup_dashboard["meta"]["folderUid"]
        # remove the old ID to trigger creation of a new one
        dashboard_request_body["dashboard"]["id"] = None
        s.post(f"{url}/api/dashboards/db", data=json.dumps(dashboard_request_body))
        print(f"Imported dashboard: {backup_dashboard['dashboard']['title']}")

    return s.get(f"{url}/api/search?limit=5000").json()


def import_alertrules(s, url, alertrules_import, alertrules_current):
    keep_list = [
        "condition",
        "data",
        "execErrState",
        "folderUID",
        "noDataState",
        "orgID",
        "ruleGroup",
        "title",
        "uid",
        "for",
    ]
    # import all alerts
    for backup_alertrule in alertrules_import:
        if backup_alertrule["uid"] in [f["uid"] for f in alertrules_current]:
            # found a uid match
            continue
        backup_alertrule = {k: v for k, v in backup_alertrule.items() if k in keep_list}
        s.post(
            f"{url}/api/v1/provisioning/alert-rules", data=json.dumps(backup_alertrule)
        )
        print(f"Imported alertrule: {backup_alertrule['title']}")
    alertrules = []
    rules = s.get(f"{url}/api/ruler/grafana/api/v1/rules").json()
    for folder in rules:
        for x in rules[folder]:
            for y in x["rules"]:
                alertrules.append(y["grafana_alert"])
    return alertrules


def dash_import(args, s):
    # get current state
    datasources, folders, dashboards, alertrules = get_current_state(s, args.url)
    # if override is active
    if args.override:
        dash_purge(s, args.url, datasources, folders, dashboards, alertrules)
        datasources, folders, dashboards, alertrules = get_current_state(s, args.url)

    grafana_current = {
        "datasources": datasources,
        "folders": folders,
        "dashboards": dashboards,
        "alertrules": alertrules,
    }
    grafana_backup = load_backup_file(args.location, args.data_format)

    grafana_current["datasources"] = import_datasources(
        s, args.url, grafana_backup["datasources"], grafana_current["datasources"]
    )
    grafana_current["folders"] = import_folders(
        s, args.url, grafana_backup["folders"], grafana_current["folders"]
    )

    # use current folder state to adjust dashlist panels to the new folder ids
    grafana_backup["dashboards"] = add_folder_id_to_dashlist_panels(
        grafana_backup["dashboards"], grafana_current["folders"]
    )

    grafana_current["dashboards"] = import_dashboards(
        s, args.url, grafana_backup["dashboards"], grafana_current["dashboards"]
    )
    grafana_current["alertrules"] = import_alertrules(
        s, args.url, grafana_backup["alertrules"], grafana_current["alertrules"]
    )
    print("\nimport completed.\n")


if __name__ == "__main__":
    # cli_arguments will sys.exit() on non valid input / help
    args = cli_arguments()
    # session setup will sys.exit(1) if connection fails
    s = login(args.url, args.secret)

    # perform export or import
    if args.command == "export":
        dash_export(args, s)
    elif args.command == "import":
        dash_import(args, s)
