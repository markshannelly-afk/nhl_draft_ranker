import requests
import json
import time


# =========================
# CONFIG
# =========================

API_KEY = "pmx_097eb4b7d3702bd4861d94bfcaad1b4b"

YEAR = 2029

OUTPUT_FILE = (
    f"data/draft_{YEAR}.json"
)

GRAPHQL_URL = (
    "https://gql.eliteprospects.com/"
)



# =========================
# PARSE API
# =========================


def get_draft_class(year):

    url = (
        "https://api.parse.bot/scraper/"
        "46f9055c-a50d-4f31-9773-8755924ff8bd/"
        "get_draft_eligible"
    )

    r = requests.get(
        url,
        headers={
            "X-API-Key": API_KEY
        },
        params={
            "year": str(year)
        },
        timeout=30
    )

    r.encoding = "utf-8" 

    data = r.json()

    # =========================
    # FIX: HANDLE API STRUCTURE CHANGES
    # =========================

    if isinstance(data, list):
        return data

    if isinstance(data, dict):

        # old expected format
        if "data" in data and isinstance(data["data"], dict):
            if "prospects" in data["data"]:
                return data["data"]["prospects"]

        # alternative format
        if "prospects" in data:
            return data["prospects"]

    print("⚠️ Unexpected API format:")
    print(json.dumps(data, indent=2)[:1000])

    return []




# =========================
# GRAPHQL
# =========================


HEADERS = {

    "User-Agent":
    "Mozilla/5.0",

    "Origin":
    "https://www.eliteprospects.com",

    "Referer":
    "https://www.eliteprospects.com",

    "apollo-require-preflight":
    "true",

    "Content-Type":
    "application/json"

}




def get_stats(player_id):


    params = {

        "operationName":
        "PlayerStatisticsDefault",

        "variables":

        json.dumps({

            "player": str(player_id),

            "statsType":
            "default,projected",

            "leagueType":
            "league",

            "sort":
            "season"

        }),

        "extensions":

        json.dumps({

            "persistedQuery": {

                "version": 1,

                "sha256Hash":
                "2b19f87ae83e7cd9ee833de6abb875f88a7d641dfbea9aaba532493e6407536e"

            }

        })

    }


    try:

        r = requests.get(
            GRAPHQL_URL,
            headers=HEADERS,
            params=params,
            timeout=20
        )

        if r.status_code != 200:
            return None
        r.encoding = "utf-8" 

        return r.json()

    except Exception as e:

        print("GraphQL error:", e)

        return None


def get_player_details(player_id):

    params = {

        "operationName":
        "PlayerProfile",

        "variables":
        json.dumps({
            "player": str(player_id)
        }),

        "extensions":
        json.dumps({

            "persistedQuery": {

                "version": 1,

                "sha256Hash":
                "PUT_PROFILE_HASH_HERE"

            }

        })

    }


    try:

        r = requests.get(
            GRAPHQL_URL,
            headers=HEADERS,
            params=params,
            timeout=20
        )


        if r.status_code != 200:
            return {}


        return r.json()


    except Exception as e:

        print(
            "Profile error:",
            e
        )

    return {}

