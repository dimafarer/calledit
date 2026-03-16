"""One-time script to inject v3 fields into golden_dataset.json base predictions."""
import json
import sys

V3_FIELDS = {
    "base-001": {
        "expected_verification_criteria": [
            "The sun appears above the horizon in New York City on the date following the prediction date"
        ],
        "expected_verification_method": "Confirm via astronomical calculations based on Earth's rotation and NYC coordinates. Deterministic from orbital mechanics — no external data source needed."
    },
    "base-002": {
        "expected_verification_criteria": [
            "December 25, 2026 falls on a Friday according to the Gregorian calendar"
        ],
        "expected_verification_method": "Apply day-of-week algorithm or calendar arithmetic to December 25, 2026. Deterministic calculation — no external data source needed."
    },
    "base-003": {
        "expected_verification_criteria": [
            "The high temperature recorded in Central Park, NYC on the specified date is at least 70°F"
        ],
        "expected_verification_method": "Query a weather service (e.g., weather.gov, OpenWeatherMap) for Central Park high temperature on the target date. Compare against 70°F threshold."
    },
    "base-004": {
        "expected_verification_criteria": [
            "The S&P 500 closing price on the prediction date exceeds the S&P 500 closing price on the previous trading day"
        ],
        "expected_verification_method": "Query a financial data source (e.g., Yahoo Finance, Google Finance) for S&P 500 closing prices on both days. Compare the two values."
    },
    "base-005": {
        "expected_verification_criteria": [
            "Precipitation (rain) is recorded in London, UK on the date following the prediction date"
        ],
        "expected_verification_method": "Query a weather service (e.g., Met Office, OpenWeatherMap) for London precipitation data on the target date. Check for any recorded rainfall."
    },
    "base-006": {
        "expected_verification_criteria": [
            "USGS reports at least one earthquake with magnitude >= 5.0 located within the Pacific Ring of Fire region within 30 days of the prediction date"
        ],
        "expected_verification_method": "Query the USGS earthquake API (earthquake.usgs.gov) filtering for magnitude >= 5.0 and Pacific Ring of Fire coordinates within the 30-day window."
    },
    "base-007": {
        "expected_verification_criteria": [
            "The scheduled start time of the New York Yankees' next home game is after 6:00 PM Eastern Time"
        ],
        "expected_verification_method": "Query MLB schedule data (mlb.com or ESPN) for the Yankees' next home game. Check the published start time against 6:00 PM ET."
    },
    "base-008": {
        "expected_verification_criteria": [
            "The current temperature reading in Tokyo, Japan exceeds 10°C at the time of verification"
        ],
        "expected_verification_method": "Query a real-time weather service (e.g., OpenWeatherMap, weather.com) for current Tokyo temperature. Compare against 10°C threshold."
    },
    "base-009": {
        "expected_verification_criteria": [
            "The total US national debt as reported by the US Treasury exceeds $35 trillion at the time of verification"
        ],
        "expected_verification_method": "Query TreasuryDirect.gov or a financial data aggregator for the current US national debt total. Compare against $35 trillion threshold."
    },
    "base-010": {
        "expected_verification_criteria": [
            "The next full moon date (from the prediction date) falls before April 1, 2026"
        ],
        "expected_verification_method": "Calculate the next full moon date using lunar cycle algorithms (approximately 29.5-day cycle). Compare against April 1, 2026 deadline. Deterministic calculation."
    },
    "base-011": {
        "expected_verification_criteria": [
            "Python 3.13 appears as an official stable release (not beta or RC) on python.org"
        ],
        "expected_verification_method": "Check python.org/downloads/ for the Python 3.13 release listing. Confirm it is marked as a stable release, not a pre-release."
    },
    "base-012": {
        "expected_verification_criteria": [
            "The EUR/USD exchange rate exceeds 1.05 at the time of verification"
        ],
        "expected_verification_method": "Query a financial data source (e.g., xe.com, Google Finance) for the current EUR/USD spot rate. Compare against 1.05 threshold."
    },
    "base-013": {
        "expected_verification_criteria": [
            "The References section of the English Wikipedia article 'Artificial intelligence' contains more than 500 citation entries"
        ],
        "expected_verification_method": "Access the Wikipedia article for 'Artificial intelligence', navigate to the References section, and count citation entries. Alternatively, use the Wikipedia API to retrieve reference count metadata."
    },
    "base-014": {
        "expected_verification_criteria": [
            "The BTC/USD spot price exceeds $150,000 at any point before December 31, 2026 23:59 UTC"
        ],
        "expected_verification_method": "Monitor BTC/USD price via a cryptocurrency price API (CoinGecko, CoinMarketCap, or exchange API). Check periodically until the deadline. No crypto price tool currently registered — requires tool registration or manual monitoring."
    },
    "base-015": {
        "expected_verification_criteria": [
            "Flight AA1234 from JFK to LAX on March 20 arrives within the airline's on-time window (typically within 15 minutes of scheduled arrival)"
        ],
        "expected_verification_method": "Query a flight tracking service (FlightAware, FlightRadar24, or American Airlines status page) for flight AA1234 on March 20. Compare actual arrival time against scheduled arrival. No flight tracking tool currently registered — requires tool registration or manual check."
    },
    "base-016": {
        "expected_verification_criteria": [
            "Apple officially announces a new iPhone model during September 2026"
        ],
        "expected_verification_method": "After September 2026 ends, search Apple press releases and tech news for iPhone announcement during that month. Cannot verify before the window closes."
    },
    "base-017": {
        "expected_verification_criteria": [
            "The global mean surface temperature for calendar year 2026 exceeds the global mean surface temperature for calendar year 2025"
        ],
        "expected_verification_method": "After 2026 ends, query NOAA or NASA GISS for annual global mean temperature data for both years. Compare the two values. Data typically available in early 2027. No climate data API currently registered."
    },
    "base-018": {
        "expected_verification_criteria": [
            "The Dominican Republic national baseball team wins their next scheduled World Baseball Classic game"
        ],
        "expected_verification_method": "Identify the next WBC game for the Dominican Republic from the tournament schedule. After the game is played, check the official WBC results or sports news for the outcome. No dedicated sports results API currently registered — use web search after the event."
    },
    "base-019": {
        "expected_verification_criteria": [
            "Tesla (TSLA) closing price on the last trading day of March 2026 exceeds $300.00"
        ],
        "expected_verification_method": "After the last trading day of March 2026, query a financial data source (Yahoo Finance, Google Finance) for TSLA closing price on that date. Compare against $300 threshold. No stock API currently registered."
    },
    "base-020": {
        "expected_verification_criteria": [
            "The US national average price for a gallon of regular gasoline falls below $3.00 at the time of verification"
        ],
        "expected_verification_method": "Query AAA's gas price tracker (gasprices.aaa.com) or EIA data for the current US national average regular gasoline price. Compare against $3.00 threshold. No fuel price API currently registered."
    },
    "base-021": {
        "expected_verification_criteria": [
            "NASA announces at least one new exoplanet discovery attributed to the James Webb Space Telescope before the end of 2026"
        ],
        "expected_verification_method": "Search NASA press releases and the NASA Exoplanet Archive for JWST-attributed exoplanet discoveries during 2026. Confirm at least one new discovery is officially announced."
    },
    "base-022": {
        "expected_verification_criteria": [
            "Amazon order #123-4567890 shows delivery status as 'Delivered' by end of day Friday following the prediction date"
        ],
        "expected_verification_method": "Check Amazon order tracking for order #123-4567890 delivery status. Requires authenticated access to the user's Amazon account — no Amazon order API currently registered. Fallback: ask the user to check their order status."
    },
    "base-023": {
        "expected_verification_criteria": [
            "The current wait time at the nearest DMV location to the user is under 30 minutes at the time of verification"
        ],
        "expected_verification_method": "Check the state DMV's online wait time tracker for the nearest location. Many states publish real-time wait times. Requires knowing the user's location to identify the nearest DMV. No DMV API currently registered."
    },
    "base-024": {
        "expected_verification_criteria": [
            "The estimated fare for an Uber ride from the user's current location to the airport is less than $40 at the time of verification"
        ],
        "expected_verification_method": "Query the Uber price estimate API or check the Uber app for a fare estimate from the user's location to the airport. Requires knowing the user's location and destination airport. No Uber API currently registered."
    },
    "base-025": {
        "expected_verification_criteria": [
            "The National Park Service declares peak bloom for Washington DC cherry blossoms before April 10, 2026"
        ],
        "expected_verification_method": "Monitor the National Park Service's cherry blossom bloom forecast and peak bloom declaration (nps.gov/cherry). Check after the bloom period for the official peak bloom date. Web search can access NPS announcements."
    },
    "base-026": {
        "expected_verification_criteria": [
            "SpaceX conducts a Starship launch attempt before May 1, 2026"
        ],
        "expected_verification_method": "Monitor SpaceX launch schedule and news. After any launch attempt, confirm via SpaceX announcements or space news outlets. Web search can access launch news."
    },
    "base-027": {
        "expected_verification_criteria": [
            "The user reports a positive subjective experience after watching the movie they see tonight"
        ],
        "expected_verification_method": "Ask the user after the movie whether they enjoyed it. This is a subjective assessment that only the user can provide — no tool or data source can determine personal enjoyment."
    },
    "base-028": {
        "expected_verification_criteria": [
            "The user assesses their team meeting at 2pm tomorrow as having gone well"
        ],
        "expected_verification_method": "Ask the user after the meeting for their assessment. 'Going well' is a subjective judgment that only the meeting participant can evaluate — no external data source applies."
    },
    "base-029": {
        "expected_verification_criteria": [
            "Tom is observed wearing a blue shirt at work on Monday"
        ],
        "expected_verification_method": "Requires direct physical observation of Tom at his workplace on Monday. Ask the user or another observer present at Tom's workplace to confirm shirt color. No tool can remotely observe clothing."
    },
    "base-030": {
        "expected_verification_criteria": [
            "The user reports feeling happy upon waking tomorrow morning"
        ],
        "expected_verification_method": "Ask the user tomorrow morning about their emotional state. Happiness is a subjective internal experience that only the user can report — no external measurement applies."
    },
    "base-031": {
        "expected_verification_criteria": [
            "The user's soufflé maintains its risen structure after removal from the oven tonight"
        ],
        "expected_verification_method": "Requires direct physical observation of the soufflé immediately after removal from the oven. Ask the user to report the outcome. No tool can remotely observe cooking results."
    },
    "base-032": {
        "expected_verification_criteria": [
            "The user's daughter expresses positive reaction (joy, excitement, gratitude) upon receiving her birthday present"
        ],
        "expected_verification_method": "Requires direct observation of the daughter's reaction at the time of gift-giving. Ask the user to report the daughter's response. Subjective assessment of another person's emotional reaction."
    },
    "base-033": {
        "expected_verification_criteria": [
            "The user receives a promotion at their workplace during the current quarter"
        ],
        "expected_verification_method": "Ask the user at the end of the quarter whether they received a promotion. This is private employment information not accessible through any public API or data source."
    },
    "base-034": {
        "expected_verification_criteria": [
            "The user assesses the dinner they cook tonight as tasting good"
        ],
        "expected_verification_method": "Ask the user after dinner for their taste assessment. Taste is a subjective sensory experience that only the person eating can evaluate — no tool applies."
    },
    "base-035": {
        "expected_verification_criteria": [
            "The user's dog physically destroys (tears apart, breaks, renders unusable) the new toy within one hour of receiving it"
        ],
        "expected_verification_method": "Requires direct physical observation of the dog's interaction with the toy over the next hour. Ask the user to report the toy's condition after one hour. No tool can remotely observe pet behavior."
    },
    "base-036": {
        "expected_verification_criteria": [
            "The user successfully completes (beats/passes) the video game level they are attempting tonight"
        ],
        "expected_verification_method": "Ask the user after their gaming session whether they beat the level. This is a personal activity outcome that only the user can report — no external data source tracks individual gaming progress."
    },
    "base-037": {
        "expected_verification_criteria": [
            "At least 80% of the user's students achieve a passing grade on the final exam"
        ],
        "expected_verification_method": "Ask the user after grades are finalized for the pass rate. Student grades are private educational records (FERPA-protected) not accessible through any public API. The user (as instructor) has access to this data."
    },
    "base-038": {
        "expected_verification_criteria": [
            "The specified painting is sold (purchased by a buyer) during the gallery show next month"
        ],
        "expected_verification_method": "Ask the user after the gallery show whether the painting sold. Gallery sales are private commercial transactions — no public API tracks individual artwork sales at local galleries."
    },
    "base-039": {
        "expected_verification_criteria": [
            "The user's official marathon finish time on Saturday is faster than their previous personal record"
        ],
        "expected_verification_method": "After the marathon, check official race results (many marathons publish results online) for the user's finish time. Compare against their stated PR. Requires knowing the user's name and previous PR. Partially automatable if race results are published online, but PR comparison requires personal data from the user."
    },
    "base-040": {
        "expected_verification_criteria": [
            "The sun appears above the horizon on the date following the prediction date at the user's location"
        ],
        "expected_verification_method": "Confirm via astronomical calculations based on Earth's rotation. Deterministic from orbital mechanics — no external data source needed. Note: 'I bet' is framing language; the factual claim is simply that the sun will rise."
    },
    "base-041": {
        "expected_verification_criteria": [
            "The user's code compiles without errors on the first attempt"
        ],
        "expected_verification_method": "Ask the user after they attempt compilation whether it succeeded on the first try. This is a personal development activity outcome that only the user can observe in real-time."
    },
    "base-042": {
        "expected_verification_criteria": [
            "The user subjectively assesses the weekend weather as 'nice'"
        ],
        "expected_verification_method": "Ask the user after the weekend for their weather assessment. While weather data is publicly available, 'nice' is a subjective judgment — what constitutes nice weather varies by person. The prediction's intent is subjective satisfaction, not an objective weather metric."
    },
    "base-043": {
        "expected_verification_criteria": [
            "The restaurant the user is visiting tonight has a Google Maps rating of 4.0 stars or higher at the time of verification"
        ],
        "expected_verification_method": "Search Google Maps for the restaurant (requires knowing which restaurant). Check the star rating. Google Maps ratings are publicly accessible via web search. However, the specific restaurant is not named — requires clarification from the user."
    },
    "base-044": {
        "expected_verification_criteria": [
            "The user's Fitbit device records at least 10,000 steps for the current day"
        ],
        "expected_verification_method": "Check the user's Fitbit app or Fitbit API for today's step count. Requires authenticated access to the user's Fitbit account. No Fitbit API currently registered. Fallback: ask the user to check their Fitbit and report the step count."
    },
    "base-045": {
        "expected_verification_criteria": [
            "The user's commute time tomorrow exceeds their commute time today"
        ],
        "expected_verification_method": "Requires the user to report both commute times (today and tomorrow). While traffic data is publicly available, the user's specific commute route and actual travel times are personal data. Partially automatable if the user's route is known and traffic APIs are available, but actual commute time requires user reporting."
    },
}

# --- Inject into dataset ---
with open("eval/golden_dataset.json", "r") as f:
    data = json.load(f)

missing = []
for bp in data["base_predictions"]:
    bp_id = bp["id"]
    if bp_id in V3_FIELDS:
        bp["ground_truth"]["expected_verification_criteria"] = V3_FIELDS[bp_id]["expected_verification_criteria"]
        bp["ground_truth"]["expected_verification_method"] = V3_FIELDS[bp_id]["expected_verification_method"]
    else:
        missing.append(bp_id)

if missing:
    print(f"ERROR: Missing v3 fields for: {missing}", file=sys.stderr)
    sys.exit(1)

with open("eval/golden_dataset.json", "w") as f:
    json.dump(data, f, indent=2)

print(f"Injected v3 fields into {len(V3_FIELDS)} base predictions")
print(f"Schema version: {data['schema_version']}")
print(f"Dataset version: {data['dataset_version']}")
