# Google Search Console Setup

## Property type

Use a **URL-prefix property** because the project is hosted under a GitHub
Pages path rather than at the hostname root.

Property URL:

```text
https://faramarzkowsari.github.io/heatsafe-climate-air-quality-lab/
```

Keep the trailing slash.

## Ownership verification

Recommended method: **HTML file upload**.

1. In Search Console, add the URL-prefix property above.
2. Choose HTML file verification.
3. Download the unique `googlexxxxxxxxxxxxxxxx.html` file.
4. Run `INSTALL_GOOGLE_VERIFICATION_FILE_10.cmd`.
5. Select the downloaded file.
6. Commit and push the new file in `docs/site/`.
7. Wait for GitHub Pages deployment.
8. Open the public verification URL in an incognito window.
9. Return to Search Console and click Verify.
10. Keep the verification file in the repository permanently.

## Submit the sitemap

After verification, open **Indexing → Sitemaps**.

Submit:

```text
sitemap.xml
```

Canonical sitemap URL:

```text
https://faramarzkowsari.github.io/heatsafe-climate-air-quality-lab/sitemap.xml
```

The sitemap is also declared in `robots.txt`.

## Request indexing for priority URLs

Use URL Inspection and request indexing for these pages first:

```text
https://faramarzkowsari.github.io/heatsafe-climate-air-quality-lab/
https://faramarzkowsari.github.io/heatsafe-climate-air-quality-lab/dataset/epa-pm25-san-diego-v0-1-0/
https://faramarzkowsari.github.io/heatsafe-climate-air-quality-lab/public-guide/
https://faramarzkowsari.github.io/heatsafe-climate-air-quality-lab/first-real-experiment/
https://faramarzkowsari.github.io/heatsafe-climate-air-quality-lab/release-review/doi-finalization/
https://faramarzkowsari.github.io/heatsafe-climate-air-quality-lab/about-author/
```

## Check after deployment

Run:

```text
VERIFY_LIVE_DISCOVERY_10.cmd
```

Then test:

- Rich Results Test for the dataset landing page;
- URL Inspection for the homepage and dataset page;
- Page indexing report;
- Sitemaps report;
- HTTPS report;
- Core Web Vitals after sufficient field data exists.

## Important limits

A sitemap and an indexing request are discovery signals, not guarantees of
ranking or immediate indexing. Keep canonical URLs stable, preserve the
verification file, and avoid duplicate or thin pages.
