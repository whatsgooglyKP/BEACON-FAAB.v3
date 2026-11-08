# Run Beacon Neighborhood Action Desk locally

Step-by-step setup for running the app on your own computer. The cleaned data is already in this repo, so you do **not** need API keys, a database, or the raw data files. It takes about 5–10 minutes the first time.

- [Windows (PowerShell)](#windows-powershell): start here if you're on Windows
- [Mac or Linux (Terminal)](#mac-or-linux-terminal)
- [Troubleshooting](#troubleshooting)

---

## Windows (PowerShell)

Open **PowerShell**: press the Windows key, type `PowerShell`, and press Enter. Paste each block below and press Enter.

### 1. Install the tools (one time)

You need Git, Node.js (20.19+ or 22.12+), and Python 3. The quickest way is `winget`, which is built into Windows 10 and 11:

```powershell
winget install --id Git.Git -e
winget install --id OpenJS.NodeJS.LTS -e
winget install --id Python.Python.3.12 -e
```

Or download the installers instead: [Git](https://git-scm.com/download/win), [Node.js LTS](https://nodejs.org), [Python](https://www.python.org/downloads/windows/). When installing Python this way, tick **"Add python.exe to PATH"**.

**Close PowerShell and open a new window** so it picks up the new tools, then check them:

```powershell
git --version
node -v
npm -v
python --version
```

`node -v` should show `v20.19` or higher, or `v22.12` or higher. If `python --version` opens the Microsoft Store instead, try `py --version`. Either one works.

### 2. Allow npm to run in PowerShell (one time)

Windows blocks npm's PowerShell script by default (the error says *"running scripts is disabled on this system"*). Allow scripts for your user only:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Type `Y` if asked. If you'd rather not change this, type `npm.cmd` everywhere this guide says `npm`.

### 3. Download the code

This puts the project in your Documents folder:

```powershell
cd $HOME\Documents
git clone https://github.com/whatsgooglyKP/BEACON-FAAB.v3.git
cd BEACON-FAAB.v3\app
```

### 4. Install and start

```powershell
npm install
npm start
```

`npm start` prepares the data with Python (it finds `python3`, `python`, or `py` on its own) and then starts the web server. If Windows Firewall asks about Node.js, you can click **Cancel**. The app still works on your own computer.

### 5. Open the app

When PowerShell shows `Local: http://localhost:5173/`, open the app in your browser, or run:

```powershell
Start-Process "http://localhost:5173/?tract=12095017703"
```

- Full app: http://localhost:5173
- Apopka demo view: http://localhost:5173/?tract=12095017703. For the demo, turn **Straight-line** on and leave **conservative mode** off.

**To stop the app**, click in the PowerShell window and press `Ctrl + C`.
**To run it again later**, open PowerShell and run:

```powershell
cd $HOME\Documents\BEACON-FAAB.v3\app
npm start
```

**To get the latest changes** from GitHub:

```powershell
cd $HOME\Documents\BEACON-FAAB.v3
git pull
cd app
npm install
```

---

## Mac or Linux (Terminal)

Install [Git](https://git-scm.com/downloads), [Node.js](https://nodejs.org) 20.19+ or 22.12+, and Python 3 (already on most Macs; otherwise [python.org](https://www.python.org/downloads/)). Then:

```bash
git clone https://github.com/whatsgooglyKP/BEACON-FAAB.v3.git
cd BEACON-FAAB.v3/app
npm install
npm start
```

Open http://localhost:5173 (or http://localhost:5173/?tract=12095017703 for the Apopka demo). Press `Ctrl + C` to stop.

---

## Optional: tests and a production build

Run these from the `app` folder. They're the same on Windows and Mac.

```
npm test         # builds the app and runs the 35 app tests
npm run build    # writes a static site to app\dist
npm run preview  # serves the built site at http://localhost:5174
```

---

## Troubleshooting

| What you see | Fix |
|---|---|
| `running scripts is disabled on this system` | Do Windows step 2, or use `npm.cmd install` and `npm.cmd start`. |
| `git`, `node`, or `npm` *is not recognized* | Close PowerShell, open a new window, and try again. If it still fails, reinstall that tool. |
| `Python 3 was not found` | Install Python (Windows step 1), tick "Add python.exe to PATH", and open a new PowerShell window. |
| `python` opens the Microsoft Store | Install Python from python.org or winget. You can also turn off the store alias in Settings, Apps, Advanced app settings, App execution aliases. |
| `Vite requires Node.js version 20.19+ or 22.12+` | Update Node: `winget upgrade --id OpenJS.NodeJS.LTS -e`, open a new window, delete the `node_modules` folder, and run `npm install` again. |
| `Port 5173 is already in use` | Another copy is already running, so close that window. Or run `npx vite --port 5175` and open http://localhost:5175. |
| `SNAP model is stale` | Files in `output\` were changed. Run `git checkout -- ..\output` from the `app` folder, or clone the repo again. |
| `npm install` fails | Delete the `node_modules` folder (`Remove-Item -Recurse -Force node_modules`) and run `npm install` again. |

## Rebuilding the data (not needed for the demo)

Only needed to regenerate the cleaned data from raw sources. See "Pipeline and model" and "Data sources and restoring inputs" in [README.md](README.md). On Windows, use `.venv\Scripts\python` wherever those steps say `.venv/bin/python`.
