"""Player position overrides sourced from ESPN's current team roster pages
(fetched 2026-08-12), used to correct/simplify BigDataBall's raw POSITION
column -- which tends to tag versatile bigs with combo labels like "C-F"
even when the player is broadly known/listed as a single position.

This is a static snapshot, not a live lookup: positions here reflect ESPN's
rosters as of the date above and are applied once during preprocessing, not
re-fetched on every run. Re-fetch and refresh this file periodically (e.g.
each offseason) if it goes stale.

Players not covered here (traded away from a full 15-man active roster,
free agents, retired, two-way/G-League) fall back to BigDataBall's own
position value in preprocess.py -- see apply_position_overrides().
"""

ESPN_POSITIONS = {
    # Oklahoma City
    "Brooks Barnhizer": "F", "Alex Caruso": "G", "Josh Dix": "G", "Shai Gilgeous-Alexander": "G",
    "Isaiah Hartenstein": "C", "Chet Holmgren": "C", "Aday Mara": "C", "Jared McCain": "G",
    "Ajay Mitchell": "G", "Otega Oweh": "G", "Thomas Sorber": "C", "Bennett Stirtz": "G",
    "Nikola Topic": "G", "Cason Wallace": "G", "Jalen Williams": "G", "Jaylin Williams": "F",
    "Kenrich Williams": "G",
    # Atlanta
    "Nickeil Alexander-Walker": "G", "Devin Carter": "G", "Dyson Daniels": "G", "RayJ Dennis": "G",
    "Luguentz Dort": "G", "Zuby Ejiofor": "F", "Kingston Flemings": "G", "Keshon Gilbert": "G",
    "Mouhamed Gueye": "F", "Buddy Hield": "G", "Jalen Johnson": "F", "Corey Kispert": "F",
    "Christian Koloko": "C", "Jock Landale": "C", "CJ McCollum": "G", "Ryan Nembhard": "G",
    "Asa Newell": "F", "Onyeka Okongwu": "F", "Henri Veesaar": "C", "Keaton Wallace": "G",
    "Aaron Wiggins": "G", "Jalen Wilson": "F",
    # Boston
    "Chris Cenac Jr.": "F", "Mike Conley": "G", "Luka Garza": "C", "Paul George": "F",
    "Hugo Gonzalez": "G", "Ron Harper Jr.": "G", "Sam Hauser": "F", "Dillon Mitchell": "F",
    "Payton Pritchard": "G", "Neemias Queta": "C", "Mitchell Robinson": "C", "Baylor Scheierman": "G",
    "Jayson Tatum": "F", "Jordan Walsh": "G", "Derrick White": "G", "Amari Williams": "F",
    # Brooklyn
    "Tyler Bilodeau": "F", "Mikel Brown Jr.": "G", "Noah Clowney": "F", "Egor Demin": "G",
    "Keon Ellis": "G", "Tyson Etienne": "G", "Joshua Jefferson": "F", "Chaney Johnson": "F",
    "E.J. Liddell": "F", "Terance Mann": "G", "Josh Minott": "F", "Michael Porter Jr.": "F",
    "Drake Powell": "G", "Julius Randle": "F", "Ben Saraf": "G", "Day'Ron Sharpe": "C",
    "Nolan Traore": "G", "Moritz Wagner": "F", "Danny Wolf": "F",
    # Charlotte
    "Grayson Allen": "G", "Christian Anderson": "G", "Pat Connaughton": "G", "Moussa Diabate": "F",
    "Dorian Finney-Smith": "F", "PJ Hall": "C", "Sion James": "G", "Ryan Kalkbrenner": "C",
    "Kon Knueppel": "G", "Tre Mann": "G", "Liam McNeeley": "G", "Brandon Miller": "F",
    "Royce O'Neale": "F", "Naz Reid": "C", "Tidjane Salaun": "F", "Hannes Steinbach": "F",
    "Coby White": "G", "Grant Williams": "F",
    # Chicago
    "Tobe Awaka": "F", "Matas Buzelis": "F", "Nic Claxton": "C", "Zach Collins": "F",
    "Rob Dillingham": "G", "Noa Essengue": "F", "Josh Giddey": "G", "Tre Jones": "G",
    "Mac McClung": "G", "Leonard Miller": "F", "Isaac Okoro": "F", "Norman Powell": "G",
    "Jalen Smith": "F", "Dailyn Swain": "G", "Patrick Williams": "F", "Caleb Wilson": "F",
    "Guerschon Yabusele": "F",
    # Cleveland
    "Jarrett Allen": "C", "Thomas Bryant": "C", "Tristan Enaruna": "F", "James Harden": "G",
    "Mario Hezonja": "F", "Sam Merrill": "G", "Riley Minix": "F", "Donovan Mitchell": "G",
    "Evan Mobley": "C", "Craig Porter Jr.": "G", "Tyrese Proctor": "G", "Olivier Sarr": "F",
    "Dennis Schroder": "G", "Max Strus": "G", "Meleek Thomas": "G", "Nae'Qwan Tomlin": "F",
    "Jaylon Tyson": "G", "Ernest Udeh Jr.": "C",
    # Dallas
    "Santi Aldama": "F", "Tarik Biberovic": "F", "Max Christie": "G", "Moussa Cisse": "C",
    "Sergio de Larrea": "F", "Cooper Flagg": "F", "Daniel Gafford": "F", "Jett Howard": "G",
    "Kyrie Irving": "G", "Vsevolod Ishchenko": "G", "Morez Johnson Jr.": "F", "Tobi Lawal": "F",
    "Dereck Lively II": "C", "Naji Marshall": "F", "Caleb Martin": "F", "John Poulakidas": "G",
    "Zaccharie Risacher": "F", "Marcus Sasser": "G", "Klay Thompson": "G", "P.J. Washington": "F",
    # Denver
    "Marvin Bagley III": "F", "Christian Braun": "G", "Trevon Brazile": "F", "Alpha Diallo": "F",
    "Aaron Gordon": "F", "DaRon Holmes II": "F", "Bryce Hopkins": "F", "Cameron Johnson": "F",
    "Nikola Jokic": "C", "Spencer Jones": "F", "Tyus Jones": "G", "Jamal Murray": "G",
    "Zeke Nnaji": "F", "Jalen Pickett": "G", "David Roddy": "F", "KJ Simpson": "G",
    "Julian Strawther": "G", "Lonnie Walker IV": "G", "Peyton Watson": "G",
    # Detroit
    "John Collins": "F", "Cade Cunningham": "G", "Jalen Duren": "C", "Javonte Green": "G",
    "Elijah Harkless": "G", "Gary Harris": "G", "Ronald Holland II": "F", "Kevin Huerter": "G",
    "Daniss Jenkins": "G", "Isaiah Joe": "G", "Isaac Jones": "C", "Chaz Lanier": "G",
    "Wendell Moore Jr.": "F", "Ebuka Okorie": "G", "Ugonna Onyenso": "C", "Taurean Prince": "F",
    "Paul Reed": "F", "Duncan Robinson": "F", "Tolu Smith": "F", "Ausar Thompson": "G",
    # Golden State
    "Charles Bassey": "C", "Jimmy Butler III": "F", "LJ Cryer": "G", "Stephen Curry": "G",
    "Draymond Green": "F", "Al Horford": "C", "Lajae Jones": "G", "Yaxel Lendeborg": "F",
    "Malevy Leons": "F", "De'Anthony Melton": "G", "Moses Moody": "G", "Gary Payton II": "G",
    "Brandin Podziemski": "G", "Kristaps Porzingis": "C", "Will Richard": "G", "Gui Santos": "F",
    "Nate Williams": "G",
    # Houston
    "Steven Adams": "C", "Bogdan Bogdanovic": "G", "Clint Capela": "C", "Quadir Copeland": "G",
    "Isaiah Crawford": "F", "Kevin Durant": "F", "Tari Eason": "F", "Tristen Newton": "G",
    "Alperen Sengun": "C", "Reed Sheppard": "G", "Marcus Smart": "G", "Jabari Smith Jr.": "F",
    "Jae'Sean Tate": "F", "Amen Thompson": "G", "Bruce Thornton": "G", "Fred VanVleet": "G",
    # Indiana
    "Kobe Brown": "G", "Johnny Furphy": "G", "Tyrese Haliburton": "G", "Jay Huff": "C",
    "Quenton Jackson": "G", "T.J. McConnell": "G", "Larry Nance Jr.": "F", "Andrew Nembhard": "G",
    "Aaron Nesmith": "G", "Kelly Oubre Jr.": "G", "Ben Sheppard": "G", "Pascal Siakam": "F",
    "Jalen Slawson": "F", "Braden Smith": "G", "Ethan Thompson": "G", "Obi Toppin": "F",
    "Jarace Walker": "F", "Ivica Zubac": "C",
    # LA Clippers
    "Johni Broome": "F", "Cam Christie": "G", "Kris Dunn": "G", "Darius Garland": "G",
    "Rui Hachimura": "F", "Isaiah Jackson": "F", "Derrick Jones Jr.": "F", "Kawhi Leonard": "F",
    "Brook Lopez": "C", "Nick Martinelli": "F", "Bennedict Mathurin": "G", "Baba Miller": "F",
    "Jordan Miller": "G", "Narcisse Ngoy": "F", "Yanic Konan Niederhauser": "C", "Kobe Sanders": "G",
    "Jamarion Sharp": "C", "Keaton Wagler": "G", "TyTy Washington Jr.": "G",
    # LA Lakers
    "Cameron Carr": "G", "Luka Doncic": "G", "Quentin Grimes": "G", "Jaden Hardy": "G",
    "Bronny James": "G", "Walker Kessler": "C", "Dalton Knecht": "F", "Jake LaRavia": "F",
    "Kevon Looney": "F", "Sandro Mamukelashvili": "F", "Chris Manon": "G", "AK Okereke": "F",
    "Austin Reaves": "G", "Collin Sexton": "G", "Adou Thiero": "F", "Matisse Thybulle": "G",
    "Jarred Vanderbilt": "F", "Ziaire Williams": "F",
    # Memphis
    "Cameron Boozer": "F", "Walter Clayton Jr.": "G", "Cedric Coward": "F", "Zach Edey": "C",
    "Taj Gibson": "F", "Jerami Grant": "F", "Taylor Hendricks": "F", "GG Jackson": "F",
    "Ty Jerome": "G", "AJ Johnson": "G", "Karim Lopez": "F", "Jahmai Mashack": "G",
    "Kris Murray": "F", "Scotty Pippen Jr.": "G", "Quinten Post": "C", "Olivier-Maxence Prosper": "F",
    "D'Angelo Russell": "G", "Richie Saunders": "G", "Javon Small": "G", "Cam Spencer": "G",
    "Isaiah Stewart": "F", "Jaylen Wells": "F",
    # Miami
    "Bam Adebayo": "C", "Giannis Antetokounmpo": "F", "Ryan Conwell": "G", "Tre Donaldson": "G",
    "Simone Fontecchio": "F", "Myron Gardner": "F", "Vladislav Goldin": "C", "Tim Hardaway Jr.": "G",
    "Nikola Jovic": "F", "Trevor Keels": "G", "Pelle Larsson": "G", "Davion Mitchell": "G",
    "Bobby Portis": "F", "Dru Smith": "G", "Andrew Wiggins": "F", "Jahmir Young": "G",
    # Milwaukee
    "Nate Ament": "F", "Brayden Burries": "G", "Ousmane Dieng": "F", "AJ Green": "G",
    "Tyler Herro": "G", "Kasparas Jakucionis": "G", "Jaime Jaquez Jr.": "F", "Kam Jones": "G",
    "Kyle Kuzma": "F", "Caris LeVert": "G", "Malique Lewis": "F", "Bogoljub Markovic": "F",
    "Pete Nance": "F", "Kevin Porter Jr.": "G", "Ryan Rollins": "G", "Cormac Ryan": "G",
    "Jericho Sims": "C", "Gary Trent Jr.": "G", "Myles Turner": "C", "Kel'el Ware": "C",
    # Minnesota
    "LaMelo Ball": "G", "Joan Beringer": "F", "Jaylen Clark": "G", "Donte DiVincenzo": "G",
    "Ayo Dosunmu": "G", "Anthony Edwards": "G", "Isaiah Evans": "G", "Enrique Freeman": "F",
    "Rudy Gobert": "C", "Josh Green": "G", "Bones Hyland": "G", "Trey Kaufman-Renn": "F",
    "Trey Lyles": "F", "Jaden McDaniels": "F", "Julian Phillips": "F", "Zyon Pullin": "G",
    "Terrence Shannon Jr.": "G", "Rocco Zikarsky": "C",
    # New Orleans
    "Saddiq Bey": "G", "Hunter Dickinson": "C", "Jeremiah Fears": "G", "Jordan Hawkins": "G",
    "Herbert Jones": "F", "DeAndre Jordan": "C", "Karlo Matkovic": "F", "Bryce McGowens": "G",
    "Yves Missi": "C", "Trey Murphy III": "F", "Dejounte Murray": "G", "Josh Oduro": "C",
    "Micah Peavy": "G", "Jaron Pierre Jr.": "G", "Jordan Poole": "G", "Derik Queen": "C",
    "Zion Williamson": "F",
    # New York
    "Jose Alvarado": "G", "OG Anunoby": "F", "Mikal Bridges": "G", "Jalen Brunson": "G",
    "Jordan Clarkson": "G", "Pacome Dadiet": "F", "Mohamed Diawara": "F", "Andre Drummond": "C",
    "Josh Hart": "G", "Jack Kayil": "G", "Tyler Kolek": "G", "Miles McBride": "G",
    "Kevin McCullar Jr.": "G", "Tyler Nickel": "F", "Landry Shamet": "G", "Karl-Anthony Towns": "C",
    # Orlando
    "Paolo Banchero": "F", "Desmond Bane": "G", "Goga Bitadze": "C", "Anthony Black": "G",
    "Jamal Cain": "F", "Jevon Carter": "G", "Wendell Carter Jr.": "C", "Colin Castleton": "C",
    "Tristan da Silva": "F", "Jonathan Isaac": "F", "Alex Morales": "G", "Izaiyah Nelson": "F",
    "Noah Penda": "F", "Jase Richardson": "G", "Jalen Suggs": "G", "Nikola Vucevic": "C",
    "Franz Wagner": "F",
    # Philadelphia (also includes LeBron James per ESPN's current roster --
    # a real trade after this assistant's knowledge cutoff, not a scraping
    # error; kept only for his position value, "F", which is stable
    # regardless of team.)
    "Dominick Barlow": "F", "Adem Bona": "C", "Jaylen Brown": "G", "Kentavious Caldwell-Pope": "G",
    "VJ Edgecombe": "G", "Justin Edwards": "F", "Joel Embiid": "C", "Ariel Hukporti": "C",
    "LeBron James": "F",
    "Caleb Love": "G", "Tyrese Maxey": "G", "Duke Miles": "G", "Labaron Philon Jr.": "G",
    "Rayan Rupert": "G", "Anfernee Simons": "G", "Dean Wade": "F", "Jabari Walker": "F",
    "Trendon Watford": "F",
    # Phoenix
    "Devin Booker": "G", "Jamaree Bouyea": "G", "Koby Brea": "G", "Miles Bridges": "F",
    "Dillon Brooks": "F", "Ryan Dunn": "F", "Rasheer Fleming": "F", "Collin Gillespie": "G",
    "Jordan Goodwin": "G", "Jalen Green": "G", "Haywood Highsmith": "F", "CJ Huntley": "F",
    "Oso Ighodaro": "F", "Luke Kennard": "G", "Isaiah Livers": "F", "Khaman Maluach": "C",
    "Koa Peat": "F", "Pat Spencer": "G", "Mark Williams": "C",
    # Portland
    "Deni Avdija": "F", "Toumani Camara": "F", "Branden Carlson": "C", "Sidy Cissoko": "G",
    "Donovan Clingan": "C", "Yang Hansen": "C", "Scoot Henderson": "G", "Jrue Holiday": "G",
    "Jayson Kent": "G", "Vit Krejci": "G", "Damian Lillard": "G", "Ja Morant": "G",
    "Micah Potter": "C", "Shaedon Sharpe": "G", "Jeremy Sochan": "F", "John Tonje": "F",
    "Robert Williams III": "C", "Chris Youngblood": "G",
    # Sacramento
    "Precious Achiuwa": "F", "Darius Acuff Jr.": "G", "Dylan Cardwell": "C", "Nique Clifford": "G",
    "Adam Flagler": "G", "De'Andre Hunter": "F", "Alex Karaban": "F", "Zach LaVine": "G",
    "Jonathan Mogbo": "F", "Malik Monk": "G", "Keegan Murray": "F", "Daeqwon Plowden": "G",
    "Maxime Raynaud": "C", "Domantas Sabonis": "F", "Emanuel Sharp": "G",
    # San Antonio
    "Harrison Barnes": "F", "Maliq Brown": "F", "Carter Bryant": "F", "Stephon Castle": "G",
    "Julian Champagnie": "F", "De'Aaron Fox": "G", "Ja'Kobi Gillespie": "G", "Dylan Harper": "G",
    "Tobias Harris": "F", "Harrison Ingram": "F", "Keldon Johnson": "F", "David Jones Garcia": "F",
    "Luke Kornet": "C", "Jordan McLaughlin": "G", "Emanuel Miller": "F", "Jayden Quaintance": "F",
    "Tarris Reed Jr.": "C", "Devin Vassell": "G", "Victor Wembanyama": "F",
    # Toronto
    "Kyle Anderson": "F", "Scottie Barnes": "F", "RJ Barrett": "F", "Jamison Battle": "F",
    "Nate Bittle": "C", "Jaden Bradley": "G", "Gradey Dick": "G", "Allen Graves": "F",
    "Chucky Hepburn": "G", "Brandon Ingram": "F", "Andre Jackson Jr.": "G", "Trayce Jackson-Davis": "F",
    "Trey Jemison III": "C", "A.J. Lawson": "G", "Alijah Martin": "G", "Collin Murray-Boyles": "F",
    "Jakob Poeltl": "C", "Immanuel Quickley": "G", "Jamal Shead": "G", "Ja'Kobe Walter": "G",
    # Utah
    "Trey Alexander": "G", "Ace Bailey": "G", "Mo Bamba": "C", "Tamar Bates": "G",
    "Isaiah Collier": "G", "Kyle Filipowski": "F", "Keyonte George": "G", "Jaxson Hayes": "C",
    "Blake Hinson": "F", "Jaren Jackson Jr.": "F", "John Konchar": "G", "Lauri Markkanen": "F",
    "Bez Mbeng": "G", "Svi Mykhailiuk": "G", "Jusuf Nurkic": "C", "Josh Okogie": "G",
    "Darryn Peterson": "G", "Brice Sensabaugh": "F", "Oscar Tshiebwe": "C", "Cody Williams": "F",
    # Washington (also includes Anthony Davis -- same real-trade situation as
    # LeBron/Philadelphia above, kept for his position value only)
    "Deandre Ayton": "C", "Anthony Davis": "F", "Bub Carrington": "G", "Justin Champagnie": "F",
    "Sharife Cooper": "G", "Bilal Coulibaly": "G", "AJ Dybantsa": "F", "Kyshawn George": "F",
    "Tre Johnson": "G", "Khris Middleton": "F", "Felix Okpara": "F", "Julian Reese": "F",
    "Will Riley": "G", "Alex Sarr": "C", "Tristan Vukcevic": "F", "Jamir Watkins": "G",
    "Cam Whitmore": "F", "Trae Young": "G",
}
