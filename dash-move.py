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

import logging

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
        help="Dump format: json, pickle(default)",
    )
    import_parser.add_argument(
        "--override",
        default=False,
        dest="override",
        help="Remove everything before importing",
        action="store_true",
    )
    import_parser.add_argument(
        "--debug",
        default=False,
        dest="debug",
        help="Enable debug logging",
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
        "--tag",
        dest="tag", 
        help="Tag used to only include dashboads with tag during export (only 1 tag supported)",
    )
    export_parser.add_argument(
        "--format",
        dest="data_format",
        default="pickle",
        help="Dump format: json pickle(default)",
    )
    export_parser.add_argument(
        "--debug",
        default=False,
        dest="debug",
        help="Enable debug logging",
        action="store_true",
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

def count_receivers(policy):
    count = 0

    # count this level's receiver (if present)
    if 'receiver' in policy:
        count += 1

    # recursively count receivers in child routes
    for route in policy.get('routes', []):
        count += count_receivers(route)

    return count


def get_current_state(s, url, tag=False):
    """
    Returns the current objects in the connected grafana instance. (mostly metadata)
    It doesn't download all the data inside the objects: datasources, folders, dashboards and alertrules.
    Use the fetch_ functions to get all the data inside those objects.
    Use tag to filter dashboards based on that tag.
    """
    tag_query = f"&tag={tag}" if tag else ""
    datasources = s.get(f"{url}/api/datasources").json()
    main_folders = s.get(f"{url}/api/folders").json()
    sub_folders = []
    for uid in [x["uid"] for x in main_folders]:
        sub_folders += s.get(f"{url}/api/folders?parentUid={uid}").json()

    folders = main_folders + sub_folders

    dashboards = s.get(f"{url}/api/search?limit=5000&type=dash-db{tag_query}").json()
    contactpoints = s.get(f"{url}/api/v1/provisioning/contact-points").json()
    policies = s.get(f"{url}/api/v1/provisioning/policies").json()

    alertrules = s.get(f"{url}/api/v1/provisioning/alert-rules").json()

    # alertrules = []
    # rules = s.get(f"{url}/api/ruler/grafana/api/v1/rules").json()
    # for folder in rules:
    #     for x in rules[folder]:
    #         for y in x["rules"]:
    #             alertrules.append(y["grafana_alert"])

    preferences = fetch_preferences(s, url)

    return datasources, folders, dashboards, alertrules, contactpoints, policies, preferences


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
    
    dashboard_list = [d for d in dashboard_list if d.get("type") != "dash-folder"]
    for uid in [x["uid"] for x in dashboard_list]:
        r = s.get(f"{url}/api/dashboards/uid/{uid}").json()
        
        # check if dashboard is a folder, dot not include folder in dashboard backup
        # if "isFolder" in r['meta'] and r['meta']["isFolder"] is True:
        #     continue
        
        dashboards.append(r)
    return dashboards


def fetch_alertrules(s, url, alertrules_list):
    alertrules = []
    rulegroups = []
    for uid in [x["uid"] for x in alertrules_list]:
        r = s.get(f"{url}/api/v1/provisioning/alert-rules/{uid}")
        alertrules.append(r.json())

    used_rulegroups = {item["folderUID"]: item["ruleGroup"] for item in alertrules_list}

    for folder_uid, rule_group in used_rulegroups.items():
        r = s.get(f"{url}/api/v1/provisioning/folder/{folder_uid}/rule-groups/{rule_group}")
        rulegroups.append(r.json())

    for i, rulegroup in enumerate(rulegroups):
        if isinstance(rulegroup, str):
            rulegroup = json.loads(rulegroup)
        rulegroup.pop("rules", None)
        rulegroups[i] = rulegroup

    return alertrules, rulegroups

def fetch_contactpoints(s, url, contactpoints_list):
    contactpoints = []
    contactpoints = s.get(f"{url}/api/v1/provisioning/contact-points").json()
    return contactpoints

def fetch_policies(s, url, policies_list):
    policies = []
    policies = s.get(f"{url}/api/v1/provisioning/policies").json()
    return policies

def fetch_preferences(s, url):
    """
    Returns the current preferences in the connected grafana instance.
    """
    org = s.get(f"{url}/api/org/preferences").json()

    # get all teams
    teams = s.get(f"{url}/api/teams/search").json()
    
    team_prefs = []
    if 'teams' in teams and 'totalCount' in teams and teams['totalCount'] > 0:
        # Found teams, lets get the preferences
        for team in teams['teams']:
            team['preferences'] = s.get(f"{url}/api/teams/{team['id']}/preferences").json()
            team_prefs.append(team)

    #TODO: we might want to migrate user preferences but we are not allowed to access that through the api at the moment

    return {"org": org, "teams": team_prefs}


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

    # print(grafana_backup)

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
    # ensure options and folderUid exist
    if not isinstance(dashlist_panel, dict):
        return dashlist_panel
    options = dashlist_panel.get("options")
    if not options or "folderUid" not in options:
        return dashlist_panel

    folder_uid = options["folderUid"]
    # safe lookup instead of indexing into possibly-empty list
    folder_id = next((folder.get("id") for folder in current_folders if folder.get("uid") == folder_uid), None)
    if folder_id is None:
        logging.warning(f"folderUid '{folder_uid}' not found in current instance; keeping folderUid")
        return dashlist_panel

    dashlist_panel["options"]["folderId"] = folder_id
    # optionally remove folderUid if you don't want to keep it:
    # dashlist_panel["options"].pop("folderUid", None)
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
    logging.info("Export started")

    # get current state
    datasources, folders, dashboards, alertrules, contactpoints, policies, preferences = get_current_state(
        s, args.url, args.tag
    )
    print(
        f"""
        Found: {len(datasources)} datasources
        Found: {len(folders)} folders
        Found: {len(dashboards)} dashboards
        Found: {len(alertrules)} alertrules
        Found: {len(preferences['org'])} org preferences
        Found: {len(preferences['teams'])} teams preferences
        Found: {len(contactpoints)} contact points
        Found: {count_receivers(policies)} notification policies
        """
    )

    # pull in full backup data not just metadata
    datasources = fetch_datasources(s, args.url, datasources)
    folders = fetch_folders(s, args.url, folders)
    dashboards = fetch_dashboards(s, args.url, dashboards)
    alertrules, rulegroups = fetch_alertrules(s, args.url, alertrules)
    contactpoints = fetch_contactpoints(s, args.url, contactpoints)
    policies = fetch_policies(s, args.url, policies)

    # add uid to dashlist panels for portability
    dashboards = add_folder_uid_to_dashlist_panels(dashboards, folders)

    # remove panels with NOBACKUP in the description from the dashboard backup
    dashboards = remove_nobackup_panels(dashboards)

    grafana_backup = {
        "folders": folders,
        "dashboards": dashboards,
        "datasources": datasources,
        "rulegroups": rulegroups,
        "alertrules": alertrules,
        "preferences": preferences,
        "contactpoints": contactpoints,
        "policies": policies,
    }

    write_to_filesystem(grafana_backup, args.location, args.data_format, args.url)

    logging.info("Export Completed")

def dash_purge(s, url, folders, dashboards, contactpoints, policies, alertrules):
    # delete dashboards
    for dashboard in dashboards:
        if dashboard["type"] == "dash-folder":
            continue
        dashboard_name = dashboard["title"]
        dashboard_uid = dashboard["uid"]
        resp = s.delete(f"{url}/api/dashboards/uid/{dashboard_uid}")
        if resp.status_code == 200:
            logging.info(f"Deleted dashboard: {dashboard_uid} with name: {dashboard_name}")
        else:
            logging.warning(f"Failed to delete dashboard with status code: {resp.status_code}")

    #delete alerts
    for alertrule in alertrules:
        alertrule_name = alertrule["title"]
        alertrule_uid = alertrule["uid"]

        resp = s.delete(f"{url}/api/v1/provisioning/alert-rules/{alertrule_uid}")

        if resp.status_code == 204:
            logging.info(f"Deleted alert rule: {alertrule_uid} with name: {alertrule_name}")
        else:
            logging.warning(f"Failed to delete alert rule {alertrule_name} with status code: {resp.status_code}")

    # delete folders
    for folder in folders:
        folder_name = folder["title"]
        folder_uid = folder["uid"]

        resp = s.delete(f"{url}/api/folders/{folder_uid}")

        if resp.status_code == 200:
            logging.info(f"Deleted folder: {folder_uid} with name: {folder_name}")
        else:
            logging.warning(f"Failed to delete folder {folder_name} with status code: {resp.status_code}")

    # # delete datasources
    # for datasource in datasources:
    #     datasource_name = datasource["name"]
    #     datasource_uid = datasource["uid"]

    #     resp = s.delete(f"{url}/api/datasources/uid/{datasource_uid}")

    #     if resp.status_code == 200:
    #         logging.info(f"Deleted datasource: {datasource_uid} with name: {datasource_name}")
    #     else:
    #         logging.warning(f"Failed to delete datasource {datasource_name} with status code: {resp.status_code}")

    # delete notification policies

    resp = s.delete(f"{url}/api/v1/provisioning/policies")

    if resp.status_code == 202:
        logging.info(f"Deleted notification policies")
    else:
        logging.warning(f"Failed to delete notification policies with status code: {resp.status_code}")

    # delete contactpoints
    for cp in contactpoints:
        cp_name = cp["name"]
        cp_uid = cp["uid"]

        resp = s.delete(f"{url}/api/v1/provisioning/contact-points/{cp_uid}")

        if resp.status_code == 202:
            logging.info(f"Deleted contact point: {cp_uid} with name: {cp_name}")
        else:
            logging.warning(f"Failed to delete contact point {cp_name} with status code: {resp.status_code}")

def load_backup_file(location, data_format):
    if data_format == "pickle":
        with open(location, "rb") as f:
            grafana_backup = pickle.load(f)
    elif data_format == "json":
        with open(location, "r") as f:
            grafana_backup = json.load(f)
    return grafana_backup


def import_datasources(s, url, datasources_import, datasources_current):
    duplicated_datasources = 0
    imported_datasources = 0
    for datasource in datasources_import:
        if datasource["uid"] in [f["uid"] for f in datasources_current]:
            # found a uid match
            duplicated_datasources += 1
            continue
        if datasource["name"] in [f["name"] for f in datasources_current]:
            # found a name match
            # check type
            if datasource["type"] != [f["type"] for f in datasources_current if f["name"] == datasource["name"]][0]:
                logging.warning(f"Datasource {datasource['name']} type mismatch found during import! Some dashboards may not work.")
                continue
            if args.override:
                logging.info(f"Datasource {datasource['name']} found in destination with other uid, deleting it before importing. (Override selected)")
                # get current uid
                uid = [f["uid"] for f in datasources_current if f["name"] == datasource["name"]][0]
                s.delete(f"{url}/api/datasources/uid/{uid}")
            else:
                logging.warning(f"Datasource {datasource['name']} found in destination with other uid, skipping it, some dashboards may not work. (Override not selected)")
                continue
        s.post(f"{url}/api/datasources", data=json.dumps(datasource))
        imported_datasources += 1
        logging.info(f"Imported datasource: {datasource['name']}")
    return imported_datasources, duplicated_datasources


def import_folders(s, url, folders_import, folders_current, override):
    duplicated_folders = 0
    imported_folders = 0

    # check for folder uids that are in current and not in the import
    if override:
        for folder in folders_current:
            if folder["uid"] in [f["uid"] for f in folders_import]:
                # found a uid match, not deleteing it because of api bugs with recreating
                continue
            print(f"Folder {folder['title']} found in current and not in backup, deleting it.")
            s.delete(f"{url}/api/folders/{folder['uid']}")


    for backup_folder in folders_import:
        if backup_folder["id"] == 0:
            # skip general folder because we can't create it as it already exists by default
            continue
        if backup_folder["uid"] in [f["uid"] for f in folders_current]:
            # found a uid match
            duplicated_folders += 1
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


        keep_fields = [
            "description",
            "parentUid",
            "title",
            "uid"
        ]

        backup_folder = {k: v for k, v in backup_folder.items() if k in keep_fields}

        s.post(f"{url}/api/folders", data=json.dumps(backup_folder))       
        imported_folders += 1
        logging.info(f"Imported folder: {backup_folder['title']}")
    return imported_folders, duplicated_folders


def import_dashboards(s, url, dashboards_import, dashboards_current):
    duplicated_dashboards = 0
    imported_dashboards = 0
    for backup_dashboard in dashboards_import:
        if backup_dashboard["dashboard"]["uid"] in [
            f["uid"] for f in dashboards_current
        ]:
            # found a uid match
            duplicated_dashboards += 1
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
        imported_dashboards += 1
        logging.info(f"Imported dashboard: {backup_dashboard['dashboard']['title']}")

    return imported_dashboards, duplicated_dashboards


def import_rulegroups(s, url, rulegroups_import):
    imported_rulegroups = 0

    for rule in rulegroups_import:
        # Import the rule
        try:
            resp = s.put(f"{url}/api/v1/provisioning/folder/{rule['folderUid']}/rule-groups/{rule['title']}", data=json.dumps(rule))
            if resp.status_code < 300:
                logging.info(f"Imported rulegroup: {rule['folderUid']} {rule['title']}")
                imported_rulegroups += 1
            else:
                logging.error(f"Failed to import rulegroup: {rule['folderUid']} {rule['title']}")
        except Exception as e:
            logging.error(f"Exception importing rulegroup: {rule['folderUid']} {rule['title']}: {str(e)}")
    return imported_rulegroups

def import_alertrules(s, url, alertrules_import, alertrules_current, override=False):
    duplicated_alertrules = 0
    imported_alertrules = 0
    
    # Get available contact points/notification receivers in target Grafana instance
    try:
        cp_resp = s.get(f"{url}/api/v1/provisioning/contact-points")
        if cp_resp.status_code == 200:
            available_contact_points = {cp['name']: cp for cp in cp_resp.json()}
        else:
            logging.error(f"Warning: Could not fetch contact points (HTTP {cp_resp.status_code}). Proceeding without validation.")
            available_contact_points = {}
    except Exception as e:
        logging.error(f"Warning: Error fetching contact points: {e}. Proceeding without validation.")
        available_contact_points = {}
    
    stats = {"success": 0, "error": 0, "skip": 0, "datasource_missing": 0, "contact_point_missing": 0}
    failed_rules = []
    
    # Process each alert rule
    for rule in alertrules_import:
        uid_exists = rule["uid"] in [r.get("uid") for r in alertrules_current]
        
        # Handle existing rule with same UID
        if uid_exists and not override:
            stats["skip"] += 1
            duplicated_alertrules += 1
            continue
        
        # Check for missing notification receivers/contact points
        if available_contact_points and 'notification_settings' in rule and rule['notification_settings'] is not None:
            notification_settings = rule['notification_settings']
            if 'receiver' in notification_settings and notification_settings['receiver'] not in available_contact_points:
                receiver_name = notification_settings['receiver']
                logging.warning(f"Rule '{rule['title']}' references missing contact point '{receiver_name}'. Not importing.")
                failed_rules.append({
                    'title': rule['title'],
                    'uid': rule.get('uid', 'N/A'),
                    'error': f"Missing contact point: {receiver_name}",
                })
                stats["contact_point_missing"] += 1
                continue

        # Import the rule
        try:
            if uid_exists and override:
                # update existing rule
                resp = s.put(f"{url}/api/v1/provisioning/alert-rules/{rule['uid']}", data=json.dumps(rule))
            else:
                # import new rule
                resp = s.post(f"{url}/api/v1/provisioning/alert-rules", data=json.dumps(rule))
            if resp.status_code < 300:
                logging.info(f"Imported alertrule: {rule['title']}")
                stats["success"] += 1
                imported_alertrules += 1
            else:
                print(f"Error importing rule: {resp.status_code}")
                stats["error"] += 1
        except Exception as e:
            print(f"Exception: {str(e)}")
            stats["error"] += 1
    
    # print("\nAlert rule migration summary:")
    # print(f"  - Imported: {stats['success']}")
    # print(f"  - Errors: {stats['error']}")
    # print(f"  - Skipped (existing): {stats['skip']}")
    # print(f"  - Skipped (missing contact point): {stats['contact_point_missing']}")
    
    # Show detailed error information if there were failures
    if failed_rules:
        print("\nFailed alert rules details:")
        for failed_rule in failed_rules:
            print(f"  - Rule: {failed_rule['title']} (UID: {failed_rule['uid']})")
            print(f"    Error: {failed_rule['error']}")
    
    return imported_alertrules, duplicated_alertrules

def import_preferences(s, url, preferences_import, preferences_current):
    duplicated_preferences = 0
    imported_preferences = 0    

    # override org preferences
    s.put(
        f"{url}/api/org/preferences",
        data=json.dumps(preferences_import['org']),
    )
    logging.info(f"Imported organisation preferences")

    # get all current teams and match the teams against the backup
    teams = s.get(f"{url}/api/teams/search").json()

    if teams['totalCount'] > 0:
        # find team matches
        for team in teams['teams']:
            team_preferences = [x['preferences'] for x in preferences_import['teams'] if x['uid'] == team['uid']]
            if len(team_preferences) > 0:
                # found a team uid match
                s.post(
                    f"{url}/api/teams/{team['id']}/preferences",
                    data=json.dumps(team_preferences[0]),
                )
                imported_preferences += 1
                logging.info(f"Imported team preferences for: {team['name']}")  
                continue

            # try to find a name match 
            team_preferences = [x['preferences'] for x in preferences_import['teams'] if x['name'] == team['name']]
            if len(team_preferences) > 0:
                # found a team name match
                s.put(
                    f"{url}/api/teams/{team['id']}/preferences",
                    data=json.dumps(team_preferences[0]),
                )
                imported_preferences += 1
                logging.info(f"Imported team preferences for: {team['name']}")

    return imported_preferences, duplicated_preferences

def import_contactpoints(s, url, contactpoints_import, contactpoints_current):
    duplicate_contactpoints = 0
    imported_contactpoints = 0
    for backup_contactpoints in contactpoints_import:
        if backup_contactpoints["name"] in [
            f["name"] for f in contactpoints_current]:
                # found a name match
                duplicate_contactpoints += 1
                continue

        contactpoints_request_body = backup_contactpoints

        for receiver in contactpoints_request_body.get("receivers", []):
            receiver.pop("uid", None)

        response = s.post(f"{url}/api/v1/provisioning/contact-points", data=json.dumps(contactpoints_request_body))
        imported_contactpoints += 1
        logging.info(f"Imported contact-point: {backup_contactpoints['name']}")

    return imported_contactpoints, duplicate_contactpoints

def import_policies(s, url, policies_import, policies_current):
    duplicated_policies = 0
    imported_policies = 0

    # Helper to collect all receivers from a policy (including sub-routes)
    def collect_receivers(policy):
        receivers = set()
        if isinstance(policy, dict) and "receiver" in policy:
            receivers.add(policy["receiver"])
        for route in policy.get("routes", []):
            receivers.update(collect_receivers(route))
        return receivers

    # Collect all receivers from current policies
    current_receivers = set()
    if isinstance(policies_current, dict):
        current_receivers.update(collect_receivers(policies_current))
    elif isinstance(policies_current, list):
        for pol in policies_current:
            current_receivers.update(collect_receivers(pol))

    # Support both dict and list for policies_import
    policies_to_import = []
    if isinstance(policies_import, dict):
        policies_to_import = [policies_import]
    elif isinstance(policies_import, list):
        policies_to_import = policies_import

    for backup_policy in policies_to_import:
        import_receivers = collect_receivers(backup_policy)
        # Only skip if ALL receivers are present
        if import_receivers.issubset(current_receivers):
            duplicated_policies += 1
            logging.info(f"Skipped policy: {backup_policy.get('receiver', '[unknown]')} (all receivers already exist)")
            continue

        response = s.put(f"{url}/api/v1/provisioning/policies", data=json.dumps(backup_policy))
        imported_policies += 1
        logging.info(f"Imported policy: {backup_policy.get('receiver', '[unknown]')}")

    return imported_policies, duplicated_policies


def dash_import(args, s):
    logging.info("Import Started")

    # get current state
    datasources, folders, dashboards, alertrules, contactpoints, policies, preferences = get_current_state(s, args.url)

    # if override is active
    if args.override:
        dash_purge(s, args.url, folders, dashboards, contactpoints, policies, alertrules)
        datasources, folders, dashboards, alertrules, contactpoints, policies, preferences = get_current_state(s, args.url)

    grafana_current = {
        "datasources": datasources,
        "folders": folders,
        "dashboards": dashboards,
        "alertrules": alertrules,
        "preferences": preferences,
        "contactpoints": contactpoints,
        "policies": policies,
    }
    grafana_backup = load_backup_file(args.location, args.data_format)

    # use current folder state to adjust dashlist panels to the new folder ids
    grafana_backup["dashboards"] = add_folder_id_to_dashlist_panels(
        grafana_backup["dashboards"], grafana_current["folders"]
    )
    # Import datasources
    imported_datasources, duplicated_datasources = import_datasources(
        s, args.url, grafana_backup["datasources"], grafana_current["datasources"]
    )
    #Import folders
    imported_folders, duplicate_folders = import_folders(
        s, args.url, grafana_backup["folders"], grafana_current["folders"], override=args.override
    )
    # Import dashboards
    imported_dashboards, duplicated_dashboards = import_dashboards(
        s, args.url, grafana_backup["dashboards"], grafana_current["dashboards"]
    )
    # Import contactpoints
    imported_contactpoints, duplicate_contactpoints = import_contactpoints(
        s, args.url, grafana_backup["contactpoints"], grafana_current["contactpoints"]
    )
    # Import alertrules
    imported_alertrules, duplicated_alertrules = import_alertrules(
        s, args.url, grafana_backup["alertrules"], grafana_current["alertrules"]
    )
    # Import rulegroups
    imported_rulegroups = import_rulegroups(
        s, args.url, grafana_backup["rulegroups"]
    )
    # Import preferences
    imported_preferences, duplicated_preferences = import_preferences(
        s, args.url, grafana_backup["preferences"], grafana_current["preferences"]
    )
    # Import policies
    imported_policies, duplicated_policies = import_policies(
        s, args.url, grafana_backup["policies"], grafana_current["policies"]
    )

    print(
        f"""
        Folders:
        Imported: {imported_folders} Skipped: {duplicate_folders}\n
        Datasources:
        Imported: {imported_datasources} Skipped: {duplicated_datasources}\n
        Dashboards:
        Imported: {imported_dashboards} Skipped: {duplicated_dashboards}\n
        Rulegroups:
        Imported: {imported_rulegroups}\n
        Alertrules:
        Imported: {imported_alertrules} Skipped: {duplicated_alertrules}\n
        Preferences:
        Imported: {imported_preferences} Skipped: {duplicated_preferences}\n
        Contactpoints:
        Imported: {imported_contactpoints} Skipped: {duplicate_contactpoints}\n
        Policies:
        Imported: {imported_policies} Skipped: {duplicated_policies}
        """
    )
    
    logging.info("Import completed")

if __name__ == "__main__":
    # cli_arguments will sys.exit() on non valid input / help
    args = cli_arguments()
    # session setup will sys.exit(1) if connection fails
    s = login(args.url, args.secret)
    
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO, format='%(levelname)s - %(message)s')

    # perform export or import
    if args.command == "export":
        dash_export(args, s)
    elif args.command == "import":
        dash_import(args, s)