from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.nasa import DataSource

MOON_CATALOGUE_SLUG = "nasa-history-moon-catalogue"
MANUAL = "Challenge Resources listing not confirmed. Check the official 2026 challenge Resources tab."
CHALLENGE_CHECKED_AT = datetime(2026, 11, 15, tzinfo=timezone.utc)
CHALLENGE_PAGE = "https://www.spaceappschallenge.org/2026/challenges/nasas-discarded-equipment-storytelling/?tab=resources"

# Challenge-listed entries below are based on the official Resources content supplied by the project owner.
# Supplemental entries remain listing_unknown; a CHECK constraint requires a check date for verified states.
SEED = [
    dict(slug=MOON_CATALOGUE_SLUG, name="Catalogue of Manmade Material on the Moon", category="historical_catalogue",
         description="NASA History Program Office catalogue of human-made objects on the lunar surface, by mission, with printed locations.",
         official_url="https://www.nasa.gov/wp-content/uploads/2024/02/final-catalogue-of-manmade-material-on-the-moon.pdf",
         access_method="HTTP download of a PDF", data_format="PDF (22 pages, text layer)",
         retrieval_method="app.ingestion.pdf (download, validate, pdftotext per page) then app.ingestion.moon_catalogue",
         attribution="NASA History Program Office", license_note="Check NASA media usage guidelines before redistributing."),
    dict(slug="lroc-images", name="LROC image archive", category="orbital_imagery", official_url="https://lroc.im-ldi.com/images",
         description="Lunar Reconnaissance Orbiter Camera imagery of landing sites.", data_format="web catalogue"),
    dict(slug="alsj-afj", name="Apollo Lunar Surface Journal / Apollo Flight Journal", category="historical_journal",
         official_url="https://www.nasa.gov/history/alsj-and-afj/", description="Transcripts and commentary on Apollo surface operations.", data_format="HTML"),
    dict(slug="pds-apollo-alsep", name="PDS Geosciences: Apollo mission data (ALSEP)", category="instrument_data",
         official_url="https://pds-geosciences.wustl.edu/missions/apollo/", description="Data from Apollo Lunar Surface Experiments Packages.", data_format="PDS archives"),
    dict(slug="hirise-pds", name="HiRISE PDS archive (Mars Reconnaissance Orbiter)", category="orbital_imagery",
         official_url="https://hirise-pds.lpl.arizona.edu/PDS/", description="High-resolution Mars orbital imagery products.", data_format="PDS image products"),
    dict(slug="pds-ode-rest", name="PDS Orbital Data Explorer REST service", category="query_api",
         official_url="https://oderest.rsl.wustl.edu/live2/", description="Query interface for planetary orbital data products.", data_format="REST"),
    dict(slug="nssdca-nmc", name="NASA Space Science Data Coordinated Archive (NSSDCA)", category="mission_catalogue",
         official_url="https://nssdc.gsfc.nasa.gov/", description="NASA's publicly available spacecraft and instrument catalogue, including mission parameters and operational/final-state information.", data_format="web catalogue", challenge_listing_status="listed_verified"),
    dict(slug="nssdca-apollo-lm", name="NSSDCA: Apollo Lunar Modules", category="mission_record", official_url="https://nssdc.gsfc.nasa.gov/nmc/spacecraft/display.action?id=1969-059C", description="Official NSSDCA Apollo Lunar Module record.", data_format="HTML", challenge_listing_status="listed_verified"),
    dict(slug="nssdca-lrv", name="NSSDCA: Lunar Roving Vehicles", category="mission_record", official_url="https://nssdc.gsfc.nasa.gov/nmc/spacecraft/display.action?id=1971-063C", description="Official NSSDCA Lunar Roving Vehicle record.", data_format="HTML", challenge_listing_status="listed_verified"),
    dict(slug="nssdca-alsep", name="NSSDCA: ALSEP Scientific Packages", category="mission_record", official_url="https://nssdc.gsfc.nasa.gov/nmc/spacecraft/display.action?id=1969-099C", description="Official NSSDCA Apollo Lunar Surface Experiments Package record.", data_format="HTML", challenge_listing_status="listed_verified"),
    dict(slug="nasa-surveyor-3", name="NASA Science: Surveyor 3", category="mission_record", official_url="https://science.nasa.gov/mission/surveyor-3/", description="NASA mission page for Surveyor 3.", data_format="HTML", challenge_listing_status="listed_verified"),
    dict(slug="nasa-mars-pathfinder", name="NASA Science: Mars Pathfinder and Sojourner", category="mission_record", official_url="https://science.nasa.gov/mission/mars-pathfinder/", description="NASA mission page for Mars Pathfinder and Sojourner.", data_format="HTML", challenge_listing_status="listed_verified"),
    dict(slug="nasa-mer", name="NASA Science: Mars Exploration Rovers", category="mission_record", official_url="https://science.nasa.gov/mission/mars-exploration-rovers-spirit-and-opportunity/", description="NASA mission page for Spirit and Opportunity.", data_format="HTML", challenge_listing_status="listed_verified"),
    dict(slug="nasa-viking-1", name="NASA Science: Viking 1", category="mission_record", official_url="https://science.nasa.gov/mission/viking-1/", description="NASA mission page for the Viking landers.", data_format="HTML", challenge_listing_status="listed_verified"),
    dict(slug="nasa-insight", name="NASA Science: InSight", category="mission_record", official_url="https://science.nasa.gov/mission/insight/", description="NASA mission page for InSight; supplied challenge resource also references Phoenix.", data_format="HTML", challenge_listing_status="listed_verified"),
    dict(slug="nasa-dawn", name="NASA Science: Dawn", category="mission_record", official_url="https://science.nasa.gov/mission/dawn/", description="NASA mission page for Dawn.", data_format="HTML", challenge_listing_status="listed_verified"),
    dict(slug="nasa-near-shoemaker", name="NASA Science: NEAR Shoemaker", category="mission_record", official_url="https://science.nasa.gov/mission/near-shoemaker/", description="NASA mission page for NEAR Shoemaker.", data_format="HTML", challenge_listing_status="listed_verified"),
    dict(slug="nasa-pioneer-10", name="NASA Science: Pioneer 10", category="mission_record", official_url="https://science.nasa.gov/mission/pioneer-10/", description="NASA mission page for Pioneer 10 and the supplied Pioneer 10/11 resource.", data_format="HTML", challenge_listing_status="listed_verified"),
    dict(slug="nasa-ingenuity", name="NASA Science: Ingenuity Mars Helicopter", category="mission_record", official_url="https://science.nasa.gov/mission/mars-2020-perseverance/ingenuity-mars-helicopter/", description="NASA mission page for Ingenuity.", data_format="HTML", challenge_listing_status="listed_verified"),
    dict(slug="nasa-kepler", name="NASA Science: Kepler", category="mission_record", official_url="https://science.nasa.gov/mission/kepler/", description="NASA mission page for Kepler.", data_format="HTML", challenge_listing_status="listed_verified"),
]


def seed_sources(db: Session) -> None:
    """Seed source metadata; challenge listing is verified only for the user-supplied official list."""
    for original in SEED:
        row = dict(original)
        slug = row["slug"]
        listed = row.pop("challenge_listing_status", None) == "listed_verified"
        existing = db.scalar(select(DataSource).where(DataSource.slug == slug))
        if existing is None:
            existing = DataSource(agency="NASA", challenge_listing_status="listing_unknown", review_notes=MANUAL, **row)
            db.add(existing)
        if listed:
            existing.challenge_listing_status = "listed_verified"
            existing.listing_checked_at = CHALLENGE_CHECKED_AT
            existing.review_notes = f"Manually confirmed from the official challenge Resources content supplied by the project owner on 2026-11-15. Resources page: {CHALLENGE_PAGE}"
        elif slug == MOON_CATALOGUE_SLUG:
            existing.challenge_listing_status = "not_listed_verified"
            existing.listing_checked_at = CHALLENGE_CHECKED_AT
            existing.review_notes = f"Not present in the official Resources content supplied by the project owner on 2026-11-15. Resources page: {CHALLENGE_PAGE}"
    db.commit()
