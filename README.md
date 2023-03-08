# Grafana-DevOps-deployment-tool
A Python tool to backup and deploy Grafana on-prem development server to production server
We created the tools `mass-export.py` and `mass-import.py` to backup or import grafana folders, dashboards and datasources.


[![asciicast](https://asciinema.org/a/FlzX53RxfgBrp4qncM7iEekLj.svg)](https://asciinema.org/a/FlzX53RxfgBrp4qncM7iEekLj)


## Key Features

* [mass-export.py] Create Backup login to the server you want to backup, with session cookie that looks like his: `grafana_session=b5565889382af2700009d41ecc0004c0`
  - Instantly see count of exported folders, dashboard and datasources. 
  
* [mass-import.py] Import folders, dashboards and datasources  
  - Only import dashboards marked with tag value "Production"
  
### How to get Cookie

1. Open your browser and navigate to the website for which you want to copy the session cookie.
2. Right-click on an empty space on the webpage and select "Inspect" or "Inspect Element" from the context menu.
3. This will open the developer tools.
4. Click on the "Network" tab in the developer tools.
5. Refresh the page to capture the network requests.
6. Locate the network request for the website and click on it.
7. In the Headers tab, scroll down to "Request Headers"
8. Locate the "Cookie" field and you can find the cookies values
9. Right-click on the cookie value and select "Copy value"


## Grafana Backup Script `mass-export.py`
This script is designed to help you export folders, dashboards, and data sources from a Grafana instance. It allows you to save the exported data in a specified location, and also allows you to only include dashboards with a specific tag in the exported data. The data can be exported in either JSON or Pickle format.

### Usage
```
python mass_migrate/mass-export.py --location <dump_file> --url <grafana_url> --cookie <grafana_session> [--output <out_format> --tag <tag>]
```
### Arguments
```
--location: The location to save the exported data.
--cookie: The cookie for the Grafana session. This can be found in your browser.
--url: The URL of the Grafana instance you wish to export data from.
--tag: The tag you want to include in the exported data.
--output: The format of the exported data. Options are json or pickle (default).
-h, --help: Show the help message and exit.
```

### Example
```
python mass_migrate/mass-export.py --location /home/user/grafana-backup/dump.pkl --url https://grafana.local --cookie grafana_session=8757ccea39b47f00259be3e2edb342bb --output pickle --tag Production
```
This command exports the data from the Grafana instance at `https://grafana.local` with the session cookie `grafana_session=8757ccea39b47f00259be3e2edb342bb`, saves the data in a file called `dump.pkl` in the directory `/home/user/grafana-backup/`, and includes the tag `Production` in the exported data. The data is exported in the `Pickle` format.

> Note that this is an example of how to run the script, the url and cookie should be replaced with your actual cookie and url.


## Grafana Importer Script `mass-import.py`
A python script to import folders, dashboards and data sources to a Grafana instance.

### Usage
```
python mass_migrate/mass-import.py --location <dump_file> --cookie <grafana_session> --url <grafana_url>
```

### Arguments
```
--location: The location of the dump file.
--cookie: grafana_session cookie value. You can find it in your browser.
--url: The Grafana URL, e.g. https://grafana.local.
--format: the dump format: pickle of json
-h, --help: Show the help message and exit.
```

### Example
```
python mass_migrate/mass-import.py --location a0505p01-22-12-20/dump.pkl --cookie grafana_session=3587f39a752d3abe118b88bfc17d6ce8 --url "http://my-grafana.local:3000"
```
This command imports the dump file located at `a0505p01-22-12-20/dump.pkl` to the Grafana instance at `http://my-grafana.local:3000` using the cookie value `grafana_session=3587f39a752d3abe118b88bfc17d6ce8`.

> Note that this is an example of how to run the script, the url and cookie should be replaced with your actual cookie and url.


## Grafana Importer Script `mass-import.py`
A python script to import folders, dashboards and data sources to a Grafana instance.

### Usage
```
python mass_migrate/mass-import.py --location <dump_file> --cookie <grafana_session> --url <grafana_url>
```

### Arguments
```
--location: The location of the dump file.
--cookie: grafana_session cookie value. You can find it in your browser.
--url: The Grafana URL, e.g. https://grafana.local.
--format: the dump format: pickle of json
-h, --help: Show the help message and exit.
```

### Example
```
python mass_migrate/mass-import.py --location a0505p01-22-12-20/dump.pkl --cookie grafana_session=3587f39a752d3abe118b88bfc17d6ce8 --url "http://my-grafana.local:3000"
```
This command imports the dump file located at `a0505p01-22-12-20/dump.pkl` to the Grafana instance at `http://my-grafana.local:3000` using the cookie value `grafana_session=3587f39a752d3abe118b88bfc17d6ce8`.

> Note that this is an example of how to run the script, the url and cookie should be replaced with your actual cookie and url.

## Server config

### `custom.ini`
This file has a few modifications to tweak it to our needs.
> Path: `E:\Program Files\GrafanaLabs\grafana\conf\custom.ini`
To edit it, open a notepad as admin and browse to the file.
To apply your changes restart the grafana service from the `services.msc`


#### Date format
```
[date_formats]
# For information on what formatting patterns that are supported https://momentjs.com/docs/#/display

# Default system date format used in time range picker and other places where full time is displayed
full_date = DD-MM-YYYY HH:mm:ss

# Used by graph and other places where we only show small intervals
interval_second = HH:mm:ss
interval_minute = HH:mm
interval_hour = DD-MM HH:mm
interval_day = DD-MM
interval_month = MM-YYYY
interval_year = YYYY
```


## Install

Add Cookie viewer [Google](https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm) extensions to chrome


## Download

You can [download](https://grafana.com/grafana/download) the latest installable version of Grafana for Windows, macOS, Linux, ARM and Docker.

## Credits

- [HCS COMPANY B.V] - for creating the Grafana deployment tool 

This software uses the following open source packages:

- [Python](http://electron.atom.io/)


## You may also like...

- [Grafana](https://www.grafana.com) - Grafana homepage
- [Grafana Github](https://github.com/grafana/grafana) - Grafana github community
- [Energinet](https://www.energinet.dk) - Energinet homepage

## License

Apache 2.0

---
