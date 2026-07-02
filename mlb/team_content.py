"""
Per-team content blocks for /mlb/team/<slug> landing pages.

Each entry pairs a current MLB team with team-specific weather narrative
that doesn't duplicate the stadium page. The stadium page covers the
ballpark; the team page covers how the team plays in weather at home
versus on the road, and what a DFS player or bettor should think about
when handicapping a team's schedule.

Rules for content:
- No em-dashes.
- No hedge language.
- No player-specific claims unless verified.
- No standings or record claims (they change).
"""

# MLB division memberships. Used to generate divisional-rival stadium
# cross-links on team pages so the SEO graph has natural internal linking.
DIVISIONS = {
    "AL East":    ["Baltimore Orioles", "Boston Red Sox", "New York Yankees",
                   "Tampa Bay Rays", "Toronto Blue Jays"],
    "AL Central": ["Chicago White Sox", "Cleveland Guardians", "Detroit Tigers",
                   "Kansas City Royals", "Minnesota Twins"],
    "AL West":    ["Houston Astros", "Los Angeles Angels", "Oakland Athletics",
                   "Seattle Mariners", "Texas Rangers"],
    "NL East":    ["Atlanta Braves", "Miami Marlins", "New York Mets",
                   "Philadelphia Phillies", "Washington Nationals"],
    "NL Central": ["Chicago Cubs", "Cincinnati Reds", "Milwaukee Brewers",
                   "Pittsburgh Pirates", "St. Louis Cardinals"],
    "NL West":    ["Arizona Diamondbacks", "Colorado Rockies",
                   "Los Angeles Dodgers", "San Diego Padres",
                   "San Francisco Giants"],
}

TEAM_TO_DIVISION = {}
for div, teams in DIVISIONS.items():
    for t in teams:
        TEAM_TO_DIVISION[t] = div


