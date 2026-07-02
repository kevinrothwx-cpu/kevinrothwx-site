"""
Per-stadium content blocks for /nfl/stadium/<slug> landing pages.

Each entry pairs with an NFL team stadium from nfl.venues.NFL_TEAMS. Two
NFL teams share stadiums (MetLife = Jets+Giants; SoFi = Chargers+Rams),
so this file has 30 unique stadium entries covering all 32 teams.

Rules for content:
- No em-dashes.
- No specific climatology numbers I can't source.
- Facts anchored in: stadium name, city, roof type, general regional
  cold/warm/wet reputation, and roof behavior for retractable/fixed.
- Season context: NFL runs September through early February.
"""

STADIUM_CONTENT = {
    "Highmark Stadium": {
        "slug": "highmark-stadium",
        "team": "Buffalo Bills",
        "headline": "Highmark Stadium Weather: Buffalo Cold, Lake-Effect Snow, Open-Air Football",
        "climate": (
            "The Bills play in Orchard Park just south of Buffalo, close "
            "to the eastern shore of Lake Erie. Late-season and playoff "
            "games regularly play in freezing temperatures with lake-"
            "effect snow risk from November through January."
        ),
        "wind": (
            "The park is fully open-air. Wind off Lake Erie can reach "
            "double digits with cross-lake flow patterns, which affects "
            "kicking accuracy and downfield passing more than at inland "
            "stadiums of similar latitude."
        ),
        "roof_note": "",
        "fantasy_note": (
            "Cold-weather Buffalo games are one of the classic weather-"
            "influenced NFL environments. Kicker performance, deep-ball "
            "efficiency, and turnover risk all shift with heavy wind and "
            "snow. Late-season games are the highest-leverage weather "
            "reads on the Bills schedule."
        ),
    },
    "Hard Rock Stadium": {
        "slug": "hard-rock-stadium",
        "team": "Miami Dolphins",
        "headline": "Hard Rock Stadium Weather: Miami Heat, Humidity, and Storm Risk",
        "climate": (
            "The Dolphins play in Miami Gardens, north of downtown Miami. "
            "Early-season games from September through October regularly "
            "run hot and humid, with heat index a real factor for player "
            "output. Afternoon thunderstorm risk is high in September."
        ),
        "wind": (
            "The stadium is open-air. Tropical-cyclone-driven weather "
            "can force schedule changes in September, and afternoon sea "
            "breeze affects passing conditions in early-season games."
        ),
        "roof_note": "",
        "fantasy_note": (
            "Heat index is the main early-season handicap. Late-season "
            "Miami games play in more moderate conditions. Rare cold "
            "fronts through December are a signal for visiting teams "
            "unaccustomed to the warm baseline."
        ),
    },
    "Gillette Stadium": {
        "slug": "gillette-stadium",
        "team": "New England Patriots",
        "headline": "Gillette Stadium Weather: New England Cold, Coastal Wind, Open-Air Football",
        "climate": (
            "The Patriots play in Foxborough between Boston and Providence. "
            "Late-season games regularly play in cold and windy conditions. "
            "December and January games can drop into the teens with wind "
            "chill well below zero."
        ),
        "wind": (
            "Coastal storm influence brings sustained wind through fall "
            "and winter. Northeast wind from Nor'easters is the highest-"
            "impact pattern for kicking and downfield passing."
        ),
        "roof_note": "",
        "fantasy_note": (
            "Coastal fronts and Nor'easter influence are the main "
            "weather angles at Gillette. Late-season wind and cold "
            "combine to suppress passing volume and kicking accuracy."
        ),
    },
    "MetLife Stadium": {
        "slug": "metlife-stadium",
        "team": "New York Jets / New York Giants",
        "headline": "MetLife Stadium Weather: East Rutherford Cold, Two-Team Home, Open-Air Football",
        "climate": (
            "MetLife is the shared home of the Jets and Giants in East "
            "Rutherford, New Jersey, in the Meadowlands. The area runs "
            "cold and wet through late season, with typical Northeast "
            "storm-track exposure November through January."
        ),
        "wind": (
            "The Meadowlands' open marshland setting produces sustained "
            "wind under most weather patterns. Northeast wind from "
            "coastal storms is the sharpest single weather signal."
        ),
        "roof_note": "",
        "fantasy_note": (
            "Two NFL teams play here, so both Jets and Giants games are "
            "affected by MetLife wind and cold. Late-season Nor'easter-"
            "influenced games are the highest-leverage weather reads."
        ),
    },
    "M&T Bank Stadium": {
        "slug": "mt-bank-stadium",
        "team": "Baltimore Ravens",
        "headline": "M&T Bank Stadium Weather: Baltimore Mid-Atlantic, Open-Air Football",
        "climate": (
            "The Ravens play in downtown Baltimore. Early-season games "
            "play warm and humid; late-season games play in cool and "
            "occasionally cold conditions with mid-Atlantic storm-track "
            "exposure."
        ),
        "wind": (
            "The stadium is open-air. Chesapeake Bay influence produces "
            "moderate wind under most patterns; Nor'easter systems bring "
            "the sharpest wind and rain."
        ),
        "roof_note": "",
        "fantasy_note": (
            "Baltimore weather is moderate for most of the season. "
            "Late-November through January games with Nor'easter-driven "
            "rain and wind are the classic weather-influenced environment."
        ),
    },
    "Paycor Stadium": {
        "slug": "paycor-stadium",
        "team": "Cincinnati Bengals",
        "headline": "Paycor Stadium Weather: Cincinnati Ohio Valley, Open-Air Football",
        "climate": (
            "The Bengals play in downtown Cincinnati on the north bank "
            "of the Ohio River. Ohio Valley climate runs humid through "
            "fall and cold in December and January."
        ),
        "wind": (
            "The stadium is open-air. Ohio River valley channeling can "
            "align wind along the river axis. Late-season cold-front "
            "passages bring the sharpest wind shifts."
        ),
        "roof_note": "",
        "fantasy_note": (
            "Late-season Cincinnati games with cold-front-driven wind "
            "and rain are the main weather handicaps. Early season plays "
            "warm and moderate."
        ),
    },
    "Huntington Bank Field": {
        "slug": "huntington-bank-field",
        "team": "Cleveland Browns",
        "headline": "Huntington Bank Field Weather: Lake Erie Wind, Cleveland Cold, Open-Air Football",
        "climate": (
            "The Browns play in downtown Cleveland directly on the "
            "south shore of Lake Erie. Lake-effect snow and lake-"
            "influenced wind are the defining weather features. "
            "Late-season games regularly play in freezing conditions."
        ),
        "wind": (
            "Direct lakefront setting produces heavy north wind off the "
            "lake under many weather patterns. Wind affects kicking "
            "accuracy and downfield passing more here than at almost any "
            "other NFL stadium."
        ),
        "roof_note": "",
        "fantasy_note": (
            "Cleveland is one of the NFL's most wind-affected stadiums. "
            "Late-season games with 15-plus mph wind are common and "
            "affect scoring environment. Snow games are on the schedule "
            "annually."
        ),
    },
    "Acrisure Stadium": {
        "slug": "acrisure-stadium",
        "team": "Pittsburgh Steelers",
        "headline": "Acrisure Stadium Weather: Pittsburgh Rivers, Late-Season Cold, Open-Air Football",
        "climate": (
            "The Steelers play at the confluence of the Allegheny and "
            "Monongahela in downtown Pittsburgh. River-valley setting "
            "with Ohio Valley climate. Late-season games run cold with "
            "typical Appalachian storm-track exposure."
        ),
        "wind": (
            "River-valley channeling affects wind at the field. "
            "Late-season cold-front passages bring the sharpest wind "
            "shifts."
        ),
        "roof_note": "",
        "fantasy_note": (
            "December and January Pittsburgh games with cold-front-"
            "driven wind and snow are the classic weather-influenced "
            "conditions. Early-season plays moderate."
        ),
    },
    "NRG Stadium": {
        "slug": "nrg-stadium",
        "team": "Houston Texans",
        "headline": "NRG Stadium Weather: Retractable Roof, Houston Heat",
        "climate": (
            "The Texans play in a retractable-roof stadium in Houston. "
            "Early-season heat is extreme and drives the roof closed "
            "decision for many September and October games."
        ),
        "wind": (
            "With the roof closed, no wind. With the roof open, downtown "
            "Houston limits natural wind reaching the field."
        ),
        "roof_note": (
            "NRG Stadium's roof closes for most home games during "
            "September and early October because of heat. Closed "
            "conditions produce climate-controlled indoor football. "
            "The roof opens more often in November, December, and "
            "January for cooler evenings."
        ),
        "fantasy_note": (
            "Roof status is the day-of-game leverage. Assume closed for "
            "any Houston high above 90. Closed roof removes weather "
            "entirely; open roof plays as warm humid outdoor football."
        ),
    },
    "Lucas Oil Stadium": {
        "slug": "lucas-oil-stadium",
        "team": "Indianapolis Colts",
        "headline": "Lucas Oil Stadium Weather: Retractable Roof, Indianapolis Setting",
        "climate": (
            "The Colts play in a retractable-roof stadium in downtown "
            "Indianapolis. Roof status varies through the season, with "
            "closed baseline for cold and wet conditions."
        ),
        "wind": (
            "With the roof closed, no wind. Roof-open games see typical "
            "downtown Indianapolis wind, which the surrounding buildings "
            "moderate."
        ),
        "roof_note": (
            "Lucas Oil closes the roof for most cold-weather games from "
            "November onward. Early-season games with moderate weather "
            "often see the roof open."
        ),
        "fantasy_note": (
            "Roof status is the leverage. Closed roof produces neutral "
            "indoor football with no weather variance. Open roof late "
            "season is rare and would signal team preference for "
            "unusually mild conditions."
        ),
    },
    "EverBank Stadium": {
        "slug": "everbank-stadium",
        "team": "Jacksonville Jaguars",
        "headline": "EverBank Stadium Weather: Jacksonville Heat, Coastal Setting, Open-Air Football",
        "climate": (
            "The Jaguars play in downtown Jacksonville near the St. "
            "Johns River. Early-season games run hot and humid. Coastal "
            "storm risk is elevated in September."
        ),
        "wind": (
            "Coastal proximity brings sea-breeze influence for afternoon "
            "games. Tropical-storm-driven weather can force schedule "
            "changes in September."
        ),
        "roof_note": "",
        "fantasy_note": (
            "Early-season heat index is the primary handicap. Late-"
            "season plays moderate. Cold snaps are rare but do occur "
            "in December and January."
        ),
    },
    "Nissan Stadium": {
        "slug": "nissan-stadium",
        "team": "Tennessee Titans",
        "headline": "Nissan Stadium Weather: Nashville, Cumberland River, Open-Air Football",
        "climate": (
            "The Titans play in downtown Nashville on the east bank of "
            "the Cumberland River. Tennessee climate runs warm and "
            "humid early season, cool and occasionally cold late season."
        ),
        "wind": (
            "River-valley setting produces moderate wind. Late-season "
            "cold-front passages bring the sharpest wind shifts."
        ),
        "roof_note": "",
        "fantasy_note": (
            "Nashville weather is moderate for most of the season. Late-"
            "season cold-front-driven games are the main handicap window."
        ),
    },
    "Empower Field at Mile High": {
        "slug": "empower-field-at-mile-high",
        "team": "Denver Broncos",
        "headline": "Empower Field Weather: Mile-High Denver, Thin Air, Open-Air Football",
        "climate": (
            "The Broncos play in Denver at 5,280 feet of elevation. "
            "Mile-high air density affects kick distance and ball flight "
            "consistently, more than any other single elevation factor "
            "in the NFL."
        ),
        "wind": (
            "Denver climate runs dry with variable wind. Late-season "
            "cold-front passages bring sharp temperature drops and "
            "snow risk."
        ),
        "roof_note": "",
        "fantasy_note": (
            "Elevation is the everyday factor. Kickers gain range at "
            "altitude; passing benefits slightly from lower air density. "
            "Cold snaps and snow games are the late-season weather "
            "handicap."
        ),
    },
    "GEHA Field at Arrowhead Stadium": {
        "slug": "arrowhead-stadium",
        "team": "Kansas City Chiefs",
        "headline": "Arrowhead Stadium Weather: Kansas City Cold, Plains Wind, Open-Air Football",
        "climate": (
            "The Chiefs play east of downtown Kansas City on the plains. "
            "Late-season games regularly play in cold and windy "
            "conditions with occasional heavy snow. Wind chill in "
            "January playoff games can drop below zero."
        ),
        "wind": (
            "Plains setting produces sustained wind, particularly with "
            "cold-front-driven north and northwest flow in late season. "
            "Wind affects kicking accuracy and downfield passing."
        ),
        "roof_note": "",
        "fantasy_note": (
            "Cold-weather Arrowhead playoff games are among the most "
            "weather-influenced NFL environments. Late-season regular-"
            "season games with sustained plains wind are the main "
            "weather handicaps."
        ),
    },
    "Allegiant Stadium": {
        "slug": "allegiant-stadium",
        "team": "Las Vegas Raiders",
        "headline": "Allegiant Stadium Weather: Fixed Dome, Las Vegas Setting",
        "climate": (
            "The Raiders play in a fixed-dome stadium in Paradise, "
            "Nevada. Outside conditions do not affect the field. "
            "Climate-controlled indoor football every game."
        ),
        "wind": (
            "No wind at Allegiant. Consistent indoor conditions "
            "eliminate weather variance from Raiders home games."
        ),
        "roof_note": (
            "Allegiant Stadium is a fixed enclosed structure. No "
            "retractable roof and no operable panels. Every Raiders "
            "home game plays in identical climate-controlled "
            "conditions."
        ),
        "fantasy_note": (
            "Dome baseball parallel: no weather variance means "
            "consistent kicking distance, passing conditions, and "
            "footing. Away Raiders games are where weather handicapping "
            "matters most."
        ),
    },
    "SoFi Stadium": {
        "slug": "sofi-stadium",
        "team": "Los Angeles Chargers / Los Angeles Rams",
        "headline": "SoFi Stadium Weather: Fixed Canopy, Two-Team Home, Los Angeles Climate",
        "climate": (
            "SoFi Stadium is the shared home of the Chargers and Rams "
            "in Inglewood. The stadium has a fixed transparent canopy "
            "roof that covers the seating but leaves the sides open. "
            "Los Angeles marine climate influences the field."
        ),
        "wind": (
            "The fixed canopy limits direct precipitation on the field "
            "but does not block wind. Outside wind reaches the playing "
            "surface. Mild California conditions predominate."
        ),
        "roof_note": (
            "SoFi has a permanent canopy roof but is not a sealed dome. "
            "Rain and heavy wind reach the field. Games play in "
            "essentially outdoor conditions with rain cover for "
            "spectators."
        ),
        "fantasy_note": (
            "Two NFL teams share this venue. Los Angeles climate is "
            "moderate year-round; Santa Ana wind events in September "
            "and October produce the main weather variance. Late-season "
            "cool temperatures are mild compared to cold-market NFL "
            "stadiums."
        ),
    },
    "AT&T Stadium": {
        "slug": "att-stadium",
        "team": "Dallas Cowboys",
        "headline": "AT&T Stadium Weather: Retractable Roof, Dallas Heat and Cold",
        "climate": (
            "The Cowboys play in a retractable-roof stadium in "
            "Arlington. Roof status varies through the season, closed "
            "for extreme heat early and for cold late."
        ),
        "wind": (
            "With the roof closed, no wind. With the roof open, typical "
            "North Texas wind reaches the field."
        ),
        "roof_note": (
            "AT&T Stadium closes the roof for the majority of home "
            "games because of extreme heat in September and cold in "
            "late season. Roof-open games are more common in "
            "mid-season stretches with moderate temperatures."
        ),
        "fantasy_note": (
            "Roof status is the day-of-game leverage. Assume closed for "
            "high above 90 or low below 45. Roof-open Cowboys games are "
            "the environment where wind and precipitation actually "
            "matter."
        ),
    },
    "Lincoln Financial Field": {
        "slug": "lincoln-financial-field",
        "team": "Philadelphia Eagles",
        "headline": "Lincoln Financial Field Weather: Philadelphia Cold, Open-Air Football",
        "climate": (
            "The Eagles play in South Philadelphia. Mid-Atlantic climate "
            "runs warm and humid early season, cold and windy in "
            "December and January with Nor'easter influence."
        ),
        "wind": (
            "Coastal storm systems bring sustained wind through late "
            "season. Northeast wind from Nor'easters is the sharpest "
            "single weather signal."
        ),
        "roof_note": "",
        "fantasy_note": (
            "Late-season Eagles games with Nor'easter-influenced wind "
            "and precipitation are the primary weather angle. Early "
            "season plays moderate."
        ),
    },
    "Northwest Stadium": {
        "slug": "northwest-stadium",
        "team": "Washington Commanders",
        "headline": "Northwest Stadium Weather: Landover Mid-Atlantic, Open-Air Football",
        "climate": (
            "The Commanders play in Landover, Maryland. Mid-Atlantic "
            "climate similar to Baltimore. Early season warm and humid; "
            "late season cool with Nor'easter risk."
        ),
        "wind": (
            "Coastal storm systems produce sustained wind through late "
            "season. Chesapeake Bay influence adds moisture."
        ),
        "roof_note": "",
        "fantasy_note": (
            "Late-season Nor'easter-driven wind and rain are the primary "
            "weather angle. Moderate conditions predominate through "
            "October."
        ),
    },
    "Soldier Field": {
        "slug": "soldier-field",
        "team": "Chicago Bears",
        "headline": "Soldier Field Weather: Lake Michigan Wind, Chicago Cold, Open-Air Football",
        "climate": (
            "The Bears play on the Chicago lakefront directly on Lake "
            "Michigan. Late-season games regularly play in freezing "
            "conditions with lake-influenced wind and occasional heavy "
            "snow."
        ),
        "wind": (
            "Direct lakefront exposure produces heavy wind under most "
            "weather patterns. Cross-lake and north wind off the lake "
            "affect kicking accuracy and passing more than at almost "
            "any other stadium."
        ),
        "roof_note": "",
        "fantasy_note": (
            "Soldier Field is one of the NFL's most consistently "
            "wind-affected stadiums. Late-season and playoff games with "
            "sustained lake wind are the highest-leverage weather reads."
        ),
    },
    "Ford Field": {
        "slug": "ford-field",
        "team": "Detroit Lions",
        "headline": "Ford Field Weather: Fixed Dome, Detroit Setting",
        "climate": (
            "The Lions play in a fixed-dome stadium in downtown Detroit. "
            "Outside conditions do not affect the field. Climate-"
            "controlled indoor football every game."
        ),
        "wind": (
            "No wind at Ford Field. Consistent indoor conditions "
            "eliminate weather variance from Lions home games."
        ),
        "roof_note": (
            "Ford Field is a fixed enclosed structure with no operable "
            "roof panels. Every Lions home game plays in identical "
            "climate-controlled conditions."
        ),
        "fantasy_note": (
            "Weather variance is zero for Lions home games. Away Lions "
            "games in cold-weather NFC North matchups at Chicago, "
            "Green Bay, and Minneapolis are where weather handicapping "
            "matters most."
        ),
    },
    "Lambeau Field": {
        "slug": "lambeau-field",
        "team": "Green Bay Packers",
        "headline": "Lambeau Field Weather: Green Bay Cold, Frozen Tundra, Open-Air Football",
        "climate": (
            "The Packers play in Green Bay, Wisconsin. Lambeau is the "
            "most historically cold-affected NFL stadium, with December "
            "and January games regularly playing in single-digit and "
            "sub-zero temperatures."
        ),
        "wind": (
            "Wisconsin plains and lake influence produce sustained wind "
            "in most weather patterns. Cold-front-driven north and "
            "northwest wind combines with sub-freezing temperatures for "
            "the classic Lambeau environment."
        ),
        "roof_note": "",
        "fantasy_note": (
            "Cold-weather Lambeau games are the archetypal NFL weather "
            "environment. Late-season and playoff games with sub-zero "
            "wind chill affect kicking accuracy, ball grip, and offensive "
            "output significantly."
        ),
    },
    "U.S. Bank Stadium": {
        "slug": "us-bank-stadium",
        "team": "Minnesota Vikings",
        "headline": "U.S. Bank Stadium Weather: Fixed Dome, Minneapolis Setting",
        "climate": (
            "The Vikings play in a fixed-dome stadium in downtown "
            "Minneapolis. Outside cold does not affect the field. "
            "Climate-controlled indoor football every game."
        ),
        "wind": (
            "No wind at U.S. Bank Stadium. Consistent indoor conditions "
            "eliminate weather variance from Vikings home games."
        ),
        "roof_note": (
            "U.S. Bank Stadium is a fixed enclosed structure. Every "
            "Vikings home game plays in identical climate-controlled "
            "conditions, regardless of Minneapolis outside temperature."
        ),
        "fantasy_note": (
            "Vikings home games have zero weather variance despite "
            "playing in one of the coldest NFL markets. Away Vikings "
            "games in cold-weather NFC North matchups at Chicago and "
            "Green Bay are where weather matters."
        ),
    },
    "Mercedes-Benz Stadium": {
        "slug": "mercedes-benz-stadium",
        "team": "Atlanta Falcons",
        "headline": "Mercedes-Benz Stadium Weather: Retractable Roof, Atlanta Setting",
        "climate": (
            "The Falcons play in a retractable-roof stadium in downtown "
            "Atlanta. Roof status varies through the season, with "
            "closed baseline for heat and rain."
        ),
        "wind": (
            "With the roof closed, no wind. With the roof open, "
            "downtown Atlanta wind reaches the field, moderated by "
            "surrounding buildings."
        ),
        "roof_note": (
            "Mercedes-Benz Stadium's roof closes for the majority of "
            "home games because of Atlanta heat and rain risk in "
            "September and early October, and cold in late season. "
            "Open-roof games are less common."
        ),
        "fantasy_note": (
            "Roof status is the leverage. Closed roof removes weather "
            "entirely. Open-roof games are relatively rare and would "
            "signal team preference for moderate outside conditions."
        ),
    },
    "Bank of America Stadium": {
        "slug": "bank-of-america-stadium",
        "team": "Carolina Panthers",
        "headline": "Bank of America Stadium Weather: Charlotte Southeast, Open-Air Football",
        "climate": (
            "The Panthers play in downtown Charlotte. Southeast climate "
            "runs warm and humid early season, cool late season. Snow "
            "is rare but does occur in December and January."
        ),
        "wind": (
            "The stadium is open-air. Piedmont wind patterns produce "
            "moderate wind under most conditions. Late-season cold-"
            "front passages bring the sharpest wind shifts."
        ),
        "roof_note": "",
        "fantasy_note": (
            "Charlotte weather is moderate for most of the NFL season. "
            "Late-November through January games with cold-front-"
            "driven wind and rain are the main weather handicaps."
        ),
    },
    "Caesars Superdome": {
        "slug": "caesars-superdome",
        "team": "New Orleans Saints",
        "headline": "Caesars Superdome Weather: Fixed Dome, New Orleans Setting",
        "climate": (
            "The Saints play in a fixed-dome stadium in downtown New "
            "Orleans. Outside conditions do not affect the field. "
            "Climate-controlled indoor football every game."
        ),
        "wind": (
            "No wind at the Superdome. Consistent indoor conditions "
            "eliminate weather variance from Saints home games."
        ),
        "roof_note": (
            "The Superdome is a fixed enclosed structure. Every Saints "
            "home game plays in identical climate-controlled conditions "
            "regardless of New Orleans outside weather."
        ),
        "fantasy_note": (
            "Zero weather variance for Saints home games despite the "
            "hurricane-exposed climate. Tropical storm risk in September "
            "occasionally affects scheduling but not gameplay conditions."
        ),
    },
    "Raymond James Stadium": {
        "slug": "raymond-james-stadium",
        "team": "Tampa Bay Buccaneers",
        "headline": "Raymond James Stadium Weather: Tampa Heat, Storm Risk, Open-Air Football",
        "climate": (
            "The Buccaneers play in Tampa. Early-season games run hot "
            "and humid with heat index a factor. Tropical-cyclone-"
            "driven weather can force schedule changes in September and "
            "October."
        ),
        "wind": (
            "Coastal proximity brings sea-breeze influence and tropical-"
            "system wind risk. Late-season plays moderate."
        ),
        "roof_note": "",
        "fantasy_note": (
            "Early-season heat and hurricane-season storm risk are the "
            "main weather angles. Late-season plays moderate; rare cold "
            "fronts in December can shift conditions for visiting warm-"
            "weather teams."
        ),
    },
    "State Farm Stadium": {
        "slug": "state-farm-stadium",
        "team": "Arizona Cardinals",
        "headline": "State Farm Stadium Weather: Retractable Roof, Arizona Heat",
        "climate": (
            "The Cardinals play in a retractable-roof stadium in "
            "Glendale, Arizona. Roof status is driven by extreme "
            "September heat baseline and moderating through late season."
        ),
        "wind": (
            "With the roof closed, no wind. With the roof open, desert "
            "wind reaches the field under prevailing patterns."
        ),
        "roof_note": (
            "State Farm Stadium's roof closes for early-season games "
            "because of Phoenix-area heat. Late-season games with cooler "
            "evenings see the roof open more often."
        ),
        "fantasy_note": (
            "Roof status is the leverage. September games with heat "
            "index above 100 outside are almost certainly closed-roof "
            "environments. Late-season roof-open games are the true "
            "outdoor Cardinals conditions."
        ),
    },
    "Levi's Stadium": {
        "slug": "levis-stadium",
        "team": "San Francisco 49ers",
        "headline": "Levi's Stadium Weather: Santa Clara Bay Air, Open-Air Football",
        "climate": (
            "The 49ers play in Santa Clara in the South Bay. Marine "
            "influence keeps temperatures moderate. Early-season "
            "afternoon games can run warm; late-season plays mild."
        ),
        "wind": (
            "South Bay setting produces moderate wind. Marine-air "
            "onshore flow is the typical pattern."
        ),
        "roof_note": "",
        "fantasy_note": (
            "Santa Clara weather is moderate year-round. Weather has "
            "little impact on 49ers home games under typical conditions. "
            "Rain during the wet season from late November through "
            "January is the main variance."
        ),
    },
    "Lumen Field": {
        "slug": "lumen-field",
        "team": "Seattle Seahawks",
        "headline": "Lumen Field Weather: Seattle Rain, Marine Climate, Open-Air Football",
        "climate": (
            "The Seahawks play in downtown Seattle near Puget Sound. "
            "Marine climate produces cool temperatures and elevated "
            "rain risk through the NFL season. Late-season and playoff "
            "games often play in steady rain."
        ),
        "wind": (
            "Marine-influenced wind reaches the field. Rain and wet "
            "conditions are more common at Lumen than at any other NFL "
            "stadium."
        ),
        "roof_note": "",
        "fantasy_note": (
            "Wet conditions and rain during late-season Seahawks home "
            "games are the primary weather angle. Ball-security "
            "handicapping and kicking accuracy under wet conditions are "
            "the leverage."
        ),
    },
}

# Slug reverse lookup + team-name lookup for URL routing
STADIUM_BY_SLUG_NFL = {c["slug"]: (name, c) for name, c in STADIUM_CONTENT.items()}
