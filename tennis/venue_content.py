"""Per-Grand-Slam venue content for /tennis/venue/<slug> landing pages.

Four Grand Slam venues with evergreen weather guides. Anchored in
verifiable facts: venue location, tournament window, weather angle
during the tournament. No specific climatology numbers I can't source.
"""

VENUE_CONTENT = {
    "wimbledon": {
        "slug": "all-england-club",
        "name": "The All England Club",
        "location": "Wimbledon, London, England",
        "tournament": "Wimbledon",
        "window": "Late June through mid-July",
        "headline": "Wimbledon Weather Guide: The All England Club and English Grass Court Conditions",
        "climate": "Wimbledon is played on grass in southwest London. English summer conditions bring mild temperatures with elevated rain risk. Passing showers and cloudy conditions are common features of the tournament. Center Court and Court No. 1 both have retractable roofs; outer courts play open-air.",
        "angle": "Rain is the defining Wimbledon weather variable. Roof status on Center Court and Court No. 1 determines whether marquee matches continue uninterrupted. Outer-court matches suspend during any measurable precipitation. Grass surface responds to moisture — slippery footing after showers changes match dynamics through the drying period."},
    "us-open": {
        "slug": "billie-jean-king-national-tennis-center",
        "name": "USTA Billie Jean King National Tennis Center",
        "location": "Flushing Meadows, Queens, New York",
        "tournament": "US Open",
        "window": "Late August through early September",
        "headline": "US Open Weather Guide: Flushing Meadows Late-Summer Heat and Coastal Rain",
        "climate": "The US Open is played on hard courts in Flushing Meadows, Queens. Late-summer New York conditions bring hot humid days with elevated afternoon thunderstorm risk. Arthur Ashe Stadium and Louis Armstrong Stadium both have retractable roofs. Outer courts are open-air.",
        "angle": "Heat index is a significant player-endurance variable in early-round day sessions. Tropical-system remnants can force schedule shifts in September. Roof status on Ashe and Armstrong keeps night matches on schedule during storms; outer courts suspend for any measurable rain."},
    "roland-garros": {
        "slug": "stade-roland-garros",
        "name": "Stade Roland-Garros",
        "location": "Paris, France",
        "tournament": "French Open",
        "window": "Late May through early June",
        "headline": "Roland-Garros Weather Guide: Paris Late-Spring Clay Court Conditions",
        "climate": "Roland-Garros is played on red clay in western Paris. Late-spring French conditions bring mild variable temperatures with rain risk. Court Philippe-Chatrier has a retractable roof; Suzanne-Lenglen also has a roof. Outer courts play open-air.",
        "angle": "Rain is the defining variable at Roland-Garros because clay drains slowly and matches suspend readily. Heavy clay after rain plays slower, favors baseline grinders, and rewards defensive play. Roof status on the two show courts keeps marquee matches on schedule; outer-court delays cascade through the day's order of play."},
    "australian-open": {
        "slug": "melbourne-park",
        "name": "Melbourne Park",
        "location": "Melbourne, Victoria, Australia",
        "tournament": "Australian Open",
        "window": "Mid-January through late January",
        "headline": "Australian Open Weather Guide: Melbourne Park Summer Heat",
        "climate": "The Australian Open is played on hard courts in Melbourne during Southern Hemisphere summer. Extreme heat is common — heat index above 100 has forced suspension in past tournaments. Rod Laver Arena, Margaret Court Arena, and John Cain Arena all have retractable roofs.",
        "angle": "Extreme heat and the Extreme Heat Policy are the defining Australian Open weather considerations. Roof status on the three show courts allows matches to continue when outer courts suspend for heat. Rain is less frequent than at Wimbledon or Roland-Garros but can still occur through the tournament."},
}

VENUE_BY_SLUG_TENNIS = {c["slug"]: (name, c) for name, c in VENUE_CONTENT.items()}
