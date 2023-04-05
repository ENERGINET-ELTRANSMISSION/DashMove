#!/bin/env python3

import argparse, sys

# create the top-level parser
parser = argparse.ArgumentParser()

# create sub-parsers for the sub-commands
subparsers = parser.add_subparsers(dest='command', required=True)

## import command argument parsing
import_parser = subparsers.add_parser('import', help='Grafana importer')
import_parser.add_argument("--location", dest="location", required=True, help="The location of the dump")
import_parser.add_argument("--secret", dest="secret", required=True, help="grafana_session=## cookie, glsa_## Service account token or apikey")
import_parser.add_argument("--url", dest="url", required=True, help="The grafana URL: https://grafana.local")
import_parser.add_argument("--format", dest="format", help="the dump format: pickle of json")
import_parser.add_argument("--override", default=False, dest="override", help="remove everything before importing", action="store_true")

## export command argument parsing
export_parser = subparsers.add_parser('export', help='Grafana exporter')
export_parser.add_argument("--location", dest="location", required=True, help="The location to save the dump, file or folder. (pointing to a folder will automaticly set a time and url specific name)")
export_parser.add_argument("--secret", dest="secret", required=True, help="grafana_session=## cookie, glsa_## Service account token or apikey")
export_parser.add_argument("--url", dest="url", required=True, help="The grafana URL: https://grafana.local")
export_parser.add_argument("--tag", dest="tag", help="The tag you want to include in your dump")
export_parser.add_argument("--output", dest="out_format", default="pickle", help="Output format: json pickle(default)")

# parse the command-line arguments and show help also for subcommands if argument list < 2
args = parser.parse_args(args=None if sys.argv[2:] else sys.argv[1:2] + ['--help'])