TEAM_CONTENT = {
    "Boston Red Sox": {
        "slug": "boston-red-sox",
        "home_park": "Fenway Park",
        "headline": "Boston Red Sox Weather Playbook: Fenway, Coastal Air, and Road Trips",
        "home_advantage": (
            "Fenway plays in cool coastal air for the first six weeks of the "
            "season and again from mid-September onward. Sea breeze from the "
            "east and southeast is common on afternoon games and reverses "
            "wind direction between first pitch and the fifth inning. The "
            "Green Monster in left field turns short-porch fly balls into "
            "wall singles and back-of-the-park doubles, which changes how "
            "wind-out-to-left plays compared to any other park in the majors."
        ),
        "road_challenges": (
            "The AL East includes the Trop dome and Yankee Stadium's short "
            "right-field porch, which are stable environments the Red Sox "
            "face repeatedly. Toronto's retractable roof at Rogers Centre "
            "removes weather from Toronto series most of the year. Camden "
            "Yards in Baltimore plays warm humid in July and August, closer "
            "to the classic hot-weather setup than Fenway ever gets."
        ),
        "betting_angle": (
            "Wind direction relative to the Monster is the single largest "
            "leverage point on Red Sox home totals. Cold northeast wind and "
            "low dew points in April can knock 1.5 runs off a total that "
            "sits at a season-average number. Warm southwest wind in July "
            "does the opposite."
        ),
    },
    "New York Yankees": {
        "slug": "new-york-yankees",
        "home_park": "Yankee Stadium",
        "headline": "New York Yankees Weather Playbook: Short Porch, Bronx Heat, Division Wind",
        "home_advantage": (
            "Yankee Stadium's short right-field porch is 314 feet down the "
            "line and reachable on any warm humid night with wind out to "
            "right. West wind, the dominant summer pattern behind cold "
            "fronts, blows out to center. The Yankees left-handed lineup "
            "structure historically benefits when either wind pattern lines "
            "up with the porch."
        ),
        "road_challenges": (
            "The AL East is a mix of dome (Trop), retractable (Rogers Centre), "
            "and coastal parks. Camden Yards plays hot and humid in the "
            "summer, closer to the maximum-carry setup. Fenway's Monster "
            "changes how wind reads on left-field balls. Rogers Centre "
            "removes weather entirely with the roof closed."
        ),
        "betting_angle": (
            "Wind direction at Yankee Stadium is the leverage. Wind out to "
            "right combined with warm humid air is the classic short-porch "
            "friendly setup. Cold north wind days flip the environment to "
            "neutral or pitcher-friendly."
        ),
    },
    "Baltimore Orioles": {
        "slug": "baltimore-orioles",
        "home_park": "Oriole Park at Camden Yards",
        "headline": "Baltimore Orioles Weather Playbook: Camden's 2025 Wall, Mid-Atlantic Humidity",
        "home_advantage": (
            "Camden Yards moved the left-field wall back in for the 2025 "
            "season, restoring home run potential the 2022 configuration "
            "had taken away. Baltimore summers run hot and humid with south "
            "wind blowing out to center and right. Afternoon thunderstorms "
            "from the Appalachian foothills reach the yard through evening "
            "in June, July, and August."
        ),
        "road_challenges": (
            "AL East road trips split between the Trop dome, Rogers Centre "
            "retractable, and Fenway and Yankee Stadium. Fenway's short "
            "Monster and Yankee Stadium's short right porch play differently "
            "than Camden even in similar wind."
        ),
        "betting_angle": (
            "Post-2025 Camden with south wind and 70-plus dew points is the "
            "friendlier hitting version of the park than 2022 to 2024. "
            "Traders who anchor to the older wall configuration are pricing "
            "totals too low on warm-wind days."
        ),
    },
    "Tampa Bay Rays": {
        "slug": "tampa-bay-rays",
        "home_park": "Tropicana Field",
        "headline": "Tampa Bay Rays Weather Playbook: Dome Baseball, No Variance",
        "home_advantage": (
            "The Trop is a fixed dome. Every Rays home game plays in air-"
            "conditioned 72-degree stillness with no wind. That gives the "
            "Rays the most predictable home environment in the majors and "
            "removes weather from their home totals entirely. Rain, heat, "
            "and Florida afternoon thunderstorms outside do not reach the "
            "field."
        ),
        "road_challenges": (
            "Rays road trips into the AL East meet coastal humidity at "
            "Camden Yards, Fenway sea breezes, Yankee Stadium in the Bronx "
            "heat, and Rogers Centre retractable. The Rays travel from a "
            "climate-controlled home to almost every kind of weather "
            "environment the season offers."
        ),
        "betting_angle": (
            "Home Rays totals are the cleanest weather-agnostic prices in "
            "MLB. Road Rays totals are where handicapping wind and "
            "temperature matters most, since their home park gives them "
            "no adaptation to outdoor variance."
        ),
    },
    "Toronto Blue Jays": {
        "slug": "toronto-blue-jays",
        "home_park": "Rogers Centre",
        "headline": "Toronto Blue Jays Weather Playbook: Rogers Centre Roof, Lake Ontario Setting",
        "home_advantage": (
            "Rogers Centre is retractable-roofed. The Jays close the roof "
            "for most cold-weather games in April, May, September, and "
            "October, and for rain. Open-roof games in the warm summer "
            "months see wind off Lake Ontario and downtown Toronto "
            "channeling that can affect carry. Closed conditions produce "
            "neutral 72-degree indoor baseball with no wind."
        ),
        "road_challenges": (
            "The AL East gives the Jays the Trop dome, Camden Yards, Fenway, "
            "and Yankee Stadium. Camden's summer heat and humidity are the "
            "biggest environmental swing from Rogers Centre. Sea-breeze "
            "reversal at Fenway and Yankee Stadium wind patterns require "
            "different lineup handicapping."
        ),
        "betting_angle": (
            "Roof status at Rogers Centre is the largest single day-of-game "
            "weather variable in the AL East. The Jays announce roof status "
            "the morning of first pitch. Open roof plus south wind is the "
            "friendliest hitting environment; closed is neutral."
        ),
    },
    "Chicago White Sox": {
        "slug": "chicago-white-sox",
        "home_park": "Guaranteed Rate Field",
        "headline": "Chicago White Sox Weather Playbook: South Side, Lake Breeze, Division Cold",
        "home_advantage": (
            "Rate Field sits on the South Side about two miles from Lake "
            "Michigan. Chicago lake breeze is the story for afternoon "
            "games: south wind at first pitch can flip to east wind by "
            "the fifth inning as the breeze arrives. Night games behind a "
            "warm-front push with south wind produce the friendliest "
            "hitting conditions."
        ),
        "road_challenges": (
            "The AL Central puts the White Sox in Cleveland lake-effect "
            "cool, Detroit summer humidity, Kansas City plains heat and "
            "wind, and Minneapolis cold snaps. The division is one of the "
            "more weather-varied in the majors, with April games regularly "
            "played in the 40s across multiple parks."
        ),
        "betting_angle": (
            "Lake-breeze timing at Rate Field is the primary handicapping "
            "angle for home totals. Night games with sustained south wind "
            "are the highest-scoring conditions. Cold north wind days from "
            "the lake can suppress totals 1 to 1.5 runs versus season "
            "averages."
        ),
    },
    "Cleveland Guardians": {
        "slug": "cleveland-guardians",
        "home_park": "Progressive Field",
        "headline": "Cleveland Guardians Weather Playbook: Lake Erie Cool, Division Handicapping",
        "home_advantage": (
            "Progressive Field sits less than a mile from Lake Erie. "
            "Lake-influenced wind and cool spring temperatures make April "
            "and early May games routinely play in the 40s and 50s. "
            "Midsummer is cooler than most inland Midwest cities. North "
            "wind off the lake blows across the field from left to right."
        ),
        "road_challenges": (
            "AL Central road trips into Chicago lake breeze, Detroit "
            "summer humidity, Kansas City plains heat and wind, and "
            "Minneapolis. The division is unusual for its combination of "
            "cool-lake and hot-plains environments, which the Guardians "
            "face in the same week during typical schedules."
        ),
        "betting_angle": (
            "Cold spring lake-effect nights suppress totals at Progressive "
            "more than surface temperature reads suggest. Dew point in the "
            "40s at 65 degrees ambient is a carry-suppressing setup even "
            "on days that look playable."
        ),
    },
    "Detroit Tigers": {
        "slug": "detroit-tigers",
        "home_park": "Comerica Park",
        "headline": "Detroit Tigers Weather Playbook: Deep Center Field, Division Environments",
        "home_advantage": (
            "Comerica's 420-foot center field magnifies wind effects on "
            "carry more than shorter parks. South wind, the summer default, "
            "blows straight out to center. North wind off Lake Huron blows "
            "straight in. The deep configuration keeps the park below "
            "league average for home runs in most weather."
        ),
        "road_challenges": (
            "AL Central variance is the main story. Chicago's Rate Field "
            "lake-breeze reversal, Cleveland's lake-effect cool, Kansas "
            "City's plains heat, and Minneapolis cold produce very "
            "different hitting environments across a single division "
            "road trip."
        ),
        "betting_angle": (
            "Comerica's deep-center configuration and prevailing wind "
            "combination is what keeps totals suppressed. South wind at "
            "12-plus mph is what unlocks the park, and it happens less "
            "often than the schedule looks like it would suggest."
        ),
    },
    "Kansas City Royals": {
        "slug": "kansas-city-royals",
        "home_park": "Kauffman Stadium",
        "headline": "Kansas City Royals Weather Playbook: 2025 Fence Changes, Plains Wind",
        "home_advantage": (
            "The Royals moved fences in for the 2025 season, taking "
            "Kauffman from a pitcher's park closer to neutral. Kansas City "
            "summer wind is stiff, with south and southwest flow across "
            "the plains regularly reaching 15 to 20 mph. Hot humid nights "
            "with sustained south wind and the new wall configuration are "
            "the friendliest home run conditions in team history."
        ),
        "road_challenges": (
            "AL Central road trips give the Royals every kind of Midwest "
            "environment. Chicago and Cleveland lake influence, Detroit "
            "summer heat, and Minneapolis spring cold are the main "
            "handicapping variables."
        ),
        "betting_angle": (
            "Post-2025 Kauffman with south wind is a genuinely different "
            "park than the version books have priced for a decade. Warm "
            "humid nights with 15-plus mph south wind may still be "
            "trading below efficient prices as models catch up."
        ),
    },
    "Minnesota Twins": {
        "slug": "minnesota-twins",
        "home_park": "Target Field",
        "headline": "Minnesota Twins Weather Playbook: Minneapolis Cold Snaps, Downtown Wind",
        "home_advantage": (
            "Target Field opened in 2010 in downtown Minneapolis. April "
            "games regularly play in the 40s, and snow delays are possible "
            "in early season. Downtown Minneapolis channels wind through "
            "the park, making it windier than average for a Midwest venue. "
            "Dew point swings widely depending on air mass."
        ),
        "road_challenges": (
            "AL Central takes the Twins into Chicago lake-breeze days, "
            "Cleveland lake-effect cool, Detroit summer humidity, and "
            "Kansas City plains heat with the new fence configuration. "
            "The division is one of the more environmentally varied in "
            "baseball."
        ),
        "betting_angle": (
            "Dew point matters more than temperature at Target Field. A "
            "75-degree game with a 45-degree dew point plays like a "
            "mid-60s game for carry. Warm humid summer nights with south "
            "wind are the friendliest hitting setup."
        ),
    },
    "Houston Astros": {
        "slug": "houston-astros",
        "home_park": "Minute Maid Park",
        "headline": "Houston Astros Weather Playbook: Retractable Roof, Texas Heat",
        "home_advantage": (
            "Minute Maid closes the roof for the majority of home games "
            "from mid-May through September because of Houston heat. "
            "Closed conditions produce 72-degree indoor baseball with no "
            "wind. Open roof on cooler April, October, and early May "
            "evenings can produce strong carry from warm humid air."
        ),
        "road_challenges": (
            "AL West road trips span the Angel Stadium marine influence, "
            "the Oakland Coliseum cold-wind bay setup, T-Mobile Park "
            "cool-marine, Globe Life Field Texas heat with retractable "
            "roof, and Sutter Health Park Sacramento heat. The variance "
            "in air density across those parks is significant."
        ),
        "betting_angle": (
            "Roof status is the day-of-game leverage at Minute Maid. "
            "Closed roof is neutral and stagnant; open roof on a warm "
            "humid night is a live-hitting environment. Assume closed on "
            "any day the Houston high is above 90."
        ),
    },
    "Los Angeles Angels": {
        "slug": "los-angeles-angels",
        "home_park": "Angel Stadium",
        "headline": "Los Angeles Angels Weather Playbook: Anaheim Marine Air, Division Environments",
        "home_advantage": (
            "Angel Stadium sits 12 miles inland from the coast in Anaheim. "
            "Onshore southwest wind, the afternoon default, blows out "
            "toward left-center. Dry marine-influenced air runs 60-degree "
            "dew points, which suppresses carry compared to humid parks. "
            "The park plays as a mild pitcher's park in typical conditions."
        ),
        "road_challenges": (
            "AL West gives the Angels the Astros dome-roof, Oakland Bay "
            "wind, T-Mobile Park Seattle marine, Globe Life Field Texas "
            "heat retractable, and Sutter Health Park Sacramento heat. "
            "Delta breeze timing at Sac and dome status in Houston and "
            "Texas are the main variables."
        ),
        "betting_angle": (
            "Santa Ana wind events in September and October are the "
            "reversal at Anaheim. Hot dry offshore flow at 15-plus mph "
            "turns the park into a live-hitting environment briefly, "
            "which books often mis-price relative to typical marine "
            "conditions."
        ),
    },
    "Oakland Athletics": {
        "slug": "oakland-athletics",
        "home_park": "Sutter Health Park",
        "headline": "Oakland Athletics Weather Playbook: Sacramento Heat, Delta Breeze",
        "home_advantage": (
            "The A's play their home games at Sutter Health Park in West "
            "Sacramento during the transition to Las Vegas. Summer heat "
            "runs hot and dry with July averages around 94 degrees. Delta "
            "breeze from the west arrives in late afternoon and evening, "
            "dropping temperatures and picking up sustained wind speeds "
            "into the 15 to 20 mph range."
        ),
        "road_challenges": (
            "AL West road trips include the Coliseum for interleague and "
            "old-schedule holdovers, T-Mobile Park cool marine, Angel "
            "Stadium onshore, Globe Life Field Texas heat retractable, "
            "and Minute Maid dome-roof. The A's face high air-density "
            "variance across their schedule."
        ),
        "betting_angle": (
            "Delta breeze onset timing is the primary weather handicap "
            "at Sutter Health. Games starting before 7 PM often play in "
            "warm still air; later starts play in stiff westerly wind. "
            "Hot dry pre-breeze afternoons are the highest carry setup."
        ),
    },
    "Seattle Mariners": {
        "slug": "seattle-mariners",
        "home_park": "T-Mobile Park",
        "headline": "Seattle Mariners Weather Playbook: Marine Cool, Retractable Cover",
        "home_advantage": (
            "T-Mobile Park's roof slides overhead but does not enclose the "
            "sides. The Mariners primarily use it as a rain cover. Games "
            "with the roof deployed still see outdoor temperatures and "
            "wind at the field, which is different from Rogers Centre or "
            "Minute Maid. Seattle marine air and low dew points keep "
            "carry below humid-park averages even on clear nights."
        ),
        "road_challenges": (
            "AL West travel gives the Mariners Angel Stadium marine, "
            "Oakland Coliseum bay wind, Globe Life Field Texas heat "
            "retractable, Minute Maid dome-roof, and Sutter Health "
            "Sacramento heat. The team travels from one of the coolest "
            "marine environments to one of the hottest inland climates "
            "repeatedly."
        ),
        "betting_angle": (
            "Marine air makes T-Mobile one of the harder home run "
            "environments in the majors. Warm dry stretches in late July "
            "and August are the friendliest window. Rain delays and roof "
            "closures do not materially change conditions."
        ),
    },
    "Texas Rangers": {
        "slug": "texas-rangers",
        "home_park": "Globe Life Field",
        "headline": "Texas Rangers Weather Playbook: Arlington Retractable, Division Heat Trade",
        "home_advantage": (
            "Globe Life Field opened in 2020 with a retractable roof to "
            "make baseball viable through DFW summer heat. The Rangers "
            "close the roof for the majority of home games May through "
            "September. Closed conditions produce 72-degree indoor "
            "baseball with no wind. Open roof on cooler April, October, "
            "and evening games in shoulder months can produce solid carry."
        ),
        "road_challenges": (
            "AL West road trips into Minute Maid retractable, T-Mobile "
            "marine, Angel Stadium onshore, Oakland Coliseum bay wind, "
            "and Sutter Health Sacramento heat. The variance across those "
            "parks is among the largest in baseball."
        ),
        "betting_angle": (
            "Roof status at Globe Life is the day-of-game leverage. "
            "Assume closed for any Arlington high above 95. Open roof "
            "with south wind produces the friendliest hitting conditions "
            "the park allows."
        ),
    },
    "Atlanta Braves": {
        "slug": "atlanta-braves",
        "home_park": "Truist Park",
        "headline": "Atlanta Braves Weather Playbook: Summer Humidity, Cobb County Setting",
        "home_advantage": (
            "Truist Park sits in Cumberland north of downtown Atlanta. "
            "Southern summer humidity with dew points in the low 70s "
            "combines with south wind out to center and right for strong "
            "carry conditions. Afternoon and evening thunderstorm risk "
            "from June through August is the main weather variance."
        ),
        "road_challenges": (
            "NL East road trips include the Marlins retractable in Miami, "
            "Nationals Park DC humidity, Citi Field Queens coastal, and "
            "Citizens Bank Park Philadelphia humid heat. The division is "
            "warm and humid overall, similar to Atlanta's home baseline."
        ),
        "betting_angle": (
            "Warm humid nights with south wind are the strong hitting "
            "environment at Truist. Rain delay risk and thunderstorm-"
            "shifted start times are the main handicap variables. Watch "
            "radar closely for late-afternoon starts in July and August."
        ),
    },
    "Miami Marlins": {
        "slug": "miami-marlins",
        "home_park": "loanDepot park",
        "headline": "Miami Marlins Weather Playbook: Retractable Roof, Miami Heat and Rain",
        "home_advantage": (
            "loanDepot park's roof is closed for the majority of home "
            "games during summer because of Miami heat and daily "
            "thunderstorm risk. Closed conditions produce 72-degree "
            "indoor baseball with no wind. Open roof on cooler April and "
            "October evenings can produce solid carry from onshore flow."
        ),
        "road_challenges": (
            "NL East gives the Marlins Braves summer humidity, Nationals "
            "Park DC heat, Citi Field coastal setup, and Citizens Bank "
            "humid heat. All are outdoor environments significantly "
            "different from their climate-controlled home."
        ),
        "betting_angle": (
            "Roof status is the day-of-game leverage. Assume closed if "
            "forecast rain probability is above 40 percent. Open roof on "
            "a warm humid summer night with onshore wind is the "
            "friendliest hitting environment the park sees."
        ),
    },
    "New York Mets": {
        "slug": "new-york-mets",
        "home_park": "Citi Field",
        "headline": "New York Mets Weather Playbook: Queens Coastal, Deep Right-Center",
        "home_advantage": (
            "Citi Field sits adjacent to Flushing Bay and less than a mile "
            "from LaGuardia. Right-center at 385 feet magnifies wind "
            "effects on batted balls to that part of the park. Southwest "
            "wind blows out; sea breeze from the east and southeast blows "
            "straight in. Sea-breeze reversal in the sixth or seventh "
            "inning can flip an offensive environment into a suppressive "
            "one."
        ),
        "road_challenges": (
            "NL East road trips into Braves summer humidity, Marlins "
            "dome-roof, Nationals Park DC heat, and Citizens Bank humid "
            "heat. All are warm humid parks similar to Citi in July and "
            "August but with different dimensions."
        ),
        "betting_angle": (
            "Southwest wind at 12-plus mph with warm humid air is the "
            "highest-scoring setup at Citi. Handicap sea-breeze timing "
            "for afternoon starts, since the direction reversal can "
            "change hourly conditions dramatically."
        ),
    },
    "Philadelphia Phillies": {
        "slug": "philadelphia-phillies",
        "home_park": "Citizens Bank Park",
        "headline": "Philadelphia Phillies Weather Playbook: South Philly Heat, Hitter-Friendly Dimensions",
        "home_advantage": (
            "Citizens Bank Park sits in South Philadelphia about three "
            "miles from the Delaware. Summer heat and humidity combine "
            "with dimensions that favor pull-side power for both hands. "
            "Southwest wind, the default summer pattern, blows out to "
            "left-center and center, amplifying the built-in hitter-"
            "friendly setup."
        ),
        "road_challenges": (
            "NL East gives the Phillies Braves summer humidity, Marlins "
            "retractable, Mets coastal, and Nationals Park DC heat. All "
            "are warm humid parks in season. The main variance is Miami "
            "roof status and Citi Field wind direction."
        ),
        "betting_angle": (
            "Warm humid nights with southwest wind are the highest run "
            "environment at Citizens Bank. The park runs above league "
            "average for home runs in most conditions, so weather-adjusted "
            "totals often price the park too conservatively on hot nights."
        ),
    },
    "Washington Nationals": {
        "slug": "washington-nationals",
        "home_park": "Nationals Park",
        "headline": "Washington Nationals Weather Playbook: DC Humidity, Division Handicapping",
        "home_advantage": (
            "Nationals Park sits on the north bank of the Anacostia in "
            "Southeast DC. Summer conditions are hot and humid with south "
            "wind blowing out to center and right. Afternoon thunderstorm "
            "risk is high through July and August, particularly for "
            "afternoon starts."
        ),
        "road_challenges": (
            "NL East road trips through Braves summer humidity, Marlins "
            "dome, Citi Field coastal, and Citizens Bank humid heat. "
            "Marlin roof status is the biggest single day-of variance in "
            "the division."
        ),
        "betting_angle": (
            "Warm humid summer nights with south wind produce the "
            "friendliest hitting conditions at Nats Park. Radar risk for "
            "June through August home games shifts start times and can "
            "invalidate morning-of forecasts."
        ),
    },
    "Chicago Cubs": {
        "slug": "chicago-cubs",
        "home_park": "Wrigley Field",
        "headline": "Chicago Cubs Weather Playbook: Wrigley Wind Is the Whole Story",
        "home_advantage": (
            "Wrigley Field is the most wind-susceptible park in the "
            "majors. Southwest wind at 15 mph turns Wrigley into a "
            "bandbox where fly balls carry to the bleachers. Northeast "
            "wind at 15 mph produces some of the lowest-scoring baseball "
            "anywhere. The lake keeps early-season wind cool and holds "
            "carry down into late May."
        ),
        "road_challenges": (
            "NL Central road trips into Great American Ball Park hitter-"
            "friendly Cincinnati, Milwaukee retractable, PNC Park "
            "Pittsburgh river wind, and Busch Stadium St. Louis heat. "
            "Cincinnati's built-in home run profile is the closest match "
            "to Wrigley in warm wind."
        ),
        "betting_angle": (
            "Wind direction and speed at Wrigley moves total lines 1.5 to "
            "2 runs by itself. Read direction from field-level ASOS at "
            "Meigs Field or Midway for the tightest reads. Wrigley wind "
            "is the highest-leverage single-park weather signal in "
            "baseball."
        ),
    },
    "Cincinnati Reds": {
        "slug": "cincinnati-reds",
        "home_park": "Great American Ball Park",
        "headline": "Cincinnati Reds Weather Playbook: GABP Hitter-Friendly, Division Variance",
        "home_advantage": (
            "Great American Ball Park is consistently one of the top run "
            "environments in the majors regardless of weather. Warm humid "
            "nights with southwest wind out to center and right push the "
            "park into elite hitting territory. Cross-winds along the "
            "Ohio River axis are common but the park runs friendly to "
            "hitters in essentially all typical conditions."
        ),
        "road_challenges": (
            "NL Central takes the Reds into Wrigley wind swings, Milwaukee "
            "retractable, PNC Park river wind, and Busch Stadium St. Louis "
            "heat. Wrigley wind direction and Milwaukee roof status are "
            "the biggest single-game weather variables."
        ),
        "betting_angle": (
            "GABP's built-in home run profile means small weather effects "
            "have outsized total impact. Warm humid nights with any "
            "component of wind blowing out are consistently mis-priced "
            "by season-averaging models."
        ),
    },
    "Milwaukee Brewers": {
        "slug": "milwaukee-brewers",
        "home_park": "American Family Field",
        "headline": "Milwaukee Brewers Weather Playbook: Retractable Roof, Lake Michigan Setting",
        "home_advantage": (
            "American Family Field closes the roof for the majority of "
            "games in April, May, September, and October because of cold, "
            "and for rain year-round. Closed conditions produce 72-degree "
            "indoor baseball with no wind. Open roof in warm summer months "
            "sees south wind and lake-influenced cooler baseline "
            "temperatures than inland Midwest."
        ),
        "road_challenges": (
            "NL Central road trips into Wrigley wind, GABP hitter-friendly "
            "Cincinnati, PNC Pittsburgh, and Busch Stadium St. Louis "
            "summer heat. Wrigley wind direction and GABP built-in home "
            "run environment are the main variables."
        ),
        "betting_angle": (
            "Roof status at American Family is the day-of-game leverage. "
            "Closed roof is neutral and stagnant; open roof on a warm "
            "humid night with south wind is the friendliest hitting "
            "conditions."
        ),
    },
    "Pittsburgh Pirates": {
        "slug": "pittsburgh-pirates",
        "home_park": "PNC Park",
        "headline": "Pittsburgh Pirates Weather Playbook: Allegheny River Wind, Division Environments",
        "home_advantage": (
            "PNC Park sits on the north bank of the Allegheny in downtown "
            "Pittsburgh. Southwest wind, funneled along the river from "
            "the west, blows out to left and center. River-valley "
            "channeling means wind at the field can differ from surface "
            "observations at Pittsburgh International, so ASOS reads a "
            "few miles away undershoot the wind at the field."
        ),
        "road_challenges": (
            "NL Central variance includes Wrigley wind, GABP hitter-"
            "friendly Cincinnati, Milwaukee retractable, and Busch "
            "Stadium St. Louis heat. Wrigley direction and Milwaukee roof "
            "are the biggest variables."
        ),
        "betting_angle": (
            "Southwest wind days at PNC with warm humid conditions "
            "produce the friendlier hitting environment. Right-field "
            "porch is close, so left-handed pull power benefits most "
            "from wind out to right."
        ),
    },
    "St. Louis Cardinals": {
        "slug": "st-louis-cardinals",
        "home_park": "Busch Stadium",
        "headline": "St. Louis Cardinals Weather Playbook: Midwest Heat, Mississippi Valley Setting",
        "home_advantage": (
            "Busch Stadium sits in downtown St. Louis a half mile from "
            "the Mississippi. Summer conditions are hot and humid with "
            "July averages around 90 degrees. South and southwest wind "
            "blows out to center and right. River-valley setting means "
            "wind at the field can differ from surface observations at "
            "STL a few miles west."
        ),
        "road_challenges": (
            "NL Central takes the Cardinals into Wrigley wind, GABP "
            "hitter-friendly Cincinnati, Milwaukee retractable, and PNC "
            "Park Pittsburgh river wind. Wrigley direction is the biggest "
            "day-of variable in the division."
        ),
        "betting_angle": (
            "Hot humid summer nights with south wind are the friendliest "
            "hitting conditions at Busch. Rain delays and evening "
            "thunderstorms in June through August shift start times and "
            "can invalidate morning-of forecasts."
        ),
    },
    "Arizona Diamondbacks": {
        "slug": "arizona-diamondbacks",
        "home_park": "Chase Field",
        "headline": "Arizona Diamondbacks Weather Playbook: Chase Field Roof, Phoenix Heat",
        "home_advantage": (
            "Chase Field closes the roof for the vast majority of home "
            "games May through September because of Phoenix heat. Closed "
            "conditions produce 72-degree indoor baseball with no wind. "
            "Open roof on cooler April, October, and shoulder-month "
            "evenings can produce extreme carry from the combination of "
            "warm dry air and low humidity."
        ),
        "road_challenges": (
            "NL West gives the D-backs Coors altitude, Dodger Stadium "
            "onshore, Petco marine, and Oracle Park bay wind. Coors is "
            "the largest single environmental variance in the division; "
            "Oracle cold-marine is the opposite extreme from Chase Field "
            "closed roof."
        ),
        "betting_angle": (
            "Assume closed roof for any Phoenix high above 100. Open roof "
            "on a hot dry night is the extreme-carry setup. Dry desert "
            "air with warm temperatures can push carry beyond humid-park "
            "baselines."
        ),
    },
    "Colorado Rockies": {
        "slug": "colorado-rockies",
        "home_park": "Coors Field",
        "headline": "Colorado Rockies Weather Playbook: Coors Altitude, Division Air Density",
        "home_advantage": (
            "Coors Field at 5,197 feet is the single most weather-affected "
            "park in the majors. Air density at that elevation is roughly "
            "82 percent of sea level, which drives the highest run "
            "environment in baseball regardless of surface weather. Warm "
            "dry afternoon and early-evening starts are the maximum-carry "
            "conditions. Rain-delayed or cool wet games are the only "
            "times Coors plays anywhere near neutral."
        ),
        "road_challenges": (
            "NL West gives the Rockies Chase Field roof-closed baseline, "
            "Dodger Stadium onshore, Petco marine, and Oracle Park bay "
            "wind. The team travels from the highest-altitude park to "
            "the densest sea-level marine air repeatedly."
        ),
        "betting_angle": (
            "Coors always plays higher than season-average totals "
            "suggest. Warm dry conditions push totals further up. The "
            "humidor still reduces carry compared to pre-2002 but the "
            "park remains the top run environment in baseball. Road "
            "Rockies games in dense marine air are the reverse trade."
        ),
    },
    "Los Angeles Dodgers": {
        "slug": "los-angeles-dodgers",
        "home_park": "Dodger Stadium",
        "headline": "Los Angeles Dodgers Weather Playbook: Chavez Ravine Consistency, Division Variance",
        "home_advantage": (
            "Dodger Stadium in Chavez Ravine plays consistent warm dry "
            "marine-influenced conditions night to night. Onshore "
            "southwest wind blows out toward left-center at typical 5 to "
            "12 mph. Dry air suppresses carry relative to humid parks. "
            "Santa Ana wind events in September and October reverse the "
            "pattern briefly with hot dry offshore flow."
        ),
        "road_challenges": (
            "NL West is the highest-air-density-variance division in "
            "baseball. Coors altitude, Chase Field closed roof, Petco "
            "marine, Oracle bay wind, and now Sutter Health Sacramento "
            "heat span the extremes of MLB weather environments."
        ),
        "betting_angle": (
            "Consistent conditions at Dodger Stadium make it easy to "
            "model. Santa Ana events are the leverage: hot dry offshore "
            "at 15-plus mph can push carry significantly above the park's "
            "usual profile. Road games in extreme environments require "
            "wider variance handicapping than home totals."
        ),
    },
    "San Diego Padres": {
        "slug": "san-diego-padres",
        "home_park": "Petco Park",
        "headline": "San Diego Padres Weather Playbook: Marine Layer, Bay Air, Division Air Density",
        "home_advantage": (
            "Petco Park sits a half mile from San Diego Bay. Summer "
            "conditions are mild and dry with July averages around 76 "
            "degrees. Marine layer cloud cover extends into afternoon on "
            "many days. Dense marine-influenced air is the reason Petco "
            "is one of the tougher home run environments in the majors."
        ),
        "road_challenges": (
            "NL West road trips into Coors altitude, Chase Field roof, "
            "Dodger Stadium onshore, Oracle bay wind, and Sutter Health "
            "Sacramento heat. Coors is the largest environmental swing "
            "the Padres experience."
        ),
        "betting_angle": (
            "Warm dry offshore-flow days in September and October are "
            "the only conditions that let Petco play as a live-hitting "
            "environment. Books that anchor to season averages "
            "under-adjust on those Santa Ana days."
        ),
    },
    "San Francisco Giants": {
        "slug": "san-francisco-giants",
        "home_park": "Oracle Park",
        "headline": "San Francisco Giants Weather Playbook: Oracle Wind, Bay Cold",
        "home_advantage": (
            "Oracle Park sits directly on San Francisco Bay. Strong "
            "westerly bay flow through the Golden Gate blows toward "
            "right field and McCovey Cove at 15 to 25 mph in typical "
            "summer conditions. Cold marine air combines with heavy "
            "wind to make Oracle one of the least favorable home run "
            "environments in the majors, particularly to left and "
            "center."
        ),
        "road_challenges": (
            "NL West gives the Giants Coors altitude, Chase Field roof, "
            "Dodger Stadium onshore, Petco marine, and Sutter Health "
            "Sacramento heat. The team travels from Oracle's cold marine "
            "extreme to Coors altitude extreme in a single division "
            "trip regularly."
        ),
        "betting_angle": (
            "Warm dry offshore September afternoons are the rare "
            "reversal at Oracle. The park favors pitching in virtually "
            "all typical weather. Road Giants games in warm humid or "
            "high-altitude parks are the reverse trade from home "
            "totals."
        ),
    },
}

TEAM_BY_SLUG = {c["slug"]: (name, c) for name, c in TEAM_CONTENT.items()}
