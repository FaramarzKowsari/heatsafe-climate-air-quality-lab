# Publishing and Archiving the Repository

## GitHub

The canonical repository is:

```text
https://github.com/FaramarzKowsari/heatsafe-climate-air-quality-lab
```

Recommended topics:

```text
air-quality, climate-change, heatwave, extreme-heat, climate-resilience,
urban-heat-island, pm25, wildfire-smoke, environmental-ai, climate-data,
open-data, geospatial-analysis, time-series-forecasting, remote-sensing,
explainable-ai, conformal-prediction, research-software, reproducibility,
copernicus, noaa, nasa, europe, turkiye
```

## GitHub Pages

The included workflow deploys `docs/site` through GitHub Actions.

## Scientific release checklist

Before a tagged release:

1. run the full quality gate;
2. freeze configurations and checksums;
3. generate experiment manifests;
4. update data cards and model cards;
5. update limitations and changelog;
6. verify citation metadata;
7. confirm that no secret or restricted dataset is included;
8. archive only a reviewed release.

## Zenodo

Connect the GitHub repository to Zenodo, enable it and archive a reviewed GitHub release. Do not display a DOI badge until Zenodo has issued the DOI.

Dataset and software artifacts should receive separate records when their versioning, licenses or reuse patterns differ.
