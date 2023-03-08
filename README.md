# Grafana-DevOps-deployment-tool
A Python tool to backup and deploy Grafana on-prem development server to production server


## Key Features

* Create Backup login to the server you want to backup, with session cookie that looks like his: `grafana_session=b5565889382af2700009d41ecc0004c0`
  - Instantly see what your Markdown documents look like in HTML as you create them.
* Sync Scrolling


## How to get Cookie

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





## How To Use

To clone and run this application, you'll need [Git](https://git-scm.com) and [Node.js](https://nodejs.org/en/download/) (which comes with [npm](http://npmjs.com)) installed on your computer. From your command line:

```bash
# Clone this repository
$ git clone https://github.com/amitmerchant1990/electron-markdownify

# Go into the repository
$ cd electron-markdownify

# Install dependencies
$ npm install

# Run the app
$ npm start
```

> **Note**
> If you're using Linux Bash for Windows, [see this guide](https://www.howtogeek.com/261575/how-to-run-graphical-linux-desktop-applications-from-windows-10s-bash-shell/) or use `node` from the command prompt.


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

