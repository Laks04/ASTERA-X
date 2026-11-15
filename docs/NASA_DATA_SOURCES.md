# NASA data sources

**Challenge:** Abandoned but not Forgotten: Storytelling about NASA's Discarded Equipment on the Moon and Mars (Space Apps 2026).
Registry statuses: `listed_verified`, `listed_unverified`, `not_listed_verified`, `listing_unknown`.

## Official Resources listing — manually supplied by project owner

On **2026-11-15**, the project owner pasted the contents of the official challenge Resources section into the ASTERA development conversation. The pasted list explicitly identifies NSSDCA and the mission-specific NASA pages below. The registry seed records these 14 supplied entries as `listed_verified`, with `listing_checked_at=2026-11-15` and a note pointing to the official Resources URL:

https://www.spaceappschallenge.org/2026/challenges/nasas-discarded-equipment-storytelling/?tab=resources

This is a manual confirmation based on the owner's supplied Resources content, not an independently captured browser screenshot. The NSSDCA source is the first qualifying data source to integrate meaningfully. Merely storing its URL is not meaningful integration; retrieve source records, preserve provenance, normalize supported fields and use them in the archive after human review.

### Challenge-listed sources recorded in the registry

| Resource | Official URL | Registry slug |
|---|---|---|
| NASA Space Science Data Coordinated Archive (NSSDCA) | https://nssdc.gsfc.nasa.gov/ | `nssdca-nmc` |
| Apollo Lunar Modules | https://nssdc.gsfc.nasa.gov/nmc/spacecraft/display.action?id=1969-059C | `nssdca-apollo-lm` |
| Lunar Roving Vehicles | https://nssdc.gsfc.nasa.gov/nmc/spacecraft/display.action?id=1971-063C | `nssdca-lrv` |
| ALSEP Scientific Packages | https://nssdc.gsfc.nasa.gov/nmc/spacecraft/display.action?id=1969-099C | `nssdca-alsep` |
| Surveyor 3 | https://science.nasa.gov/mission/surveyor-3/ | `nasa-surveyor-3` |
| Mars Pathfinder / Sojourner | https://science.nasa.gov/mission/mars-pathfinder/ | `nasa-mars-pathfinder` |
| Spirit & Opportunity | https://science.nasa.gov/mission/mars-exploration-rovers-spirit-and-opportunity/ | `nasa-mer` (URL stored as supplied) |
| Viking 1 & 2 | https://science.nasa.gov/mission/viking-1/ | `nasa-viking-1` |
| Phoenix & InSight | https://science.nasa.gov/mission/insight/ | `nasa-insight` |
| Dawn | https://science.nasa.gov/mission/dawn/ | `nasa-dawn` |
| NEAR Shoemaker | https://science.nasa.gov/mission/near-shoemaker/ | `nasa-near-shoemaker` |
| Pioneer 10 & 11 | https://science.nasa.gov/mission/pioneer-10/ | `nasa-pioneer-10` |
| Ingenuity | https://science.nasa.gov/mission/mars-2020-perseverance/ingenuity-mars-helicopter/ | `nasa-ingenuity` |
| Kepler | https://science.nasa.gov/mission/kepler/ | `nasa-kepler` |

### Supplemental sources

| Source | URL | Listing status | Intended use |
|---|---|---|---|
| Catalogue of Manmade Material on the Moon | https://www.nasa.gov/wp-content/uploads/2024/02/final-catalogue-of-manmade-material-on-the-moon.pdf | `not_listed_verified` based on supplied list | Supplementary site-level lunar inventory; full original-PDF ingestion and review still outstanding |
| LROC image archive | https://lroc.im-ldi.com/images | `listing_unknown` | Lunar orbital imagery; third-party site use terms must be followed |
| Apollo Lunar Surface / Flight Journals | https://www.nasa.gov/history/alsj-and-afj/ | `listing_unknown` | Mission transcripts and historical context |
| PDS Geosciences Apollo | https://pds-geosciences.wustl.edu/missions/apollo/ | `listing_unknown` | ALSEP science data |
| HiRISE PDS | https://hirise-pds.lpl.arizona.edu/PDS/ | `listing_unknown` | Mars orbital imagery |
| PDS Orbital Data Explorer | https://oderest.rsl.wustl.edu/live2/ | `listing_unknown` | Planetary image/product discovery |

### NSSDCA source retrieval adapter

`services/api/app/integrations/nasa/nssdca.py` provides an allowlisted HTTPS fetcher for `nssdc.gsfc.nasa.gov` and `science.nasa.gov`. Run `python scripts/inspect_challenge_mission_sources.py` from `services/api` to save source-page snapshots, hashes, retrieval metadata and extracted text under `services/api/data/nasa_resource_snapshots/`. These snapshots are evidence for normalization and human review; they are **not yet normalized Mission/Artifact rows**.

NASA does not endorse ASTERA. For non-U.S. Government websites, comply with each provider's own data-use terms. Check image licensing and attribution before redistributing content.

## Data-quality findings in the Moon catalogue
- **Ranger 9:** printed latitude 112.828 °N is impossible. Stored as printed, flagged `invalid_coordinate_needs_review`; approval requires a reviewer's correction or discarding the location.
- **Luna 10 to 13, 19, 20:** names and coordinates sit on separate lines in the extracted text. Coordinates are attached to the last preceding name and flagged `layout_inferred_association`; other names are stored with no location. Verify on the PDF page.
- Entries printed as UNKNOWN or Crashed, or with only a region, are stored without coordinates and flagged.
- A stray space in "- 46.2" (SMART-1) is read as -46.2, noted, raw text kept.
- Entries with no location text at all (e.g. some subsatellites) are not yet captured; per-item inventory lines are not ingested.