# =========================
# PARSE STATS
# =========================



    if not data:
        return {}

    blocks = []

    def walk(obj):

        if isinstance(obj, dict):

            if "GP" in obj:
                blocks.append(obj)

            for value in obj.values():
                walk(value)

        elif isinstance(obj, list):

            for item in obj:
                walk(item)

    walk(data)

    if not blocks:
        return {}

    goalie_blocks = [
        b for b in blocks
        if (
            "SV%" in b
            or "GAA" in b
            or "SO" in b
        )
    ]

    skater_blocks = [
        b for b in blocks
        if (
            "PTS" in b
            or "G" in b
            or "A" in b
        )
    ]


    # =========================
    # GOALIE
    # =========================

    if goalie_blocks:

        best = max(
            goalie_blocks,
            key=lambda x: int(x.get("GP") or 0)
        )

        return {

            "gp":
            best.get("GP") or 0,

            "goals": 0,
            "assists": 0,
            "points": 0,

            "pim":
            best.get("PIM") or 0,

            "plusMinus":
            None,

            "savePercentage":
            best.get("SV%"),

            "goalsAgainstAverage":
            best.get("GAA"),

            "shutouts":
            best.get("SO") or 0,

            "wins":
            best.get("W") or 0,

            "losses":
            best.get("L") or 0
        }


    # =========================
    # SKATER
    # =========================

    if skater_blocks:

        best = max(
            skater_blocks,
            key=lambda x: int(x.get("GP") or 0)
        )

        return {

            "gp":
            best.get("GP") or 0,

            "goals":
            best.get("G") or 0,

            "assists":
            best.get("A") or 0,

            "points":
            best.get("PTS") or 0,

            "pim":
            best.get("PIM") or 0,

            "plusMinus":
            best.get("PM")
        }

    return {}

def parse_stats(data):

    if not data:
        return {}


    edges = (
        data
        .get("data", {})
        .get("playerStats", {})
        .get("edges", [])
    )


    if not edges:
        return {}



    rows = []



    for edge in edges:

        season = edge.get("season")

        if not season:
            continue


        stats = edge.get("regularStats") or {}


        if not stats.get("GP"):
            continue



        # =========================
        # DETECT GOALIE
        # =========================

        is_goalie = (
            stats.get("SV%") is not None
            or stats.get("GAA") is not None
            or stats.get("SO") is not None
        )



        if is_goalie:

            rows.append({

                "season":
                f"{season.get('startYear')}-{str(season.get('endYear'))[-2:]}",


                "team":
                edge.get("teamName"),


                "league":
                edge.get("leagueName"),


                "gp":
                stats.get("GP") or 0,


                "goalsAgainstAverage":
                stats.get("GAA"),


                "savePercentage":
                stats.get("SV%"),


                "shutouts":
                stats.get("SO") or 0,


                "wins":
                stats.get("W") or 0,


                "losses":
                stats.get("L") or 0,


                "pim":
                stats.get("PIM") or 0,


                "plusMinus":
                None

            })


        else:

            rows.append({

                "season":
                f"{season.get('startYear')}-{str(season.get('endYear'))[-2:]}",


                "team":
                edge.get("teamName"),


                "league":
                edge.get("leagueName"),


                "gp":
                stats.get("GP") or 0,


                "goals":
                stats.get("G") or 0,


                "assists":
                stats.get("A") or 0,


                "points":
                stats.get("PTS") or 0,


                "pim":
                stats.get("PIM") or 0,


                "plusMinus":
                stats.get("PM")

            })




    if not rows:
        return {}



    # =========================
    # ONLY KEEP MOST RECENT SEASON
    # =========================


    # =========================
# KEEP MOST RECENT TWO SEASONS
# =========================

    seasons = sorted(
        list(
            set(
                r["season"]
                for r in rows
            )
        ),
        reverse=True
    )


    recent_seasons = seasons[:2]


    rows = [

        r for r in rows

        if r["season"] in recent_seasons

    ]



    return {

        "season":
        rows[0]["season"],


        "teams":
        rows

    }


# =========================
# RUN
# =========================


players = get_draft_class(YEAR)

print("Players:", len(players))

for i, player in enumerate(players):

    print(
        i + 1,
        "/",
        len(players),
        player["name"]
    )

    stats = get_stats(player["id"])

    parsed = parse_stats(stats)
    
    details = get_player_details(
        player["id"]
    )


    # Add profile information
    player.update(details)


    if "performanceStats" not in player:
        player["performanceStats"] = {}


    player["performanceStats"].update(parsed)


    print(
        player["name"],
        parsed
    )


    time.sleep(1)





# =========================
# SAVE
# =========================


with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        players,
        f,
        indent=4,
        ensure_ascii=False
    )

print()
print("Saved:", OUTPUT_FILE)