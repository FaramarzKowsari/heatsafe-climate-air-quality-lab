# Publishing the Repository

The build environment verified the connected GitHub identity as `FaramarzKowsari`, but the installed GitHub connector does not expose repository creation. The repository was therefore prepared in **BUILD_ONLY** mode.

## GitHub CLI

From the directory containing this repository:

```bash
gh auth login
gh repo create FaramarzKowsari/heatsafe-climate-air-quality-lab \
  --public \
  --description "Open-data AI for heatwaves, air quality, wildfire smoke, urban heat and home resilience across Europe, North America and Türkiye" \
  --source . \
  --remote origin \
  --push
```

Then add the recommended topics in GitHub repository settings:

```text
air-quality, climate-change, heatwave, extreme-heat, climate-resilience,
urban-heat-island, pm25, wildfire-smoke, environmental-ai, climate-data,
open-data, geospatial-analysis, time-series-forecasting, remote-sensing,
explainable-ai, copernicus, noaa, nasa, europe, turkiye
```

## Manual Git publishing

Create an empty public repository named `heatsafe-climate-air-quality-lab` under `FaramarzKowsari`, then run:

```bash
git remote add origin git@github.com:FaramarzKowsari/heatsafe-climate-air-quality-lab.git
git branch -M main
git push -u origin main
```

## GitHub Pages

After the first push, enable **Settings → Pages → Source: GitHub Actions**. The included `pages.yml` workflow deploys `docs/site`.

## Zenodo

Connect the published GitHub repository to Zenodo, enable it, create a reviewed GitHub release, and allow Zenodo to archive that release. Do not place a DOI badge in the README until Zenodo has actually issued the DOI.

## Book identifiers

Add a verified Google Books purchase URL and book DOI only after they exist. Do not invent or guess them.
