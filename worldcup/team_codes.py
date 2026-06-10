"""
worldcup.team_codes — FIFA 3-letter codes for World Cup nations.

ESPN's `shortDisplayName` is usually just the full team name again (not
helpful), and `abbreviation` is inconsistent — sometimes 2 letters,
sometimes 3, sometimes empty. So we override with the official FIFA
codes here. Used by the cheat-card display where horizontal space is
tight.

Lookup is case-insensitive against the ESPN displayName.
"""

from __future__ import annotations


# Official FIFA 3-letter codes. Covers every confirmed and likely 2026
# qualifier across all six confederations. Missing entries fall through
# to ESPN's abbreviation / short_name in the schedule parser.
FIFA_CODES = {
    # CONCACAF hosts + qualifiers
    "United States":             "USA",
    "USA":                       "USA",
    "Canada":                    "CAN",
    "Mexico":                    "MEX",
    "Costa Rica":                "CRC",
    "Jamaica":                   "JAM",
    "Panama":                    "PAN",
    "Honduras":                  "HON",
    "Guatemala":                 "GUA",
    "El Salvador":               "SLV",
    "Curaçao":                   "CUW",
    "Curacao":                   "CUW",
    "Trinidad and Tobago":       "TRI",
    "Haiti":                     "HAI",

    # CONMEBOL
    "Argentina":                 "ARG",
    "Brazil":                    "BRA",
    "Uruguay":                   "URU",
    "Colombia":                  "COL",
    "Ecuador":                   "ECU",
    "Paraguay":                  "PAR",
    "Peru":                      "PER",
    "Chile":                     "CHI",
    "Bolivia":                   "BOL",
    "Venezuela":                 "VEN",

    # UEFA
    "England":                   "ENG",
    "France":                    "FRA",
    "Germany":                   "GER",
    "Spain":                     "ESP",
    "Italy":                     "ITA",
    "Portugal":                  "POR",
    "Netherlands":               "NED",
    "Belgium":                   "BEL",
    "Croatia":                   "CRO",
    "Denmark":                   "DEN",
    "Switzerland":               "SUI",
    "Austria":                   "AUT",
    "Sweden":                    "SWE",
    "Norway":                    "NOR",
    "Czechia":                   "CZE",
    "Czech Republic":            "CZE",
    "Poland":                    "POL",
    "Hungary":                   "HUN",
    "Greece":                    "GRE",
    "Slovakia":                  "SVK",
    "Slovenia":                  "SVN",
    "Albania":                   "ALB",
    "Romania":                   "ROU",
    "Serbia":                    "SRB",
    "Ukraine":                   "UKR",
    "Türkiye":                   "TUR",
    "Turkey":                    "TUR",
    "Republic of Ireland":       "IRL",
    "Ireland":                   "IRL",
    "Scotland":                  "SCO",
    "Wales":                     "WAL",
    "Northern Ireland":          "NIR",
    "Finland":                   "FIN",
    "Iceland":                   "ISL",
    "Bosnia and Herzegovina":    "BIH",
    "Bosnia & Herzegovina":      "BIH",
    "Bosnia-Herzegovina":        "BIH",
    "Bosnia-Herz.":              "BIH",
    "Bosnia-Herz":               "BIH",
    "North Macedonia":           "MKD",
    "Kosovo":                    "KVX",
    "Montenegro":                "MNE",
    "Bulgaria":                  "BUL",
    "Georgia":                   "GEO",
    "Russia":                    "RUS",
    "Belarus":                   "BLR",
    "Estonia":                   "EST",
    "Latvia":                    "LVA",
    "Lithuania":                 "LTU",
    "Moldova":                   "MDA",
    "Armenia":                   "ARM",
    "Azerbaijan":                "AZE",
    "Cyprus":                    "CYP",
    "Israel":                    "ISR",
    "Luxembourg":                "LUX",
    "Andorra":                   "AND",
    "Malta":                     "MLT",
    "Liechtenstein":             "LIE",
    "San Marino":                "SMR",
    "Gibraltar":                 "GIB",
    "Faroe Islands":             "FRO",

    # CAF
    "Morocco":                   "MAR",
    "Senegal":                   "SEN",
    "Egypt":                     "EGY",
    "Nigeria":                   "NGA",
    "Ghana":                     "GHA",
    "Tunisia":                   "TUN",
    "Cameroon":                  "CMR",
    "Algeria":                   "ALG",
    "South Africa":              "RSA",
    "Mali":                      "MLI",
    "Côte d'Ivoire":             "CIV",
    "Cote d'Ivoire":             "CIV",
    "Ivory Coast":               "CIV",
    "Cape Verde":                "CPV",
    "Madagascar":                "MAD",
    "Gabon":                     "GAB",
    "Burkina Faso":              "BFA",
    "Guinea":                    "GUI",
    "DR Congo":                  "COD",
    "Democratic Republic of the Congo": "COD",
    "Congo":                     "CGO",
    "Angola":                    "ANG",
    "Zambia":                    "ZAM",
    "Sudan":                     "SDN",
    "Mozambique":                "MOZ",
    "Equatorial Guinea":         "EQG",
    "Mauritania":                "MTN",
    "Comoros":                   "COM",
    "Sierra Leone":              "SLE",
    "Benin":                     "BEN",
    "Togo":                      "TOG",
    "Uganda":                    "UGA",
    "Tanzania":                  "TAN",
    "Kenya":                     "KEN",
    "Zimbabwe":                  "ZIM",
    "Namibia":                   "NAM",
    "Libya":                     "LBY",
    "Niger":                     "NIG",
    "Botswana":                  "BOT",
    "Lesotho":                   "LES",
    "Eswatini":                  "SWZ",
    "Ethiopia":                  "ETH",
    "Malawi":                    "MWI",
    "Rwanda":                    "RWA",
    "Burundi":                   "BDI",
    "Liberia":                   "LBR",
    "Guinea-Bissau":             "GNB",

    # AFC
    "Japan":                     "JPN",
    "South Korea":               "KOR",
    "Korea Republic":            "KOR",
    "Republic of Korea":         "KOR",
    "Iran":                      "IRN",
    "IR Iran":                   "IRN",
    "Saudi Arabia":              "KSA",
    "Australia":                 "AUS",
    "Iraq":                      "IRQ",
    "Qatar":                     "QAT",
    "United Arab Emirates":      "UAE",
    "UAE":                       "UAE",
    "Jordan":                    "JOR",
    "Uzbekistan":                "UZB",
    "China":                     "CHN",
    "China PR":                  "CHN",
    "Vietnam":                   "VIE",
    "Thailand":                  "THA",
    "Indonesia":                 "IDN",
    "Malaysia":                  "MAS",
    "Lebanon":                   "LBN",
    "Syria":                     "SYR",
    "Palestine":                 "PLE",
    "Oman":                      "OMA",
    "Kuwait":                    "KUW",
    "Bahrain":                   "BHR",
    "Yemen":                     "YEM",
    "Tajikistan":                "TJK",
    "Turkmenistan":              "TKM",
    "Kyrgyzstan":                "KGZ",
    "Kazakhstan":                "KAZ",
    "India":                     "IND",
    "Bangladesh":                "BAN",
    "Pakistan":                  "PAK",
    "Sri Lanka":                 "SRI",
    "Nepal":                     "NEP",
    "Myanmar":                   "MYA",
    "Philippines":               "PHI",
    "Singapore":                 "SGP",
    "Hong Kong":                 "HKG",
    "Taiwan":                    "TPE",
    "Chinese Taipei":            "TPE",

    # OFC
    "New Zealand":               "NZL",
    "Fiji":                      "FIJ",
    "Solomon Islands":           "SOL",
    "Tahiti":                    "TAH",
    "Vanuatu":                   "VAN",
    "Papua New Guinea":          "PNG",
}


# Normalized lookup: lowercase keys → FIFA code. Built once at module load
# so each lookup is a single dict access.
_NORMALIZED = {k.lower().strip(): v for k, v in FIFA_CODES.items()}


def fifa_code_for(team_name: str) -> str:
    """
    Return the FIFA 3-letter code for a team name, or empty string if
    not in the lookup. Case-insensitive.
    """
    if not team_name:
        return ""
    return _NORMALIZED.get(team_name.lower().strip(), "")
