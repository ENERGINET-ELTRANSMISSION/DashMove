#!/bin/env python3

# cli input handling
import argparse, sys

# http session
import requests


def cli_arguments():
    """
    Uses Argparse to get user input returns a Namespace object:
    Namespace(command='export', location='/tmp/', secret='glsa_.....', url='https://grafana....', tag=None, out_format='pickle')
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
        "--format", dest="format", help="the dump format: pickle of json"
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
        "--output",
        dest="out_format",
        default="pickle",
        help="Output format: json pickle(default)",
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

    grafana_backup = {"folders": folders, "dashboards": dashboards, "datasources": datasources, "alertrules": alertrules }

