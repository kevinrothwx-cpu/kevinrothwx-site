"""
Per-park content blocks for /mlb/stadium/<slug> landing pages.

Each entry corresponds to a park in mlb/park_metadata.PARK_METADATA.
Content is intentionally verifiable: geographic facts, roof-type behavior,
climate norms for the region, and OVERcast historical data where Kevin has
uploaded it.

Rules for content:
- No em-dashes.
- No hedge language like "perhaps" or "notably."
- No game-outcome speculation.
- No claims about specific players or records unless verified.
- Wind direction language uses CF bearing from park_metadata.

Keys per park:
  slug              short URL slug
  headline          H1 for the page (park + city + weather angle)
  climate           one paragraph on regional climate in-season
  wind              one paragraph on how wind plays at this park
  roof_note         paragraph on roof behavior (empty if open-air)
  fantasy_note      one paragraph on what DFS/bettor should watch
  quick_facts       list of (label, value) tuples for the facts strip
"""

STADIUM_CONTENT = {
    "Fenway Park": {
        "slug": "fenway-park",
        "headline": "Fenway Park Weather: Wind, the Wall, and Boston's Coastal Climate",
        "climate": (
            "Fenway sits about a mile from Boston Harbor and roughly two miles "
            "from the open Atlantic at Nantasket. From April through September the "
            "park runs cool in the early months and warm-humid in July and August, "
            "with sea breezes from the east and southeast common on afternoon and "
            "evening games. Nighttime dew points climb into the mid-60s during "
            "typical summer stretches, and coastal fronts can drop temperatures "
            "10 to 15 degrees inside a single evening game."
        ),
        "wind": (
            "Center field is to the northeast (bearing about 45 degrees from home "
            "plate), so a straight southwest wind blows out to right and center. "
            "Northeast winds, common with coastal storms and sea breezes, blow "
            "straight in from center. The Green Monster in left is 37 feet tall "
            "and only 310 down the line, which changes how left-field wind reads "
            "on batted balls. Wind out to left at 10 mph can turn routine flies "
            "into wall-scrapers, and wind blowing in from left at the same speed "
            "kills what would otherwise be doubles off the Monster."
        ),
        "roof_note": "",
        "fantasy_note": (
            "Watch sea-breeze onset in day-night doubleheaders and afternoon starts. "
            "The wind can flip 90 degrees between first pitch and the seventh. "
            "Wind out to left plus warm humid air makes left-handed pull-power "
            "profiles the primary beneficiary. Cold northeast wind and low dew "
            "points are among the toughest hitting conditions in the majors."
        ),
    },

    "Yankee Stadium": {
        "slug": "yankee-stadium",
        "headline": "Yankee Stadium Weather: Short Porch, River Wind, Bronx Heat",
        "climate": (
            "The current Yankee Stadium opened in 2009 in the South Bronx, three "
            "quarters of a mile east of the Harlem River and roughly four miles "
            "from the harbor at Bay Ridge. Summer stretches are hot and humid, "
            "with LaGuardia recording July highs in the upper 80s on average and "
            "dew points frequently in the 60s to low 70s during evening games."
        ),
        "wind": (
            "Center field runs east (bearing about 80 degrees). West winds, the "
            "dominant summer flow behind cold fronts, blow straight out to center. "
            "The right-field porch is 314 feet and the wall is short. Wind out to "
            "right, common on afternoon games with river-channeled south flow, is "
            "the setup that turns lazy fly balls into home runs to right for "
            "left-handed hitters."
        ),
        "roof_note": "",
        "fantasy_note": (
            "Left-handed power hitters and the short-porch profile drive DFS "
            "leverage here. Wind out to right or straight to center, low humidity, "
            "and warm temps are the classic Yankee Stadium home run environment. "
            "Cool north wind in April and September pushes carry back sharply."
        ),
    },

    "Oriole Park at Camden Yards": {
        "slug": "oriole-park-at-camden-yards",
        "headline": "Camden Yards Weather: Bay Air, the New Left-Field Wall, Baltimore Summers",
        "climate": (
            "Camden Yards sits in downtown Baltimore about a mile and a half from "
            "the Patapsco. Summer weather is hot and muggy, with July averages "
            "around 88 degrees for highs at BWI and dew points routinely in the "
            "upper 60s. Afternoon thunderstorms from the Appalachian foothills "
            "reach the yard through late afternoon in June, July, and August."
        ),
        "wind": (
            "Center field is to the north-northeast (bearing 30 degrees). South "
            "and southwest winds blow out to center and right field. The park "
            "moved its left-field wall in for the 2025 season, restoring some of "
            "the home-run potential the 2022 changes had taken away. That change "
            "matters most on nights with wind out to left, when left-handed "
            "carry to the wall becomes the main story."
        ),
        "roof_note": "",
        "fantasy_note": (
            "Summer evenings with south wind and 70-plus dew points are the "
            "friendliest hitting conditions at Camden. Sea-breeze arrival from "
            "the Chesapeake can cool things down after 8 PM but also swing wind "
            "direction, so track hourly forecasts closely for late starts."
        ),
    },

    "Rogers Centre": {
        "slug": "rogers-centre",
        "headline": "Rogers Centre Weather: Retractable Roof and Toronto's Lakefront Climate",
        "climate": (
            "Rogers Centre sits on the north shore of Lake Ontario in downtown "
            "Toronto. The park is retractable-roofed. When the roof is open, "
            "lake-driven wind and cool spring temperatures play a major role. "
            "Early-season and late-season games are frequently played with the "
            "roof closed for cold. Midsummer, the roof opens more often for "
            "night games when the lake keeps temperatures moderate."
        ),
        "wind": (
            "With the roof open, wind at the field is heavily influenced by the "
            "lake to the south and by the downtown skyline that surrounds the "
            "park. Prevailing summer wind is from the southwest, which crosses "
            "the field from left to right. Cool north wind off the lake in April "
            "and September can drop temperatures and suppress carry."
        ),
        "roof_note": (
            "The roof is closed for most cold-weather games and for rain. Once "
            "closed, temperature settles into the low 70s and there is no wind. "
            "The Jays tend to open the roof for warm summer nights, which is "
            "when Rogers Centre plays as a live-hitting park."
        ),
        "fantasy_note": (
            "Roof status is the entire betting angle at Rogers Centre. Closed "
            "roof means neutral run environment, no wind, controlled temperature. "
            "Open roof with south wind and dew points above 60 is the run-scoring "
            "setup. The team publishes roof status the morning of first pitch."
        ),
    },

    "Tropicana Field": {
        "slug": "tropicana-field",
        "headline": "Tropicana Field Weather: Dome Baseball in St. Petersburg",
        "climate": (
            "Tropicana Field is a fixed dome in downtown St. Petersburg, six "
            "blocks from Tampa Bay. Outside conditions do not affect the field. "
            "Every game plays in air-conditioned 72-degree stillness."
        ),
        "wind": (
            "There is no wind at Tropicana Field. Batted balls fly through dry, "
            "static air. Home run distances are consistent from day to day, "
            "which makes the park easier to model than any outdoor stadium."
        ),
        "roof_note": (
            "The roof is permanent and non-operable. It has held up in multiple "
            "hurricanes, though structural inspections have been ongoing since "
            "Hurricane Milton in October 2024. Games are played there when the "
            "building is cleared as safe."
        ),
        "fantasy_note": (
            "Dome baseball removes weather variance entirely. No rain delays, "
            "no wind swings, no humidity spikes. Consistent 72 degrees indoors "
            "and stagnant air puts run scoring in a narrow, predictable band."
        ),
    },

    "Guaranteed Rate Field": {
        "slug": "guaranteed-rate-field",
        "headline": "Rate Field Weather: Chicago Wind, South Side Summers",
        "climate": (
            "The White Sox park sits about three miles south of downtown Chicago "
            "and roughly two miles from Lake Michigan. Chicago summers run "
            "warm-humid with July averages around 84 degrees at Midway. Lake "
            "breeze from the east arrives in the afternoon on many days and can "
            "drop temperatures sharply between first pitch and the sixth inning."
        ),
        "wind": (
            "Center field is to the east-northeast (bearing 45 degrees). West and "
            "southwest winds blow out to center and right, and lake breeze from "
            "the east blows straight in. The lake breeze effect is the story at "
            "this park: a stiff summer south wind at first pitch can flip to a "
            "10 mph east wind by the fifth inning."
        ),
        "roof_note": "",
        "fantasy_note": (
            "Lake-breeze timing determines the run environment. Afternoon games "
            "on warm humid days almost always see the breeze arrive, which kills "
            "carry after about 4 PM. Night games behind a warm-front push with "
            "south wind are the highest-scoring setups."
        ),
    },

    "Progressive Field": {
        "slug": "progressive-field",
        "headline": "Progressive Field Weather: Lake Erie Effect, Cleveland Summers",
        "climate": (
            "Progressive Field is in downtown Cleveland about six blocks from "
            "the Cuyahoga and less than a mile from Lake Erie. April and early "
            "May games regularly play in the 40s and 50s with lake-influenced "
            "wind. Midsummer runs warm with dew points in the mid-60s, cooler "
            "than most Midwest cities because of the lake."
        ),
        "wind": (
            "Center field is to the east (bearing 90 degrees). West wind blows "
            "straight out to center, and north wind off the lake blows across "
            "the field from left to right. The lake-effect setup can suppress "
            "carry by 5 to 10 degrees on evening games in April and May."
        ),
        "roof_note": "",
        "fantasy_note": (
            "Watch north wind and low dew points early in the season. Those "
            "combinations can knock 20 feet off fly balls. Warm humid nights "
            "with light south wind are the friendliest hitting conditions at "
            "Progressive."
        ),
    },

    "Comerica Park": {
        "slug": "comerica-park",
        "headline": "Comerica Park Weather: Detroit Summers, Deep Center Field",
        "climate": (
            "Comerica sits in downtown Detroit about a half mile from the river. "
            "Summer weather is warm and humid, though the Great Lakes keep the "
            "region cooler than typical Midwest inland cities. April and May "
            "games often start in the 50s. July averages around 84 degrees at "
            "Detroit Metro."
        ),
        "wind": (
            "Center field is to the north (bearing 15 degrees). South wind, the "
            "dominant summer flow, blows straight out to center. North wind off "
            "Lake Huron blows straight in. Center field is 420 feet deep, so "
            "wind effects on carry are magnified compared to shorter parks."
        ),
        "roof_note": "",
        "fantasy_note": (
            "The deep center-field configuration makes Comerica a below-average "
            "run environment on average. South wind at 12 mph or higher is what "
            "unlocks the park. North wind days are among the toughest for home "
            "run production."
        ),
    },

    "Kauffman Stadium": {
        "slug": "kauffman-stadium",
        "headline": "Kauffman Stadium Weather: Kansas City Heat, 2025 Fence Changes",
        "climate": (
            "Kauffman sits east of downtown Kansas City on the plains. Summer "
            "weather is hot with July averages around 90 degrees at KCI and "
            "dew points regularly in the upper 60s. Afternoon and evening "
            "thunderstorms from cold-front passages are common."
        ),
        "wind": (
            "Center field is to the northeast (bearing 55 degrees). South and "
            "southwest wind, the dominant summer flow across the plains, blows "
            "out to left and center. The park runs open on all sides, so wind "
            "reaches the field almost undisturbed. Wind speed at Kauffman "
            "regularly reaches 15 to 20 mph in the afternoon."
        ),
        "roof_note": "",
        "fantasy_note": (
            "The Royals moved fences in for the 2025 season, taking Kauffman "
            "from a pitcher's park closer to neutral. That combined with south "
            "wind at 15-plus and warm humid air produces the highest scoring "
            "conditions the park sees. Cold north wind days remain suppressive."
        ),
    },

    "Target Field": {
        "slug": "target-field",
        "headline": "Target Field Weather: Minneapolis Cold Snaps, Prairie Wind",
        "climate": (
            "Target Field opened in 2010 in downtown Minneapolis. April games "
            "regularly play in the 40s, and snow delays are possible in early "
            "season. Midsummer is warm and can be humid, but dew points swing "
            "widely depending on air mass. September nights turn cold quickly."
        ),
        "wind": (
            "Center field is to the northeast (bearing 45 degrees). Southwest "
            "wind blows out to center and right. North wind blows straight in "
            "from center. The Twins park runs windier than average because of "
            "downtown Minneapolis channeling."
        ),
        "roof_note": "",
        "fantasy_note": (
            "Watch dew point more than temperature. A 75-degree game with a "
            "dew point in the 40s plays like a mid-60s game for ball carry. "
            "Warm humid nights with south wind are the run-scoring setup here."
        ),
    },

    "Minute Maid Park": {
        "slug": "minute-maid-park",
        "headline": "Minute Maid Park Weather: Retractable Roof and Houston Heat",
        "climate": (
            "Minute Maid sits in downtown Houston. Summer conditions are extreme: "
            "July averages around 94 degrees with dew points in the low to "
            "mid-70s. That combination pushes heat index above 100 through most "
            "of June, July, and August afternoons and evenings."
        ),
        "wind": (
            "With the roof closed, no wind. With the roof open, the park is in "
            "the middle of downtown Houston with limited natural wind reaching "
            "the field. When the roof is open, batted balls fly farther because "
            "warm humid air is less dense than dry air at the same temperature."
        ),
        "roof_note": (
            "The roof is closed for the majority of Astros home games from mid-May "
            "through September because of heat. When closed, the park plays at "
            "72 degrees with no wind. The roof opens more often in April, "
            "October, and cooler April and May evenings."
        ),
        "fantasy_note": (
            "Roof status is the primary weather angle in Houston. Closed roof "
            "removes wind and locks temperature. Open roof on a warm humid night "
            "is the friendliest hitting condition. Track roof status the day of "
            "the game; the Astros typically confirm about three hours before "
            "first pitch."
        ),
    },

    "Angel Stadium": {
        "slug": "angel-stadium",
        "headline": "Angel Stadium Weather: Anaheim's Marine Layer and Dry Heat",
        "climate": (
            "Angel Stadium sits in Anaheim about 12 miles inland from Huntington "
            "Beach. Summer weather is warm and dry: July averages around 85 "
            "degrees with dew points in the low 60s. Marine-layer clouds and "
            "onshore flow keep evenings cool relative to inland Southern "
            "California cities."
        ),
        "wind": (
            "Center field is to the northeast (bearing 30 degrees). Onshore "
            "southwest wind, the dominant afternoon flow, blows out toward "
            "left-center and center. Wind speed rarely exceeds 12 mph. The park "
            "plays as a mild pitcher's park in dry marine air."
        ),
        "roof_note": "",
        "fantasy_note": (
            "Consistent conditions night to night make Angel Stadium easy to "
            "model. Dry air and cool onshore breeze suppress carry versus humid "
            "parks. Santa Ana wind events, which happen in September and October, "
            "reverse the pattern with hot dry offshore flow."
        ),
    },

    "Oakland Coliseum": {
        "slug": "oakland-coliseum",
        "headline": "Oakland Coliseum Weather: Bay Wind, Marine Air, Deep Foul Ground",
        "climate": (
            "The Coliseum sits about a mile from San Francisco Bay in Oakland. "
            "Summer conditions are cool and windy: July averages around 74 "
            "degrees with strong onshore flow. Marine-layer stratus is common "
            "for morning and evening games. Dew points stay in the 50s."
        ),
        "wind": (
            "Center field is to the east-southeast. Strong westerly bay wind, "
            "channeled through the Golden Gate and the Bay, blows out to left "
            "and left-center during typical summer afternoons. Wind speed of "
            "15 to 25 mph is common in July."
        ),
        "roof_note": "",
        "fantasy_note": (
            "Oakland pairs cold marine air with big foul ground and heavy wind "
            "to left. Wind out to left with warm afternoon temps is the only "
            "reliably friendly hitting environment. Cool foggy nights are among "
            "the toughest offensive settings in the majors."
        ),
    },

    "T-Mobile Park": {
        "slug": "t-mobile-park",
        "headline": "T-Mobile Park Weather: Seattle's Retractable Roof and Marine Climate",
        "climate": (
            "T-Mobile Park sits in downtown Seattle about a half mile from Elliott "
            "Bay. Summer weather is mild and often dry: July averages around 78 "
            "degrees at Sea-Tac with dew points in the low to mid-50s. Marine "
            "air keeps carry lower than warmer humid parks even on clear nights."
        ),
        "wind": (
            "Center field is to the east-northeast. Onshore westerly wind blows "
            "out to center and right. Wind speed is generally light, 5 to 12 mph "
            "for typical evening games."
        ),
        "roof_note": (
            "The roof at T-Mobile is not a full enclosure. It slides overhead "
            "but leaves the sides open, so wind and outside air still reach the "
            "field even with the roof deployed. It is used primarily as a rain "
            "cover. Games played with the roof closed still see outdoor "
            "temperatures and wind at the field, unlike Rogers Centre or "
            "Minute Maid."
        ),
        "fantasy_note": (
            "Marine-air-cool nights and low dew points make T-Mobile one of the "
            "harder home run environments in the majors. Warm dry stretches in "
            "late July and August are the friendliest window. Rain delays and "
            "roof closures do not change the temperature or wind materially."
        ),
    },

    "Globe Life Field": {
        "slug": "globe-life-field",
        "headline": "Globe Life Field Weather: Texas Heat and a Retractable Roof",
        "climate": (
            "Globe Life Field opened in 2020 in Arlington. Summer heat is extreme: "
            "July averages around 96 degrees at DFW with dew points in the mid-60s. "
            "The old open-air Globe Life Park nearby saw 100-plus heat index "
            "regularly. The new park was built with a retractable roof to allow "
            "climate control for those conditions."
        ),
        "wind": (
            "With the roof closed, no wind. With the roof open, prevailing summer "
            "wind is from the south. The park is engineered so that even with "
            "the roof open, wind at the field is muted relative to the outdoor "
            "flow."
        ),
        "roof_note": (
            "The Rangers close the roof for the majority of home games during "
            "the summer to manage heat. Closed conditions run around 72 degrees "
            "with no wind. The roof opens more often in April, September, and "
            "October when outside temperatures are moderate."
        ),
        "fantasy_note": (
            "Closed roof produces neutral, wind-free conditions. Open roof on a "
            "warm night with south wind is the run-scoring setup. Roof status "
            "is announced day of game; assume closed on any day with heat index "
            "above 95."
        ),
    },

    "Truist Park": {
        "slug": "truist-park",
        "headline": "Truist Park Weather: Atlanta Summers, Cobb County Setting",
        "climate": (
            "Truist Park sits in Cumberland north of downtown Atlanta. Summer "
            "conditions run hot and humid: July averages around 89 degrees at "
            "Hartsfield with dew points frequently in the low 70s. Afternoon "
            "thunderstorms from the southern Appalachians reach the park through "
            "early evening from June through August."
        ),
        "wind": (
            "Center field is to the north-northeast (bearing 25 degrees). "
            "Southwest wind, the summer default, blows out to center and right. "
            "The surrounding hills around Cumberland limit wind speed at the "
            "field to typically 8 to 12 mph."
        ),
        "roof_note": "",
        "fantasy_note": (
            "Warm humid air and south wind combine into strong carry conditions "
            "throughout Atlanta summer. Rain delays and evening thunderstorm "
            "risk are the main variance. Watch the radar closely for late "
            "afternoon games in July and August."
        ),
    },

    "Wrigley Field": {
        "slug": "wrigley-field",
        "headline": "Wrigley Field Weather: Lake Michigan Wind, the Ivy, Chicago Summers",
        "climate": (
            "Wrigley sits in the Lakeview neighborhood a half mile from Lake "
            "Michigan. That proximity to the lake is the entire weather story "
            "at Wrigley. Lake temperature holds well into the 40s through late "
            "May, which cools onshore wind and keeps carry down early in the "
            "season. Midsummer, once the lake warms, the effect softens."
        ),
        "wind": (
            "Center field is to the northeast (bearing 50 degrees). Southwest "
            "wind blows straight out to center and right. Northeast wind off "
            "the lake blows straight in. Wrigley is the most wind-susceptible "
            "park in the majors because of the open sightlines on all sides "
            "and the tall buildings on Sheffield and Waveland that channel "
            "flow. Wind out at 15 mph turns Wrigley into a bandbox. Wind in at "
            "15 mph produces some of the lowest-scoring baseball anywhere."
        ),
        "roof_note": "",
        "fantasy_note": (
            "Wind direction is the single most important weather variable at "
            "Wrigley. Total lines swing 1.5 to 2 runs based on wind alone. "
            "Read the direction and speed at the field-level ASOS at Meigs "
            "Field or Midway, not surface observations from farther away, "
            "for the tightest reads before first pitch."
        ),
    },

    "loanDepot park": {
        "slug": "loandepot-park",
        "headline": "loanDepot park Weather: Miami's Heat, Humidity, and Retractable Roof",
        "climate": (
            "loanDepot park sits in Little Havana about five miles inland from "
            "Biscayne Bay. Summer weather is hot, humid, and rainy: July averages "
            "around 90 degrees with dew points routinely at 75 or above. "
            "Afternoon thunderstorm chance is 40 to 60 percent daily from June "
            "through September."
        ),
        "wind": (
            "With the roof closed, no wind. With the roof open, sea-breeze flow "
            "from the east is the dominant summer pattern, but the roof stays "
            "closed on most home dates because of heat and rain."
        ),
        "roof_note": (
            "The Marlins close the roof for the majority of home games during "
            "the summer because of heat and rain. Closed conditions run around "
            "72 degrees with no wind. The roof opens more often in April and "
            "October when heat and rain risk are lower."
        ),
        "fantasy_note": (
            "Closed roof produces predictable neutral scoring conditions. Open "
            "roof on a hot humid night with sea-breeze onshore wind is the "
            "highest-carry setup. Track the team's roof announcement day of "
            "game; assume closed if forecast rain probability is above 40 "
            "percent."
        ),
    },

    "Citi Field": {
        "slug": "citi-field",
        "headline": "Citi Field Weather: Queens Coastal Setting, Deep Right-Center",
        "climate": (
            "Citi Field sits in Flushing, Queens, adjacent to Flushing Bay and "
            "less than a mile from LaGuardia. Summer conditions are hot humid "
            "with July averages in the upper 80s and dew points in the 60s and "
            "low 70s. Coastal fronts and sea breeze are common weather features "
            "for afternoon and evening games."
        ),
        "wind": (
            "Center field is to the east. Southwest wind blows out to center. "
            "Sea breeze from the east and southeast blows straight in from "
            "center. Right-center at Citi is 385 feet deep, so wind effects "
            "there are magnified on batted balls that would carry to right "
            "field in shorter parks."
        ),
        "roof_note": "",
        "fantasy_note": (
            "Wind direction relative to right-center is the leverage at Citi. "
            "Southwest wind at 12-plus mph combined with warm humid air are "
            "the highest-scoring conditions. Sea-breeze reversal in the sixth "
            "or seventh inning can flip a good hitting environment into a "
            "carry-suppressing one."
        ),
    },

    "Citizens Bank Park": {
        "slug": "citizens-bank-park",
        "headline": "Citizens Bank Park Weather: Philadelphia Summers, Hitter-Friendly Dimensions",
        "climate": (
            "The Phillies' park sits in South Philadelphia about three miles "
            "from the Delaware River. Summer weather is hot and humid: July "
            "averages around 87 degrees at PHL with dew points in the mid to "
            "upper 60s. Afternoon thunderstorms are common in June, July, and "
            "August."
        ),
        "wind": (
            "Center field is to the northeast. Southwest wind, the summer "
            "default, blows out to left-center and center. The park's "
            "dimensions favor pull-side power for both hands, so wind out to "
            "either corner amplifies the built-in hitter-friendly setup."
        ),
        "roof_note": "",
        "fantasy_note": (
            "Warm humid nights with southwest wind are the highest run "
            "environments at Citizens Bank. Cold-front north wind days are "
            "the main downside. The park runs above league average for home "
            "runs in most conditions."
        ),
    },

    "Nationals Park": {
        "slug": "nationals-park",
        "headline": "Nationals Park Weather: DC Humidity, the Anacostia River",
        "climate": (
            "Nationals Park sits on the north bank of the Anacostia in Southeast "
            "DC. Summer conditions are hot and humid: July averages around 88 "
            "degrees at DCA with dew points in the upper 60s. Afternoon "
            "thunderstorm risk is high through July and August."
        ),
        "wind": (
            "Center field is to the north-northeast. South wind blows out to "
            "center and right. North wind blows in from center. The Anacostia "
            "channels flow slightly along the river axis, but the effect is "
            "small compared to lakefront parks."
        ),
        "roof_note": "",
        "fantasy_note": (
            "Warm humid summer nights with south wind produce the friendliest "
            "hitting conditions. Rain delays and thunderstorm risk are the main "
            "variance to track for June through August home games."
        ),
    },

    "Great American Ball Park": {
        "slug": "great-american-ball-park",
        "headline": "Great American Ball Park Weather: Ohio River Wind, Cincinnati Summers",
        "climate": (
            "GABP sits on the north bank of the Ohio River in downtown "
            "Cincinnati. Summer weather is warm and humid: July averages around "
            "87 degrees at CVG with dew points in the mid to upper 60s."
        ),
        "wind": (
            "Center field is to the northeast. Southwest wind, the summer "
            "default, blows out to center and right. Cross-winds along the "
            "river axis are common. GABP is one of the friendliest home run "
            "parks in the majors regardless of wind, and wind out to right on "
            "a warm humid night pushes it into elite scoring territory."
        ),
        "roof_note": "",
        "fantasy_note": (
            "GABP consistently ranks near the top of MLB parks for run "
            "environment. Warm humid nights with any wind component blowing "
            "out are the strongest hitting conditions. Cold north wind days "
            "are the only condition where the park plays neutral."
        ),
    },

    "Coors Field": {
        "slug": "coors-field",
        "headline": "Coors Field Weather: Denver Altitude, Thin Air, Afternoon Storms",
        "climate": (
            "Coors sits at 5,197 feet in downtown Denver. Air density at that "
            "elevation is roughly 82 percent of sea-level density, which is "
            "the entire reason Coors plays as the highest-scoring park in the "
            "majors. Summer daytime highs run in the mid-80s and low-90s at "
            "DIA. Afternoon thunderstorms from the front range reach downtown "
            "through evening in June, July, and August."
        ),
        "wind": (
            "Center field is to the northeast (bearing 35 degrees). Wind at "
            "Coors matters less than at any other park because the altitude "
            "effect dwarfs wind effects on carry. That said, downslope west "
            "wind and warm dry conditions push carry to its maximum. Cool wet "
            "conditions with north or east wind produce Coors's tamer hitting "
            "nights."
        ),
        "roof_note": "",
        "fantasy_note": (
            "Coors is the single most important weather-affected park in the "
            "majors. Warm dry afternoon and early-evening starts are the "
            "maximum-carry conditions. Rain-delayed or cool wet games are the "
            "only times Coors plays anywhere near neutral. The humidor still "
            "reduces carry compared to pre-2002 conditions but the park remains "
            "the top run environment."
        ),
    },

    "American Family Field": {
        "slug": "american-family-field",
        "headline": "American Family Field Weather: Milwaukee Wind, Retractable Roof",
        "climate": (
            "American Family Field sits in Milwaukee about three miles from "
            "Lake Michigan. Summer weather is cool relative to inland Midwest: "
            "July averages around 80 degrees at MKE with dew points in the low "
            "to mid-60s. Lake breeze is common in the afternoon."
        ),
        "wind": (
            "With the roof closed, no wind. With the roof open, prevailing "
            "summer wind is from the south and southwest. The park was designed "
            "with a fan-shaped roof that leaves the outfield exposed to sky "
            "when partially open."
        ),
        "roof_note": (
            "The Brewers close the roof for the majority of games from April "
            "through May and again in September and October because of cold, "
            "and for rain year-round. Closed conditions run around 72 degrees "
            "with no wind. The roof opens more often in June, July, and August "
            "for warm evening games."
        ),
        "fantasy_note": (
            "Roof status defines the run environment. Closed roof is neutral "
            "and stagnant. Open roof on a warm humid night with south wind "
            "is the friendliest hitting condition. Track roof status day of "
            "game."
        ),
    },

    "PNC Park": {
        "slug": "pnc-park",
        "headline": "PNC Park Weather: Allegheny River Wind, Pittsburgh Summers",
        "climate": (
            "PNC Park sits on the north bank of the Allegheny in downtown "
            "Pittsburgh. Summer weather is warm and humid: July averages "
            "around 84 degrees at PIT with dew points in the mid-60s."
        ),
        "wind": (
            "Center field is to the northeast (bearing 55 degrees). Southwest "
            "wind, funneled along the river from the west, blows out to left "
            "and center. Wind at PNC is often channeled by the river valley, "
            "which makes ground-level readings differ from higher-elevation "
            "surface observations."
        ),
        "roof_note": "",
        "fantasy_note": (
            "Southwest wind days combined with warm humid conditions are the "
            "friendlier hitting environment. The park's right-field wall is "
            "close, so left-handed pull power is the primary beneficiary of "
            "wind out to right."
        ),
    },

    "Busch Stadium": {
        "slug": "busch-stadium",
        "headline": "Busch Stadium Weather: St. Louis Heat, Mississippi Valley Setting",
        "climate": (
            "Busch Stadium sits in downtown St. Louis about a half mile from "
            "the Mississippi. Summer weather is hot and humid: July averages "
            "around 90 degrees at STL with dew points in the low 70s. "
            "Afternoon thunderstorms from cold-front passages are common."
        ),
        "wind": (
            "Center field is to the north-northeast (bearing 25 degrees). "
            "South and southwest wind, the summer default, blows out to center "
            "and right. The park's setting near the river valley means wind at "
            "the field can differ from surface observations at STL a few miles "
            "west."
        ),
        "roof_note": "",
        "fantasy_note": (
            "Hot humid summer nights with south wind are the friendliest "
            "hitting conditions. Watch for evening thunderstorms in June, "
            "July, and August; rain-delayed games can shift start times "
            "past the freshest wind."
        ),
    },

    "Chase Field": {
        "slug": "chase-field",
        "headline": "Chase Field Weather: Phoenix Heat and a Retractable Roof",
        "climate": (
            "Chase Field sits in downtown Phoenix. Summer heat is extreme: July "
            "and August averages run 105 to 107 degrees at Sky Harbor with dew "
            "points that rise into the 60s during monsoon season from July "
            "into September. The park was built with a retractable roof "
            "specifically to make baseball viable in that climate."
        ),
        "wind": (
            "With the roof closed, no wind. With the roof open, the surrounding "
            "downtown limits natural wind reaching the field. Monsoon "
            "thunderstorm outflows can push short-lived gusts through Phoenix "
            "in the evening from July into September."
        ),
        "roof_note": (
            "The Diamondbacks close the roof for the vast majority of home "
            "games from May through September because of heat. Closed "
            "conditions run around 72 degrees with no wind. The roof opens "
            "more often in April, October, and cooler April and early May "
            "evenings."
        ),
        "fantasy_note": (
            "Closed roof produces predictable neutral conditions. Open roof "
            "on a hot dry night can produce extreme carry because of the "
            "combination of low humidity and warm temperatures. Roof status "
            "is confirmed day of game; assume closed for any day with high "
            "above 100."
        ),
    },

    "Dodger Stadium": {
        "slug": "dodger-stadium",
        "headline": "Dodger Stadium Weather: Chavez Ravine Marine Air, Dry Heat",
        "climate": (
            "Dodger Stadium sits in Chavez Ravine north of downtown Los "
            "Angeles. Summer weather is warm and dry: July averages around "
            "84 degrees at Downtown LA with dew points in the low 60s. Marine "
            "layer influences morning and evening conditions from May through "
            "August."
        ),
        "wind": (
            "Center field is to the north-northeast. Onshore southwest wind, "
            "the afternoon default, blows out toward left-center. Wind at "
            "Dodger Stadium is generally light, 5 to 12 mph, and consistent."
        ),
        "roof_note": "",
        "fantasy_note": (
            "Consistent conditions night to night make Dodger Stadium easy "
            "to model. Dry air suppresses carry compared to humid parks, "
            "which contributes to the park's slight pitcher's lean. Santa "
            "Ana wind events in September and October reverse the pattern "
            "with hot dry offshore flow."
        ),
    },

    "Petco Park": {
        "slug": "petco-park",
        "headline": "Petco Park Weather: San Diego Marine Layer, Bay Air",
        "climate": (
            "Petco Park sits in downtown San Diego a half mile from the bay. "
            "Summer weather is mild and dry: July averages around 76 degrees "
            "at San Diego Airport with dew points in the low 60s. Marine "
            "layer cloud cover extends into afternoon on many days from May "
            "through August."
        ),
        "wind": (
            "Center field is to the northeast. Onshore southwest wind, the "
            "default afternoon pattern, blows out toward left-center. Wind "
            "at Petco is typically light, 6 to 12 mph. The marine-influenced "
            "air is dense and cool, which suppresses carry."
        ),
        "roof_note": "",
        "fantasy_note": (
            "Petco is one of the tougher home run environments in the majors "
            "because of dense marine air. Warm dry offshore-flow days in "
            "September and October are the only conditions that let the "
            "park play as a live-hitting environment."
        ),
    },

    "Oracle Park": {
        "slug": "oracle-park",
        "headline": "Oracle Park Weather: Bay Wind, Fog, and McCovey Cove",
        "climate": (
            "Oracle Park sits on the south side of downtown San Francisco "
            "directly on the bay. Summer weather is cold and windy: July "
            "averages around 68 degrees at SFO with dew points in the low "
            "50s. Marine-layer fog and stratus are common through morning "
            "and afternoon and often persist into evening games."
        ),
        "wind": (
            "Wind at Oracle is the defining feature of the park. Strong "
            "westerly bay flow, channeled through the Golden Gate, blows "
            "toward right field and McCovey Cove. Wind speed of 15 to 25 mph "
            "is common in July and August. Cold air and heavy carry-"
            "suppressing conditions combine to make Oracle one of the "
            "least favorable home run environments in the majors, "
            "particularly to left and center."
        ),
        "roof_note": "",
        "fantasy_note": (
            "Cold marine air and strong wind blowing toward right are the "
            "consistent conditions at Oracle. Warm dry September afternoons "
            "with offshore flow are the rare exceptions. The park favors "
            "pitching in virtually all typical weather."
        ),
    },

    "Sutter Health Park": {
        "slug": "sutter-health-park",
        "headline": "Sutter Health Park Weather: Sacramento Heat, the A's Temporary Home",
        "climate": (
            "Sutter Health Park sits in West Sacramento about 90 miles inland "
            "from the Bay. Summer weather is dry and hot: July averages around "
            "94 degrees with dew points in the 50s. Delta breeze from the west "
            "arrives in the afternoon and evening, dropping temperatures and "
            "picking up wind."
        ),
        "wind": (
            "The park was built as a minor-league facility. Delta breeze from "
            "the west, the dominant late-afternoon pattern in Sacramento "
            "summer, blows across the field and can reach 15 to 20 mph. "
            "Dry hot afternoons before the breeze arrives are the highest-"
            "carry conditions."
        ),
        "roof_note": "",
        "fantasy_note": (
            "This is the A's temporary home during their transition to Las "
            "Vegas. Delta breeze onset timing is the primary weather angle. "
            "Games starting before 7 PM can play in warm still air; late "
            "starts play in stiff westerly wind. Hot dry conditions with "
            "still air produce the best hitting environment."
        ),
    },
}

# Slug reverse lookup for URL routing
STADIUM_BY_SLUG = {c["slug"]: (name, c) for name, c in STADIUM_CONTENT.items()}
