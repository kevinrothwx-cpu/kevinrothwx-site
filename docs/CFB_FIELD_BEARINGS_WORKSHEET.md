# CFB field bearings — fill-in worksheet

**What to measure:** the compass bearing the field runs toward, endzone to endzone. Either endzone works (the axis is symmetric — 0 and 180 describe the same north-south field).

**How:** click the satellite link, look at the field, read the bearing off the north-up view. A field running exactly north-south is 0 (or 180). Exactly east-west is 90 (or 270).

**Where it goes:** `cfb/venues.py`, add `bearing=NNN` to that stadium's `_stadium(...)` call. Example:

```python
stadium=_stadium("Bryant-Denny Stadium", "Tuscaloosa, AL",
                 33.2083, -87.5503, "America/Chicago",
                 cap=100077, bearing=0)
```

Domes still matter for the graphic even though wind is irrelevant — but they're lowest priority. Marked below.


---


**Progress: 0 / 134 measured**


## SEC

| Team | Stadium | City | Satellite | Bearing |
|---|---|---|---|---|
| Alabama | Bryant-Denny Stadium | Tuscaloosa, AL | [view](https://www.google.com/maps/@33.2083,-87.5503,400m/data=!3m1!1e3) | `` |
| Arkansas | Donald W. Reynolds Razorback Stadium | Fayetteville, AR | [view](https://www.google.com/maps/@36.0682,-94.1789,400m/data=!3m1!1e3) | `` |
| Auburn | Jordan-Hare Stadium | Auburn, AL | [view](https://www.google.com/maps/@32.602,-85.4912,400m/data=!3m1!1e3) | `` |
| Florida | Ben Hill Griffin Stadium | Gainesville, FL | [view](https://www.google.com/maps/@29.6498,-82.3486,400m/data=!3m1!1e3) | `` |
| Georgia | Sanford Stadium | Athens, GA | [view](https://www.google.com/maps/@33.9495,-83.3733,400m/data=!3m1!1e3) | `` |
| Kentucky | Kroger Field | Lexington, KY | [view](https://www.google.com/maps/@38.022,-84.505,400m/data=!3m1!1e3) | `` |
| LSU | Tiger Stadium | Baton Rouge, LA | [view](https://www.google.com/maps/@30.4118,-91.1838,400m/data=!3m1!1e3) | `` |
| Mississippi State | Davis Wade Stadium | Starkville, MS | [view](https://www.google.com/maps/@33.4566,-88.7935,400m/data=!3m1!1e3) | `` |
| Missouri | Faurot Field | Columbia, MO | [view](https://www.google.com/maps/@38.9404,-92.3338,400m/data=!3m1!1e3) | `` |
| Oklahoma | Gaylord Family Oklahoma Memorial Stadium | Norman, OK | [view](https://www.google.com/maps/@35.2058,-97.4421,400m/data=!3m1!1e3) | `` |
| Ole Miss | Vaught-Hemingway Stadium | Oxford, MS | [view](https://www.google.com/maps/@34.3618,-89.5366,400m/data=!3m1!1e3) | `` |
| South Carolina | Williams-Brice Stadium | Columbia, SC | [view](https://www.google.com/maps/@33.9728,-81.0193,400m/data=!3m1!1e3) | `` |
| Tennessee | Neyland Stadium | Knoxville, TN | [view](https://www.google.com/maps/@35.955,-83.925,400m/data=!3m1!1e3) | `` |
| Texas | Darrell K Royal-Texas Memorial Stadium | Austin, TX | [view](https://www.google.com/maps/@30.2836,-97.7325,400m/data=!3m1!1e3) | `` |
| Texas A&M | Kyle Field | College Station, TX | [view](https://www.google.com/maps/@30.61,-96.34,400m/data=!3m1!1e3) | `` |
| Vanderbilt | FirstBank Stadium | Nashville, TN | [view](https://www.google.com/maps/@36.1432,-86.8074,400m/data=!3m1!1e3) | `` |

## B1G

| Team | Stadium | City | Satellite | Bearing |
|---|---|---|---|---|
| Illinois | Memorial Stadium | Champaign, IL | [view](https://www.google.com/maps/@40.0993,-88.2356,400m/data=!3m1!1e3) | `` |
| Indiana | Memorial Stadium | Bloomington, IN | [view](https://www.google.com/maps/@39.181,-86.5258,400m/data=!3m1!1e3) | `` |
| Iowa | Kinnick Stadium | Iowa City, IA | [view](https://www.google.com/maps/@41.6586,-91.5512,400m/data=!3m1!1e3) | `` |
| Maryland | SECU Stadium | College Park, MD | [view](https://www.google.com/maps/@38.9907,-76.9474,400m/data=!3m1!1e3) | `` |
| Michigan | Michigan Stadium | Ann Arbor, MI | [view](https://www.google.com/maps/@42.2658,-83.7487,400m/data=!3m1!1e3) | `` |
| Michigan State | Spartan Stadium | East Lansing, MI | [view](https://www.google.com/maps/@42.7282,-84.4847,400m/data=!3m1!1e3) | `` |
| Minnesota | Huntington Bank Stadium | Minneapolis, MN | [view](https://www.google.com/maps/@44.9764,-93.2243,400m/data=!3m1!1e3) | `` |
| Nebraska | Memorial Stadium | Lincoln, NE | [view](https://www.google.com/maps/@40.8208,-96.7058,400m/data=!3m1!1e3) | `` |
| Northwestern | Ryan Field | Evanston, IL | [view](https://www.google.com/maps/@42.0648,-87.6926,400m/data=!3m1!1e3) | `` |
| Ohio State | Ohio Stadium | Columbus, OH | [view](https://www.google.com/maps/@40.0017,-83.0197,400m/data=!3m1!1e3) | `` |
| Oregon | Autzen Stadium | Eugene, OR | [view](https://www.google.com/maps/@44.0583,-123.0682,400m/data=!3m1!1e3) | `` |
| Penn State | Beaver Stadium | State College, PA | [view](https://www.google.com/maps/@40.8122,-77.8562,400m/data=!3m1!1e3) | `` |
| Purdue | Ross-Ade Stadium | West Lafayette, IN | [view](https://www.google.com/maps/@40.4347,-86.9182,400m/data=!3m1!1e3) | `` |
| Rutgers | SHI Stadium | Piscataway, NJ | [view](https://www.google.com/maps/@40.5135,-74.4655,400m/data=!3m1!1e3) | `` |
| UCLA | Rose Bowl | Pasadena, CA | [view](https://www.google.com/maps/@34.1613,-118.1676,400m/data=!3m1!1e3) | `` |
| USC | Los Angeles Memorial Coliseum | Los Angeles, CA | [view](https://www.google.com/maps/@34.0141,-118.2879,400m/data=!3m1!1e3) | `` |
| Washington | Husky Stadium | Seattle, WA | [view](https://www.google.com/maps/@47.6502,-122.3019,400m/data=!3m1!1e3) | `` |
| Wisconsin | Camp Randall Stadium | Madison, WI | [view](https://www.google.com/maps/@43.0696,-89.4124,400m/data=!3m1!1e3) | `` |

## ACC

| Team | Stadium | City | Satellite | Bearing |
|---|---|---|---|---|
| Boston College | Alumni Stadium | Chestnut Hill, MA | [view](https://www.google.com/maps/@42.3354,-71.1665,400m/data=!3m1!1e3) | `` |
| Cal | California Memorial Stadium | Berkeley, CA | [view](https://www.google.com/maps/@37.8716,-122.2509,400m/data=!3m1!1e3) | `` |
| Clemson | Memorial Stadium | Clemson, SC | [view](https://www.google.com/maps/@34.6787,-82.843,400m/data=!3m1!1e3) | `` |
| Duke | Wallace Wade Stadium | Durham, NC | [view](https://www.google.com/maps/@36.0007,-78.9412,400m/data=!3m1!1e3) | `` |
| Florida State | Doak Campbell Stadium | Tallahassee, FL | [view](https://www.google.com/maps/@30.438,-84.3047,400m/data=!3m1!1e3) | `` |
| Georgia Tech | Bobby Dodd Stadium | Atlanta, GA | [view](https://www.google.com/maps/@33.7724,-84.3925,400m/data=!3m1!1e3) | `` |
| Louisville | L&N Federal Credit Union Stadium | Louisville, KY | [view](https://www.google.com/maps/@38.2065,-85.7572,400m/data=!3m1!1e3) | `` |
| Miami | Hard Rock Stadium | Miami Gardens, FL | [view](https://www.google.com/maps/@25.958,-80.2389,400m/data=!3m1!1e3) | `` |
| NC State | Carter-Finley Stadium | Raleigh, NC | [view](https://www.google.com/maps/@35.8011,-78.7194,400m/data=!3m1!1e3) | `` |
| North Carolina | Kenan Memorial Stadium | Chapel Hill, NC | [view](https://www.google.com/maps/@35.9069,-79.0476,400m/data=!3m1!1e3) | `` |
| Pittsburgh | Acrisure Stadium | Pittsburgh, PA | [view](https://www.google.com/maps/@40.4467,-80.0157,400m/data=!3m1!1e3) | `` |
| SMU | Gerald J. Ford Stadium | Dallas, TX | [view](https://www.google.com/maps/@32.8403,-96.7822,400m/data=!3m1!1e3) | `` |
| Stanford | Stanford Stadium | Stanford, CA | [view](https://www.google.com/maps/@37.4347,-122.161,400m/data=!3m1!1e3) | `` |
| Syracuse ⌂ | JMA Wireless Dome | Syracuse, NY | [view](https://www.google.com/maps/@43.0364,-76.1361,400m/data=!3m1!1e3) | `` |
| Virginia | Scott Stadium | Charlottesville, VA | [view](https://www.google.com/maps/@38.0316,-78.5128,400m/data=!3m1!1e3) | `` |
| Virginia Tech | Lane Stadium | Blacksburg, VA | [view](https://www.google.com/maps/@37.2197,-80.418,400m/data=!3m1!1e3) | `` |
| Wake Forest | Allegacy Federal Credit Union Stadium | Winston-Salem, NC | [view](https://www.google.com/maps/@36.1322,-80.254,400m/data=!3m1!1e3) | `` |

## B12

| Team | Stadium | City | Satellite | Bearing |
|---|---|---|---|---|
| Arizona | Arizona Stadium | Tucson, AZ | [view](https://www.google.com/maps/@32.2298,-110.9491,400m/data=!3m1!1e3) | `` |
| Arizona State | Mountain America Stadium | Tempe, AZ | [view](https://www.google.com/maps/@33.4264,-111.9325,400m/data=!3m1!1e3) | `` |
| BYU | LaVell Edwards Stadium | Provo, UT | [view](https://www.google.com/maps/@40.2575,-111.6542,400m/data=!3m1!1e3) | `` |
| Baylor | McLane Stadium | Waco, TX | [view](https://www.google.com/maps/@31.5582,-97.1156,400m/data=!3m1!1e3) | `` |
| Cincinnati | Nippert Stadium | Cincinnati, OH | [view](https://www.google.com/maps/@39.1316,-84.5168,400m/data=!3m1!1e3) | `` |
| Colorado | Folsom Field | Boulder, CO | [view](https://www.google.com/maps/@40.0075,-105.267,400m/data=!3m1!1e3) | `` |
| Houston | TDECU Stadium | Houston, TX | [view](https://www.google.com/maps/@29.7222,-95.3491,400m/data=!3m1!1e3) | `` |
| Iowa State | Jack Trice Stadium | Ames, IA | [view](https://www.google.com/maps/@42.0145,-93.6357,400m/data=!3m1!1e3) | `` |
| Kansas | David Booth Kansas Memorial Stadium | Lawrence, KS | [view](https://www.google.com/maps/@38.9633,-95.2456,400m/data=!3m1!1e3) | `` |
| Kansas State | Bill Snyder Family Stadium | Manhattan, KS | [view](https://www.google.com/maps/@39.2018,-96.5942,400m/data=!3m1!1e3) | `` |
| Oklahoma State | Boone Pickens Stadium | Stillwater, OK | [view](https://www.google.com/maps/@36.1255,-97.0664,400m/data=!3m1!1e3) | `` |
| TCU | Amon G. Carter Stadium | Fort Worth, TX | [view](https://www.google.com/maps/@32.71,-97.3686,400m/data=!3m1!1e3) | `` |
| Texas Tech | Jones AT&T Stadium | Lubbock, TX | [view](https://www.google.com/maps/@33.5912,-101.8729,400m/data=!3m1!1e3) | `` |
| UCF | FBC Mortgage Stadium | Orlando, FL | [view](https://www.google.com/maps/@28.6079,-81.1929,400m/data=!3m1!1e3) | `` |
| Utah | Rice-Eccles Stadium | Salt Lake City, UT | [view](https://www.google.com/maps/@40.7608,-111.8484,400m/data=!3m1!1e3) | `` |
| West Virginia | Milan Puskar Stadium | Morgantown, WV | [view](https://www.google.com/maps/@39.6483,-79.954,400m/data=!3m1!1e3) | `` |

## IND

| Team | Stadium | City | Satellite | Bearing |
|---|---|---|---|---|
| Notre Dame | Notre Dame Stadium | Notre Dame, IN | [view](https://www.google.com/maps/@41.6985,-86.2336,400m/data=!3m1!1e3) | `` |
| UConn | Pratt & Whitney Stadium at Rentschler Field | East Hartford, CT | [view](https://www.google.com/maps/@41.7591,-72.6092,400m/data=!3m1!1e3) | `` |

## AAC

| Team | Stadium | City | Satellite | Bearing |
|---|---|---|---|---|
| Army | Michie Stadium | West Point, NY | [view](https://www.google.com/maps/@41.376,-73.9582,400m/data=!3m1!1e3) | `` |
| Charlotte | Jerry Richardson Stadium | Charlotte, NC | [view](https://www.google.com/maps/@35.31056,-80.74028,400m/data=!3m1!1e3) | `` |
| ECU | Dowdy-Ficklen Stadium | Greenville, NC | [view](https://www.google.com/maps/@35.59117,-77.35917,400m/data=!3m1!1e3) | `` |
| FAU | Flagler Credit Union Stadium | Boca Raton, FL | [view](https://www.google.com/maps/@26.37528,-80.10028,400m/data=!3m1!1e3) | `` |
| Memphis | Simmons Bank Liberty Stadium | Memphis, TN | [view](https://www.google.com/maps/@35.12111,-89.9775,400m/data=!3m1!1e3) | `` |
| Navy | Navy-Marine Corps Memorial Stadium | Annapolis, MD | [view](https://www.google.com/maps/@38.985,-76.50694,400m/data=!3m1!1e3) | `` |
| North Texas | DATCU Stadium | Denton, TX | [view](https://www.google.com/maps/@33.20361,-97.15944,400m/data=!3m1!1e3) | `` |
| Rice | Rice Stadium | Houston, TX | [view](https://www.google.com/maps/@29.71639,-95.40917,400m/data=!3m1!1e3) | `` |
| Temple | Lincoln Financial Field | Philadelphia, PA | [view](https://www.google.com/maps/@39.90083,-75.16778,400m/data=!3m1!1e3) | `` |
| Tulane | Yulman Stadium | New Orleans, LA | [view](https://www.google.com/maps/@29.94482,-90.11682,400m/data=!3m1!1e3) | `` |
| Tulsa | Skelly Field at H.A. Chapman Stadium | Tulsa, OK | [view](https://www.google.com/maps/@36.14861,-95.94389,400m/data=!3m1!1e3) | `` |
| UAB | Protective Stadium | Birmingham, AL | [view](https://www.google.com/maps/@33.52778,-86.80917,400m/data=!3m1!1e3) | `` |
| USF | Raymond James Stadium | Tampa, FL | [view](https://www.google.com/maps/@27.97583,-82.50333,400m/data=!3m1!1e3) | `` |
| UTSA ⌂ | Alamodome | San Antonio, TX | [view](https://www.google.com/maps/@29.41694,-98.47889,400m/data=!3m1!1e3) | `` |

## MWC

| Team | Stadium | City | Satellite | Bearing |
|---|---|---|---|---|
| Air Force | Falcon Stadium | Colorado Springs, CO | [view](https://www.google.com/maps/@38.99667,-104.84359,400m/data=!3m1!1e3) | `` |
| Boise State | Albertsons Stadium | Boise, ID | [view](https://www.google.com/maps/@43.60306,-116.19611,400m/data=!3m1!1e3) | `` |
| Colorado State | Canvas Stadium | Fort Collins, CO | [view](https://www.google.com/maps/@40.57,-105.0885,400m/data=!3m1!1e3) | `` |
| Fresno State | Valley Children's Stadium | Fresno, CA | [view](https://www.google.com/maps/@36.8144,-119.758,400m/data=!3m1!1e3) | `` |
| Hawai'i | Clarence T.C. Ching Athletics Complex | Honolulu, HI | [view](https://www.google.com/maps/@21.294,-157.818,400m/data=!3m1!1e3) | `` |
| Nevada | Mackay Stadium | Reno, NV | [view](https://www.google.com/maps/@39.54681,-119.8175,400m/data=!3m1!1e3) | `` |
| New Mexico | University Stadium | Albuquerque, NM | [view](https://www.google.com/maps/@35.06689,-106.62831,400m/data=!3m1!1e3) | `` |
| San Diego State | Snapdragon Stadium | San Diego, CA | [view](https://www.google.com/maps/@32.78444,-117.12283,400m/data=!3m1!1e3) | `` |
| San Jose State | CEFCU Stadium | San Jose, CA | [view](https://www.google.com/maps/@37.31972,-121.86833,400m/data=!3m1!1e3) | `` |
| UNLV ⌂ | Allegiant Stadium | Paradise, NV | [view](https://www.google.com/maps/@36.09079,-115.18395,400m/data=!3m1!1e3) | `` |
| Utah State | Maverik Stadium | Logan, UT | [view](https://www.google.com/maps/@41.75169,-111.81169,400m/data=!3m1!1e3) | `` |
| Wyoming | War Memorial Stadium | Laramie, WY | [view](https://www.google.com/maps/@41.307,-105.5677,400m/data=!3m1!1e3) | `` |

## SBC

| Team | Stadium | City | Satellite | Bearing |
|---|---|---|---|---|
| App State | Kidd Brewer Stadium | Boone, NC | [view](https://www.google.com/maps/@36.21167,-81.68556,400m/data=!3m1!1e3) | `` |
| Arkansas State | Centennial Bank Stadium | Jonesboro, AR | [view](https://www.google.com/maps/@35.84889,-90.66722,400m/data=!3m1!1e3) | `` |
| Coastal Carolina | Brooks Stadium | Conway, SC | [view](https://www.google.com/maps/@33.7929,-79.0175,400m/data=!3m1!1e3) | `` |
| Georgia Southern | Allen E. Paulson Stadium | Statesboro, GA | [view](https://www.google.com/maps/@32.41216,-81.78314,400m/data=!3m1!1e3) | `` |
| Georgia State | Center Parc Stadium | Atlanta, GA | [view](https://www.google.com/maps/@33.73528,-84.38944,400m/data=!3m1!1e3) | `` |
| James Madison | Bridgeforth Stadium | Harrisonburg, VA | [view](https://www.google.com/maps/@38.43528,-78.87306,400m/data=!3m1!1e3) | `` |
| Louisiana | Cajun Field | Lafayette, LA | [view](https://www.google.com/maps/@30.21583,-92.04194,400m/data=!3m1!1e3) | `` |
| Marshall | Joan C. Edwards Stadium | Huntington, WV | [view](https://www.google.com/maps/@38.425,-82.42083,400m/data=!3m1!1e3) | `` |
| Old Dominion | S.B. Ballard Stadium | Norfolk, VA | [view](https://www.google.com/maps/@36.8889,-76.30488,400m/data=!3m1!1e3) | `` |
| South Alabama | Hancock Whitney Stadium | Mobile, AL | [view](https://www.google.com/maps/@30.6969,-88.19201,400m/data=!3m1!1e3) | `` |
| Southern Miss | M.M. Roberts Stadium | Hattiesburg, MS | [view](https://www.google.com/maps/@31.32889,-89.33139,400m/data=!3m1!1e3) | `` |
| Texas State | UFCU Stadium | San Marcos, TX | [view](https://www.google.com/maps/@29.89111,-97.92556,400m/data=!3m1!1e3) | `` |
| Troy | Veterans Memorial Stadium | Troy, AL | [view](https://www.google.com/maps/@31.79944,-85.95194,400m/data=!3m1!1e3) | `` |
| ULM | JPS Field at Malone Stadium | Monroe, LA | [view](https://www.google.com/maps/@32.53083,-92.06583,400m/data=!3m1!1e3) | `` |

## CUSA

| Team | Stadium | City | Satellite | Bearing |
|---|---|---|---|---|
| Delaware | Delaware Stadium | Newark, DE | [view](https://www.google.com/maps/@39.6617,-75.7488,400m/data=!3m1!1e3) | `` |
| FIU | Pitbull Stadium | Miami, FL | [view](https://www.google.com/maps/@25.7525,-80.37778,400m/data=!3m1!1e3) | `` |
| Jax State | Burgess-Snow Field at AmFirst Stadium | Jacksonville, AL | [view](https://www.google.com/maps/@33.82028,-85.76639,400m/data=!3m1!1e3) | `` |
| Kennesaw State | Fifth Third Stadium | Kennesaw, GA | [view](https://www.google.com/maps/@34.029,-84.5676,400m/data=!3m1!1e3) | `` |
| Liberty | Williams Stadium | Lynchburg, VA | [view](https://www.google.com/maps/@37.354,-79.175,400m/data=!3m1!1e3) | `` |
| Louisiana Tech | Joe Aillet Stadium | Ruston, LA | [view](https://www.google.com/maps/@32.53202,-92.6559,400m/data=!3m1!1e3) | `` |
| Middle Tennessee | Johnny "Red" Floyd Stadium | Murfreesboro, TN | [view](https://www.google.com/maps/@35.85051,-86.36822,400m/data=!3m1!1e3) | `` |
| Missouri State | Robert W. Plaster Stadium | Springfield, MO | [view](https://www.google.com/maps/@37.19778,-93.27972,400m/data=!3m1!1e3) | `` |
| New Mexico State | Aggie Memorial Stadium | Las Cruces, NM | [view](https://www.google.com/maps/@32.27972,-106.74111,400m/data=!3m1!1e3) | `` |
| Sam Houston | Elliott T. Bowers Stadium | Huntsville, TX | [view](https://www.google.com/maps/@30.71389,-95.54167,400m/data=!3m1!1e3) | `` |
| UTEP | Sun Bowl | El Paso, TX | [view](https://www.google.com/maps/@31.77306,-106.50806,400m/data=!3m1!1e3) | `` |
| Western Kentucky | Houchens Industries-L.T. Smith Stadium | Bowling Green, KY | [view](https://www.google.com/maps/@36.98472,-86.45944,400m/data=!3m1!1e3) | `` |

## MAC

| Team | Stadium | City | Satellite | Bearing |
|---|---|---|---|---|
| Akron | InfoCision Stadium-Summa Field | Akron, OH | [view](https://www.google.com/maps/@41.07234,-81.50802,400m/data=!3m1!1e3) | `` |
| Ball State | Scheumann Stadium | Muncie, IN | [view](https://www.google.com/maps/@40.216,-85.4168,400m/data=!3m1!1e3) | `` |
| Bowling Green | Doyt L. Perry Stadium | Bowling Green, OH | [view](https://www.google.com/maps/@41.37811,-83.6225,400m/data=!3m1!1e3) | `` |
| Buffalo | UB Stadium | Amherst, NY | [view](https://www.google.com/maps/@42.9992,-78.7775,400m/data=!3m1!1e3) | `` |
| Central Michigan | Kelly/Shorts Stadium | Mount Pleasant, MI | [view](https://www.google.com/maps/@43.5775,-84.77081,400m/data=!3m1!1e3) | `` |
| Eastern Michigan | Rynearson Stadium | Ypsilanti, MI | [view](https://www.google.com/maps/@42.25583,-83.64722,400m/data=!3m1!1e3) | `` |
| Kent State | Dix Stadium | Kent, OH | [view](https://www.google.com/maps/@41.1392,-81.31331,400m/data=!3m1!1e3) | `` |
| Miami (OH) | Yager Stadium | Oxford, OH | [view](https://www.google.com/maps/@39.51833,-84.72633,400m/data=!3m1!1e3) | `` |
| Northern Illinois | Huskie Stadium | DeKalb, IL | [view](https://www.google.com/maps/@41.93406,-88.77798,400m/data=!3m1!1e3) | `` |
| Ohio | Frank Solich Field at Peden Stadium | Athens, OH | [view](https://www.google.com/maps/@39.32111,-82.10281,400m/data=!3m1!1e3) | `` |
| Toledo | Glass Bowl | Toledo, OH | [view](https://www.google.com/maps/@41.65739,-83.61402,400m/data=!3m1!1e3) | `` |
| UMass | McGuirk Alumni Stadium | Amherst, MA | [view](https://www.google.com/maps/@42.394,-72.529,400m/data=!3m1!1e3) | `` |
| Western Michigan | Waldo Stadium | Kalamazoo, MI | [view](https://www.google.com/maps/@42.286,-85.60075,400m/data=!3m1!1e3) | `` |
