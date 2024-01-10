# DashMove: Grafana Dashboard Migration Tool
>DashMove is a command-line interface (CLI) tool for exporting and importing data from Grafana. 

## What to expect
This tool allows users to migrate:
- Datasources
- Folders
- Dashboards
- Alerts

[![asciicast](https://asciinema.org/a/G9Y51DIuxDxfeKcabfzdCrRch.svg)](https://asciinema.org/a/G9Y51DIuxDxfeKcabfzdCrRch)

## Installation
At the moment there are no formal installation methods.
To use DashMove you just need the [dash-move.py](dash-move.py) file, Python 3 and [requests](https://requests.readthedocs.io/en/latest/)
I chose to keep external packages to a minimum to be abe to run this anywhere.

### Quick and dirty I need this now installation method
```bash
sudo curl -o /usr/local/bin/dm https://raw.githubusercontent.com/ENERGINET-ELTRANSMISSION/DashMove/main/dash-move.py
sudo chmod +x /usr/local/bin/dm
dm
```

## Usage
To use DashMove, run the dash-move.py file the help wil guide you in getting the correct arguments.

### main help
```txt
$ dm
usage: dm [-h] {import,export} ...

positional arguments:
  {import,export}
    import         Grafana importer
    export         Grafana exporter

options:
  -h, --help       show this help message and exit
```

### Import Command
The import command imports data from your machine to a Grafana instance. Here are the available arguments:

```txt
$ dm import
usage: dm import [-h] --location LOCATION --secret SECRET --url URL [--format DATA_FORMAT] [--override]

options:
  -h, --help            show this help message and exit
  --location LOCATION   The location of the dump
  --secret SECRET       grafana_session=## cookie, glsa_## Service account token or apikey
  --url URL             The grafana URL: https://grafana.local
  --format DATA_FORMAT  Dump format: json pickle(default)
  --override            remove everything before importing
```

### Export Command
The export command exports data from a Grafana instance and saves it to a local file. Here are the available arguments:

```txt
$ dm export
usage: dm export [-h] --location LOCATION --secret SECRET --url URL [--tag TAG] [--format DATA_FORMAT]

options:
  -h, --help            show this help message and exit
  --location LOCATION   The location to save the dump, file or folder. (pointing to a folder will automaticly set a time and url specific name)
  --secret SECRET       grafana_session=## cookie, glsa_## Service account token or apikey
  --url URL             The grafana URL: https://grafana.local
  --tag TAG             The tag you want to include in your dump
  --format DATA_FORMAT  Dump format: json pickle(default)
```

## Download grafana

You can [download](https://grafana.com/grafana/download) the latest installable version of Grafana for Windows, macOS, Linux, ARM and Docker.

## Credits

- **[HCS COMPANY B.V](https://www.hcs-company.com/)** - for creating this Migration tool 


## You may also like...

- [Grafana](https://www.grafana.com) - Grafana homepage
- [Grafana Github](https://github.com/grafana/grafana) - Grafana github community
- [Energinet](https://www.energinet.dk) - Energinet homepage

## License

Apache 2.0
