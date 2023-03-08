# Grafana-DevOps-deployment-tool
A Python tool to backup and deploy Grafana on-prem development server to production server
We created the tools `mass-export.py` and `mass-import.py` to backup or import grafana folders, dashboards and datasources.

## Key Features

* Create Backup login to the server you want to backup, with session cookie that looks like his: `grafana_session=b5565889382af2700009d41ecc0004c0`
  - Instantly see what your Markdown documents look like in HTML as you create them.
* Sync Scrolling


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










## Download

You can [download](https://github.com/amitmerchant1990/electron-markdownify/releases/tag/v1.2.0) the latest installable version of Markdownify for Windows, macOS and Linux.

## Credits

This software uses the following open source packages:

- [Python](http://electron.atom.io/)
- [HCS COMPANY B.V] - for creating the Grafana deployment tool 

## You may also like...

- [Grafana](https://www.grafana.com) - Grafana homepage
- [Grafana Github](https://github.com/grafana/grafana) - Grafana github community

## License

MIT

---

> [amitmerchant.com](https://www.amitmerchant.com) &nbsp;&middot;&nbsp;
> GitHub [@amitmerchant1990](https://github.com/amitmerchant1990) &nbsp;&middot;&nbsp;
> Twitter [@amit_merchant](https://twitter.com/amit_merchant)

