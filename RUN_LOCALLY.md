# Run Beacon Neighborhood Action Desk locally

This guide stands up the app on your own computer (Mac, Windows, or Linux) from the command line. It takes about 5 minutes. The cleaned data is already in this repo, so you do **not** need API keys, a database, or the raw data files to run the app.

## 1. Install the prerequisites (one time)

| Tool | Version | Check it | Get it |
|---|---|---|---|
| Git | any recent | `git --version` | https://git-scm.com/downloads |
| Node.js (includes npm) | 20.19+ or 22.12+ (LTS recommended) | `node -v` | https://nodejs.org |
| Python 3 | 3.9+ (standard library only, no packages) | `python3 --version` (Windows: `python --version`) | https://www.python.org/downloads |

Python is needed because `npm start` first runs `app/prepare_data.py`, which copies the cleaned data from `output/` into the app.

## 2. Get the code

```bash
git clone https://github.com/whatsgooglyKP/BEACON-FAAB.v3.git
cd BEACON-FAAB.v3/app
```

## 3. Install and start

### Mac or Linux

```bash
npm install
npm start
```

### Windows (PowerShell or Command Prompt)

```bash
npm install
npm start
```

If `npm start` fails with `'python3' is not recognized` (common on Windows), run the two steps it does by hand instead:

```bash
python prepare_data.py
npx vite --host 0.0.0.0 --port 5173
```

## 4. Open the app

When the terminal shows `Local: http://localhost:5173/`, open:

- Full app: http://localhost:5173
- Apopka demo view (used in the demo video): http://localhost:5173/?tract=12095017703

For the demo, set the access lens to **Straight-line** and leave **conservative mode off**.

To stop the server, press `Ctrl + C` in the terminal. To start it again later, run `npm start` from the `app` folder.

## Optional: tests and a production build

```bash
npm test        # builds the app and runs the 35 app tests
npm run build   # writes a static site to app/dist
npm run preview # serves app/dist at http://localhost:5174
```

## Troubleshooting

| Problem | Fix |
|---|---|
| `Vite requires Node.js version 20.19+ or 22.12+` | Update Node.js from https://nodejs.org, open a new terminal, then rerun `npm install`. |
| `'python3' is not recognized` | Use the Windows steps above, or install Python and tick "Add python.exe to PATH". |
| `Port 5173 is already in use` | Close the other terminal running the app, or run `npx vite --port 5175` and open that port. |
| `SNAP model is stale` | The data in `output/` was changed. Rerun the model (see the main README, "Pipeline and model") or re-clone the repo. |
| `npm install` errors after a Node upgrade | Delete the `node_modules` folder and run `npm install` again. |

## Rerunning the data pipeline (not needed for the demo)

Only needed if you want to rebuild the cleaned data from raw sources. See the "Pipeline and model" and "Data sources and restoring inputs" sections of `README.md`.
