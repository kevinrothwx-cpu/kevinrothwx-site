"""Per-franchise + per-ground content for IPL landing pages.

10 IPL franchises with primary home grounds. Cricket season runs late
March through late May. Content anchored to verifiable facts: city,
ground name, capacity, seasonal weather reputation for the region.
"""

TEAM_CONTENT_IPL = {
    "Chennai Super Kings": {"slug": "chennai-super-kings", "abbrev": "CSK",
        "ground": "M. A. Chidambaram Stadium", "city": "Chennai", "capacity": 50000,
        "headline": "Chennai Super Kings Weather Playbook: Chepauk Stadium and Chennai Heat",
        "home": "Chennai Super Kings play at M. A. Chidambaram Stadium (Chepauk) in Chennai on the Tamil Nadu coast. Open-air setting with extreme summer heat and humidity during IPL season. Coastal proximity brings sea-breeze relief in evenings but high dew point conditions.",
        "road": "IPL road environments span dry inland heat at Delhi and Punjab, humid Kolkata, coastal Mumbai humidity, high-altitude Bengaluru, and Ahmedabad dry heat.",
        "angle": "Chennai heat and humidity are the defining home conditions. Dew factor during evening matches is a significant tactical variable that affects ball movement and grip. Coastal storm risk exists in late April and May."},
    "Mumbai Indians": {"slug": "mumbai-indians", "abbrev": "MI",
        "ground": "Wankhede Stadium", "city": "Mumbai", "capacity": 33108,
        "headline": "Mumbai Indians Weather Playbook: Wankhede Stadium and Mumbai Coastal Setting",
        "home": "Mumbai Indians play at Wankhede Stadium in South Mumbai on the Arabian Sea coast. Open-air venue with extreme humidity through IPL season. Sea-breeze influence from the west affects match conditions.",
        "road": "IPL road environments span dry inland Delhi and Punjab heat, humid Kolkata coast, Chennai coastal humidity, Bengaluru elevation, Ahmedabad dry heat.",
        "angle": "Mumbai humidity is extreme. Dew factor during evening matches significantly affects ball grip and swing. Late-season pre-monsoon conditions can bring elevated storm risk."},
    "Royal Challengers Bengaluru": {"slug": "royal-challengers-bengaluru", "abbrev": "RCB",
        "ground": "M. Chinnaswamy Stadium", "city": "Bengaluru", "capacity": 40000,
        "headline": "Royal Challengers Bengaluru Weather Playbook: M. Chinnaswamy Stadium and Bengaluru Elevation",
        "home": "Royal Challengers Bengaluru play at M. Chinnaswamy Stadium in central Bengaluru at approximately 3,000 feet of elevation. Open-air setting with moderate temperatures relative to other IPL venues due to the elevation.",
        "road": "IPL road environments span extreme coastal humidity at Mumbai and Chennai, dry inland heat at Delhi and Punjab, Kolkata humidity, and Ahmedabad dry heat.",
        "angle": "Bengaluru elevation keeps conditions milder than most IPL venues. Pre-monsoon showers from mid-April onward are the primary weather variable. Ball movement in cooler evening conditions is a factor."},
    "Kolkata Knight Riders": {"slug": "kolkata-knight-riders", "abbrev": "KKR",
        "ground": "Eden Gardens", "city": "Kolkata", "capacity": 68000,
        "headline": "Kolkata Knight Riders Weather Playbook: Eden Gardens and Bengal Humidity",
        "home": "Kolkata Knight Riders play at Eden Gardens in central Kolkata. Historic ground with one of the largest capacities in world cricket. Open-air West Bengal setting with elevated humidity and pre-monsoon storm risk in late April and May.",
        "road": "IPL road environments span coastal Mumbai and Chennai humidity, dry inland Delhi and Punjab heat, Bengaluru elevation, Ahmedabad dry heat.",
        "angle": "Bengal humidity and pre-monsoon storm risk are the defining variables. Late-season nor'wester storms (Kalbaisakhi) can force delays. Dew factor affects evening match conditions."},
    "Sunrisers Hyderabad": {"slug": "sunrisers-hyderabad", "abbrev": "SRH",
        "ground": "Rajiv Gandhi International Cricket Stadium", "city": "Hyderabad", "capacity": 55000,
        "headline": "Sunrisers Hyderabad Weather Playbook: Rajiv Gandhi International Stadium",
        "home": "Sunrisers Hyderabad play at Rajiv Gandhi International Cricket Stadium in Hyderabad. Open-air Deccan Plateau setting with warm dry conditions predominating during IPL season. Elevation of approximately 1,600 feet provides moderate relief.",
        "road": "IPL road environments span coastal Mumbai and Chennai humidity, dry inland Delhi and Punjab, Bengaluru elevation, Kolkata humidity.",
        "angle": "Deccan Plateau conditions are drier than coastal venues. Pre-monsoon storm risk from mid-April onward is elevated. Evening matches see less dew factor than coastal venues."},
    "Delhi Capitals": {"slug": "delhi-capitals", "abbrev": "DC",
        "ground": "Arun Jaitley Stadium", "city": "New Delhi", "capacity": 41842,
        "headline": "Delhi Capitals Weather Playbook: Arun Jaitley Stadium and Delhi Extreme Heat",
        "home": "Delhi Capitals play at Arun Jaitley Stadium (Feroz Shah Kotla) in Old Delhi. Open-air North India setting with extreme summer heat during IPL season. Loo winds from the west bring hot dry conditions that reach dangerous levels in May.",
        "road": "IPL road environments span coastal Mumbai and Chennai humidity, Kolkata pre-monsoon storms, Bengaluru elevation, Ahmedabad dry heat.",
        "angle": "Extreme Delhi heat is the defining variable. May matches see afternoon temperatures well over 40°C. Dust storms and pre-monsoon thunderstorms are elevated risk from mid-April onward."},
    "Punjab Kings": {"slug": "punjab-kings", "abbrev": "PBKS",
        "ground": "Punjab Cricket Association IS Bindra Stadium", "city": "Mohali", "capacity": 26950,
        "headline": "Punjab Kings Weather Playbook: PCA Stadium Mohali and Punjab Climate",
        "home": "Punjab Kings play primary home matches at PCA IS Bindra Stadium in Mohali near Chandigarh, with secondary venue at HPCA Stadium in Dharamshala. Punjab plains setting with warm dry conditions early season and pre-monsoon variability by May.",
        "road": "IPL road environments span coastal Mumbai and Chennai humidity, Delhi extreme heat, Bengaluru elevation, Kolkata humidity.",
        "angle": "Northern plains heat is the defining home condition. Loo winds from the west bring hot dry afternoons. Dharamshala matches play in Himalayan foothills with distinctly cooler conditions."},
    "Rajasthan Royals": {"slug": "rajasthan-royals", "abbrev": "RR",
        "ground": "Sawai Mansingh Stadium", "city": "Jaipur", "capacity": 30000,
        "headline": "Rajasthan Royals Weather Playbook: Sawai Mansingh Stadium and Rajasthan Desert Heat",
        "home": "Rajasthan Royals play at Sawai Mansingh Stadium in Jaipur, Rajasthan, with secondary matches at Barsapara Cricket Stadium in Guwahati. Open-air Rajasthan setting with extreme desert heat during IPL season and dust storm risk.",
        "road": "IPL road environments span coastal Mumbai and Chennai humidity, Delhi extreme heat, Bengaluru elevation, Kolkata humidity.",
        "angle": "Rajasthan desert heat is extreme. Dust storms (andhi) from the Thar Desert are a real weather variable. Pre-monsoon thunderstorms bring occasional delays from mid-April onward."},
    "Gujarat Titans": {"slug": "gujarat-titans", "abbrev": "GT",
        "ground": "Narendra Modi Stadium", "city": "Ahmedabad", "capacity": 132000,
        "headline": "Gujarat Titans Weather Playbook: Narendra Modi Stadium (World's Largest Cricket Ground)",
        "home": "Gujarat Titans play at Narendra Modi Stadium in Ahmedabad, the largest cricket ground in the world by capacity. Open-air Gujarat setting with extreme dry heat during IPL season.",
        "road": "IPL road environments span coastal Mumbai and Chennai humidity, Delhi extreme heat, Bengaluru elevation, Kolkata humidity.",
        "angle": "Ahmedabad dry heat is extreme through IPL season. Dust and haze conditions are common. Evening matches offer temperature relief but dew factor remains a variable."},
    "Lucknow Super Giants": {"slug": "lucknow-super-giants", "abbrev": "LSG",
        "ground": "Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium", "city": "Lucknow", "capacity": 50000,
        "headline": "Lucknow Super Giants Weather Playbook: Ekana Cricket Stadium and UP Heat",
        "home": "Lucknow Super Giants play at Ekana Cricket Stadium in Lucknow. Open-air Uttar Pradesh setting with extreme summer heat during IPL season. Northern plains climate brings hot dry conditions and elevated pre-monsoon storm risk by May.",
        "road": "IPL road environments span coastal Mumbai and Chennai humidity, Delhi extreme heat, Bengaluru elevation, Kolkata humidity.",
        "angle": "Northern UP heat is extreme through April and May. Loo winds bring hot dry afternoons. Pre-monsoon dust storms and thunderstorms are the primary weather variables from mid-April onward."},
}

# Ground content derived from team dict (1:1 mapping)
GROUND_CONTENT_IPL = {}
for team_name, tc in TEAM_CONTENT_IPL.items():
    GROUND_CONTENT_IPL[tc["ground"]] = {
        "slug": tc["slug"] + "-ground",
        "team": team_name,
        "city": tc["city"],
        "capacity": tc["capacity"],
        "headline": f"{tc['ground']} Weather Guide: {tc['city']} IPL Cricket",
        "overview": tc["home"],
        "angle": tc["angle"],
    }

TEAM_BY_SLUG_IPL = {c["slug"]: (name, c) for name, c in TEAM_CONTENT_IPL.items()}
GROUND_BY_SLUG_IPL = {c["slug"]: (name, c) for name, c in GROUND_CONTENT_IPL.items()}
