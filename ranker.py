import json
from datetime import datetime
import math
import os


# Config

DRAFT_YEAR = 2027

INPUT_FILE = f"data/draft_{DRAFT_YEAR}.json"
OUTPUT_FILE = f"data/ranked_{DRAFT_YEAR}.json"

LEAGUE_FILE = "data/league_weights.json"
CONFIG_FILE = "data/ranking_config.json"

# Load Data
# Load Data

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    players = json.load(f)


with open(LEAGUE_FILE, "r", encoding="utf-8") as f:
    league_data = json.load(f)


league_weights = {}

league_ppg = {}

league_age = {}

for league, data in league_data.items():

    if isinstance(data, dict):

        league_weights[league] = data.get(
            "league_weight",
            1.0
        )

        league_ppg[league] = data.get(
            "average_ppg",
            None
        )

        league_age[league] = data.get(
            "average_age",
            None
        )

    else:
        league_weights[league] = data
        league_ppg[league] = None
        league_age[league] = None


with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    config = json.load(f)

# CONFIG VALUES
POSITION_BONUS = config.get(
    "position_bonus",
    {}
)

POSITION_PRODUCTION_BONUS = config.get(
    "position_production_bonus",
    {}
)


ELITE_FORWARD_BONUS = config.get(
    "elite_forward_bonus",
    {} 
)


ELITE_PPG = config.get(
    "forward_ppg",
    {}
).get(
    "elite_ppg",
    {} 
)

FORWARD_PPG = config.get(
    "forward_ppg",
    {}
)

DEFENSE_PPG = config.get(
    "defense_ppg",
    {}
)

ELITE_DEFENSE_BONUS = config.get(
    "elite_defenseman_bonus",
    {} 
)

ELITE_DEFENSE_PPG = config.get(
    "elite_defense_thresholds",
    {}
).get(
    "defense_ppg",
    {} 
)

DEFENSE_SCORING_BONUS = config.get(
    "defense_scoring_bonus",
    {} 
)


DEFENSE_RARITY_BONUS = config.get(
    "defense_rarity_bonus",
    {} 
)


RHD_BONUS = config.get(
    "rhd_bonus",
    {} 
)

PLUS_MINUS_WEIGHT = config.get(
    "plus_minus_weight",
    0
)


MIN_SAMPLE_GAMES = config.get(
    "sample_size",
    {}
).get(
    "minimum_games",
    20
)


FULL_SEASON_GAMES = config.get(
    "sample_size",
    {}
).get(
    "full_season_games",
    60
)


SMALL_SAMPLE_PENALTY = config.get(
    "sample_size",
    {}
).get(
    "small_sample_penalty",
    {} 
)


RELIABILITY_STRENGTH = config.get(
    "sample_size",
    {}
).get(
    "reliability_strength",
    {} 
)

LEAGUE_DOMINANCE_CONFIG = config.get(
    "league_dominance",
    {}
)

SCORING_WEIGHTS = config.get(
    "scoring_weights",
    {} 
   
)

GOAL_SCORING = config.get(
    "goal_scoring",
    {}
)


GOALIE_CONFIG = config.get(
    "goalie",
    {}
)

TOURNAMENT_LEAGUES = [
    "WHC-17",
    "WHC-18",
    "WHC-20",
    "WJC"
]

AGE_CONFIG = config.get(
    "age_adjustment",
    {}
)

# This is a basic offset so that the most recent season's stats count more toward the score than previous seasons
# Helps if a player had a million points when they were 14.
SEASON_WEIGHTS = {
    "2025": 1.00,
    "2024": 0.25,
    "2023": 0.15,
    "2022": 0.05
}


def get_stats(player):

    return player.get(
        "performanceStats",
        {}
    )


def get_team_stats(player):
    return get_stats(player).get(
        "teams",
        []
    )

def safe_number(value):
    if value is None:
        return 0

    try:
        return float(value)

    except:
        return 0

def is_defenseman(player):

    positions = player.get(
        "position",
        []
    )

    if isinstance(
        positions,
        str
    ):
        positions = [positions]

    return any(
        pos in ["D","LD","RD"]
        for pos in positions
    )

def is_goalie(player):

    positions = player.get(
        "position",
        []
    )

    if isinstance(
        positions,
        str
    ):
        positions = [positions]


    return any(
        pos in [
            "G",
            "GK",
            "Goalie"
        ]
        for pos in positions
    )

def get_primary_position(player):

    positions = player.get(
        "position",
        []
    )

    if isinstance(
        positions,
        str
    ):
        return positions


    if not positions:
        return None

    return positions[0]


def get_season_weight(season):

    if not season:
        return 0.75

    return SEASON_WEIGHTS.get(
        season[:4],
        0.75
    )

def calculate_age(dob):

    if not dob:
        return None

    try:

        birth = datetime.strptime(
            dob,
            "%Y-%m-%d"
        )

        today = datetime.now()

        return round(
            (
                today - birth
            ).days / 365.25,
            2
        )

    except:
        return None



def calculate_relative_age_factor(player, league_info):

    if not AGE_CONFIG.get("enabled", True):
        return 1.0

    age = player.get("age")

    if not age:
        return 1.0

    age = int(float(age))

    league_average_age = league_info.get(
        "average_age"
    )

    if not league_average_age:
        return 1.0

    if age < league_average_age:
        return 1.02

    if age > league_average_age + 1:
        return 0.97

    return 1.0

def height_to_inches(height):

    if not height:
        return 0

    try:

        feet, inches = height.replace(
            '"',
            ''
        ).split("'")

        return (
            int(feet) * 12
            +
            int(inches)
        )

    except:
        return 0
    
# Combines seasons using:
# - league strength (from league_weights.jaon)
# - season weighting (sample size) 
# - tournament weighting (tournament seasons are slightly reduced) 
# - goalie weighted averages

def calculate_weighted_stats(player):

    teams = get_team_stats(player)

    totals = {

        "points": 0,
        "goals": 0,
        "assists": 0,

        "gp": 0,

        "pim": 0,
        "plusMinus": 0,

        "goalsAgainstAverage": None,
        "savePercentage": None,

        "gaa_total": 0,
        "gaa_games": 0,

        "save_total": 0,
        "save_games": 0,

        "shutouts": 0,
        "wins": 0,
        "losses": 0,

        "league": "",
        "primaryLeague": "",

        "breakdown": []

    }


    if not teams:
        return totals

    seasons = {}

    for team in teams:

        season = team.get(
            "season",
            "unknown"
        )


        seasons.setdefault(
            season,
            []
        ).append(team)

    league_games = {}

    goalie_contribution = 0

    for season, season_teams in seasons.items():

        season_weight = get_season_weight(
            season
        )

        eligible = []

        for team in season_teams:

            league = team.get(
                "league",
                ""
            )

            if league in TOURNAMENT_LEAGUES:

                tournament_multiplier = config.get(
                    "tournament_weights",
                    {}
                ).get(
                    league,
                    0.50
                )

                multiplier = (
                    league_weights.get(
                        league,
                        1.0
                    )
                    *
                    tournament_multiplier
                    *
                    season_weight
                )

                gp = safe_number(
                    team.get("gp")
                )

                totals["breakdown"].append({
                    **team,
                    "weight": round(
                        multiplier,
                        3
                    ),

                    "weightedPoints": round(
                        safe_number(team.get("points"))
                        *
                        multiplier,
                        2
                    ),

                    "goalieContribution": 0

                })

                # add tournament production into totals

                if not is_goalie(player):

                    totals["points"] += (
                        safe_number(
                            team.get("points")
                        )
                        *
                        multiplier
                    )

                    totals["goals"] += (
                        safe_number(
                            team.get("goals")
                        )
                        *
                        multiplier
                    )

                    totals["assists"] += (
                        safe_number(
                            team.get("assists")
                        )
                        *
                        multiplier
                    )

                    totals["pim"] += (
                        safe_number(
                            team.get("pim")
                        )
                        *
                        multiplier
                    )

                # weighted games for rate stats
                totals["gp"] += gp

                league_games[league] = (
                    league_games.get(
                        league,
                        0
                    )
                    +
                    gp
                )

                continue


            else:

                eligible.append(team)

        if not eligible:
            continue

        # strongest league displays first
        eligible.sort(

            key=lambda x: (

                league_weights.get(
                    x.get("league",""),
                    0.75
                ),

                safe_number(
                    x.get("gp")
                )

            ),

            reverse=True

        )
        
        # Only count the top 3 leagues per season
       # eligible = eligible[:3]

        sample_games = 0

        for index, team in enumerate(eligible):

            league = team.get(
                "league",
                ""
            )

            gp = safe_number(
                team.get(
                    "gp"
                )
            )

            multiplier = (
                season_weight *
                league_weights.get(
                    league,
                    1.0
                )
            )
            
            # secondary teams matter,
            # but not as much as primary

            if index > 0:

                multiplier *= 0.15

                # Only count primary team/season for sample size
            if index == 0:
                sample_games += gp

            totals["gp"] += gp

            if not is_goalie(player):

                totals["points"] += (
                    safe_number(
                        team.get("points")
                    )
                    *
                    multiplier
                )

                totals["goals"] += (
                    safe_number(
                        team.get("goals")
                    )
                    *
                    multiplier
                )

                totals["assists"] += (
                    safe_number(
                        team.get("assists")
                    )
                    *
                    multiplier
                )

                totals["pim"] += (
                    safe_number(
                        team.get("pim")
                    )
                    *
                    multiplier
                )

                totals["plusMinus"] += (
                    safe_number(
                        team.get("plusMinus")
                    )
                    *
                    multiplier
                )

            else:

                gaa = team.get(
                    "goalsAgainstAverage"
                )


                if gaa is not None and gp > 0:

                    totals["gaa_total"] += (
                        safe_number(
                            gaa
                        )

                        *
                        gp
                    )


                    totals["gaa_games"] += gp

                save = team.get(
                    "savePercentage"
                )

                if save is not None and gp > 0:
                    totals["save_total"] += (
                        safe_number(
                            save
                        )
                        *
                        gp
                    )


                    totals["save_games"] += gp
                    
                totals["wins"] += (
                    safe_number(team.get("wins"))
                    *
                    multiplier
                )

                totals["shutouts"] += (
                    safe_number(team.get("shutouts"))
                    *
                    multiplier
                )


                totals["losses"] += safe_number(
                    team.get(
                        "losses"
                    )
                )

                if gaa is not None:
                    goalie_contribution += max(
                        (
                            GOALIE_CONFIG.get(
                                "gaa_baseline",
                                3.00
                            )
                            -
                            safe_number(gaa)
                        )
                        *
                        GOALIE_CONFIG.get(
                            "gaa_weight",
                            10
                        ),
                        0
                    )

                goalie_contribution += (
                    safe_number(
                        team.get("shutouts")
                    )
                    *
                    GOALIE_CONFIG.get(
                        "shutout_bonus",
                        1
                    )
                )


           

            league_games[league] = (

                league_games.get(
                    league,
                    0
                )
                +
                gp
            )

            totals["breakdown"].append({

                "season": season,

                "league": league,

                "team": team.get(
                    "team",
                    ""
                ),

                "gp": gp,

                "points": safe_number(
                    team.get("points")
                ),

                "goals": safe_number(
                    team.get("goals")
                ),

                "assists": safe_number(
                    team.get("assists")
                ),

                "pim": safe_number(
                    team.get("pim")
                ),

                "plusMinus": team.get(
                    "plusMinus"
                ),

                    "goalsAgainstAverage": team.get(
                    "goalsAgainstAverage"
                ),

                "savePercentage": team.get(
                    "savePercentage"
                ),

                "wins": safe_number(
                    team.get("wins")
                ),

                "losses": safe_number(
                    team.get("losses")
                ),

                "shutouts": safe_number(
                    team.get("shutouts")
                ),

                "weight": round(
                    multiplier,
                    3
                ),

                "weightedPoints": round(

                (
                    safe_number(team.get("points"))
                    *
                    multiplier
                )

                if not is_goalie(player)

                else

                (
                    (
                        max(
                            (
                                GOALIE_CONFIG.get(
                                    "gaa_baseline",
                                    3.00
                                )
                                -
                                safe_number(
                                    team.get("goalsAgainstAverage")
                                )
                            )
                            *
                            GOALIE_CONFIG.get(
                                "gaa_weight",
                                10
                            ),
                            0
                        )
                        +
                        (
                            safe_number(
                                team.get("shutouts")
                            )
                            *
                            GOALIE_CONFIG.get(
                                "shutout_bonus",
                                1
                            )
                        )
                    )
                    *
                    multiplier
                ),

                2
            ),

                "goalieContribution": round(
                    (
                        max(
                            (
                                GOALIE_CONFIG.get(
                                    "gaa_baseline",
                                    3.00
                                )
                                -
                                safe_number(
                                    team.get("goalsAgainstAverage")
                                )
                            )
                            *
                            GOALIE_CONFIG.get(
                                "gaa_weight",
                                10
                            ),
                            0
                        )
                        +
                        (
                            safe_number(
                                team.get("shutouts")
                            )
                            *
                            GOALIE_CONFIG.get(
                                "shutout_bonus",
                                1
                            )
                        )
                    )
                    *
                    multiplier,
                    2
                )
                if is_goalie(player)
                else 0

            })
            
    if totals["gaa_games"] > 0:

        totals["goalsAgainstAverage"] = (

            totals["gaa_total"]

            /

            totals["gaa_games"]

        )


    if totals["save_games"] > 0:

        totals["savePercentage"] = (

            totals["save_total"]

            /

            totals["save_games"]

        )


    if league_games:


        totals["primaryLeague"] = max(
    league_games,
    key=lambda league: league_games[league]
)

        totals["league"] = totals["primaryLeague"]
        totals["sampleGames"] = sample_games

    return totals


def calculate_ppg(player):
    stats = player.get(
        "weightedStats",
        {}
    )

    gp = safe_number(
        stats.get(
            "sampleGames",
            stats.get("gp", 0)
        )
    )

    if gp <= 0:
        return 0

    if gp <= 0:
        return 0

    return (
        safe_number(
            stats.get("points")
        )
        /
        gp
    )


def calculate_actual_ppg(player):
    stats = player.get(
        "primaryStats",
        {}
    )

    gp = safe_number(
        stats.get("gp")
    )

    if gp <= 0:
        return 0

    return (
        safe_number(
            stats.get("points")
        )
        /
        gp
    )


def get_display_stats(player):
    teams = get_team_stats(player)

    if not teams:
        return {}


    # remove tournaments
    teams = [
        t for t in teams
        if t.get("league") not in TOURNAMENT_LEAGUES
    ]

    if not teams:
        return {}

    # newest season first
    teams.sort(
        key=lambda x: (
            x.get("season",""),
            league_weights.get(
                x.get("league",""),
                0
            ),
            safe_number(x.get("gp"))
        ),
        reverse=True
    )

    team = teams[0]

    return {

        "league": team.get("league",""),

        "team": team.get("team",""),

        "gp": safe_number(team.get("gp")),

        "goals": safe_number(team.get("goals")),

        "assists": safe_number(team.get("assists")),

        "points": safe_number(team.get("points")),

        "pim": safe_number(team.get("pim")),

        "plusMinus": safe_number(team.get("plusMinus")),

        # goalie stats
        "goalsAgainstAverage": team.get(
            "goalsAgainstAverage"
        ),

        "savePercentage": team.get(
            "savePercentage"
        ),

        "wins": safe_number(
            team.get("wins")
        ),

        "losses": safe_number(
            team.get("losses")
        ),

        "shutouts": safe_number(
            team.get("shutouts")
        )

    }

def calculate_pm_pg(player):
    stats = player.get(
        "weightedStats",
        {}
    )


    gp = stats.get(
        "sampleGames",
        stats.get("gp", 0)
    )

    if gp <= 0:

        return 0

    return (

        safe_number(
            stats.get("plusMinus")
        )
        /
        gp
    )



def calculate_pim_pg(player):
    stats = player.get(
        "weightedStats",{}
    )

    gp = stats.get(
        "sampleGames",
        stats.get("gp", 0)
    )

    if gp <= 0:

        return 0

    return (
        safe_number(
            stats.get("pim")
        )
        /
        gp
    )


def calculate_size_profile(player):

    height = height_to_inches(
        player.get("height")
    )
    
    weight = safe_number(
        player.get("weight")
    )

    size = config.get(
        "size_profile",
        {}
    )

    if (
        height >= size.get("elite_size", {}).get("height", 999)
        and
        weight >= size.get("elite_size", {}).get("weight", 999)
    ):

        return (
            size["elite_size"]["bonus"],
            "Elite Size"
        )

    if (
        height >= size.get("large_frame", {}).get("height", 999)
        and
        weight >= size.get("large_frame", {}).get("weight", 999)
    ):

        return (
            size["large_frame"]["bonus"],
            "Large Frame"
        )

    if (
        height <= 70
        and
        calculate_ppg(player)
        >=
        size.get(
            "undersized_skill",
            {}
        ).get(
            "ppg",
            999
        )
    ):

        return (
            size["undersized_skill"]["bonus"],
            "Undersized Skill"
        ):

    if (
        height <= 70
        and
        weight <= 150
        and
        calculate_ppg(player)
        >= 
        size.get(
            "undersized_developing", 
            {}
        ).get(
            "ppg", 
            999
        )
    ):
        return (
            size["undersized_developing"]["bonus"],
            "Undersized Developing" 
        ):
        
    return (
        1.0,
        "Average"
    )
    
def calculate_league_dominance(player):

    stats = player.get(
        "weightedStats",
        {}
    )

    league = stats.get(
        "league",
        ""
    )

    gp = safe_number(
        stats.get("gp")
    )

    points = safe_number(
        stats.get("points")
    )

    if gp <= 0:
        return 1.0

    ppg = points / gp

    dominance = LEAGUE_DOMINANCE_CONFIG.get(
        league,
        {}
    )

    baseline = dominance.get(
        "average_ppg"
    )

    if not baseline:
        return 1.0

    max_bonus = dominance.get(
        "max_bonus",
        1.10
    )

    ratio = ppg / baseline

    multiplier = 1 + (
        (ratio - 1)
        *
        0.10
    )

    return min(
        max(
            multiplier,
            0.95
        ),
        max_bonus
    )
    
def calculate_score(player):

    stats = player.get(
    "primaryStats",
    {}
    )

    breakdown = {}

    if is_goalie(player):

        gp = safe_number(
            stats.get(
                "sampleGames",
                stats.get("gp", 0)
            )
        )

        gaa = stats.get(
            "goalsAgainstAverage"
        )

        if gaa is not None:
            gaa = safe_number(gaa)

        if gaa is None:
            gaa = GOALIE_CONFIG.get(
                "gaa_baseline",
                3.00
            )

        shutouts = safe_number(
            stats.get(
                "shutouts",
                0
            )
        )

        league_multiplier = league_weights.get(
            stats.get(
                "league",
                ""
            ),
            0.75
        )
    
        if gaa is None:

            gaa = GOALIE_CONFIG.get(
                "gaa_baseline",
                3.00
            )

        score = GOALIE_CONFIG.get(
            "base_score",
            50
        )

        gaa_bonus = max(
            (
                GOALIE_CONFIG.get(
                    "gaa_baseline",
                    3.00
                )
                
                -
                
                gaa
            )

            *

            GOALIE_CONFIG.get(
                "gaa_weight",
                10
            )

            *

            league_multiplier,

            0

        )

        score += gaa_bonus

        shutout_bonus = (

            shutouts

            *
            
            GOALIE_CONFIG.get(
                "shutout_bonus",
                1
            )

            *

            league_multiplier

        )

        score += shutout_bonus

        breakdown["goalieGAA"] = round(
            gaa,
            2
        )

        breakdown["gaaBonus"] = round(
            gaa_bonus,
            2
        )

        breakdown["shutoutBonus"] = round(
            shutout_bonus,
            2
        )

        breakdown["shutouts"] = shutouts

        breakdown["gamesPlayed"] = gp

        breakdown["league"] = league_multiplier

        if gp < MIN_SAMPLE_GAMES:

            score *= SMALL_SAMPLE_PENALTY

        elif gp >= FULL_SEASON_GAMES:

            score *= (
                1 +
                RELIABILITY_STRENGTH
            )

            breakdown["sampleSize"] = (
                1 +
                RELIABILITY_STRENGTH
            )

        return (
            round(score,2),
            breakdown
        )

    points = safe_number(
        stats.get("points")
    )

    goals = safe_number(
        stats.get("goals")
    )

    assists = safe_number(
        stats.get("assists")
    )

    gp = safe_number(
        stats.get("gp")
    )


    league = stats.get(
    "league",
    ""
    )

    league_multiplier = league_weights.get(
        league,
        0.75
    )


    production_score = math.sqrt(

        (

            points
            *
            SCORING_WEIGHTS.get(
                "points",
                1
            )

            +

            goals
            *
            SCORING_WEIGHTS.get(
                "goals",
                1
            )

            +

            assists
            *
            SCORING_WEIGHTS.get(
                "assists",
                1
            )

        )

    ) * 12
    
    

    production_score *= (
    1 +
    ((league_multiplier - 1) * 0.5)
    )

    player_type = determine_player_type(player)

    if is_defenseman(player):

        if player_type == "Shutdown Defenseman":

            ppg = calculate_ppg(player)

            league_average_ppg = league_ppg.get(
                league
            )

            if league_average_ppg is not None:

                if ppg < league_average_ppg:

                    production_score *= 1.10

    score = production_score

    league_dominance_multiplier = calculate_league_dominance(player)
    
    score *= league_dominance_multiplier
    
    breakdown["leagueDominance"] = round(
        league_dominance_multiplier,
        3
    )
    
    league = stats.get(
    "league",
    ""
    )

    league_info = league_data.get(
        league,
        {}
    )

    age_multiplier = calculate_relative_age_factor(
        player,
        league_info
    )

    score *= age_multiplier
    breakdown["age"] = age_multiplier


    nhl_translation = calculate_nhl_translation(player)

    score *= nhl_translation

    breakdown["nhlTranslation"] = round(
        nhl_translation,
        3
    )

    breakdown["production"] = round(
        production_score,
        2
    )

    breakdown["league"] = league_multiplier

    pim_pg = calculate_pim_pg(player)

    
    discipline_multiplier = 1.0


    discipline = config.get(
        "discipline",
        {}
    )


    if pim_pg <= discipline.get(
    "elite_pim_pg",
    0
):

        discipline_multiplier = discipline.get(
            "elite_bonus",
            1
        )

    elif pim_pg <= discipline.get(
        "good_pim_pg",
        0
    ):

        discipline_multiplier = discipline.get(
            "good_bonus",
            1
        )

    elif pim_pg >= discipline.get(
        "poor_pim_pg",
        999
    ):

        discipline_multiplier = discipline.get(
            "poor_penalty",
            1
        )

    

    player_type = determine_player_type(player)

    discipline_effect = 1.0

    if is_defenseman(player):

        if player_type == "Shutdown Defenseman":
            discipline_effect = 0.50

        elif player_type == "Two-Way Defenseman":
            discipline_effect = 0.75

    discipline_multiplier = (
        1 +
        ((discipline_multiplier - 1) * discipline_effect)
    )

    score *= discipline_multiplier
    breakdown["discipline"] = round(
    discipline_multiplier,
    2
)

    breakdown["pimPerGame"] = round(
        pim_pg,
        3
    )

    ppg = calculate_ppg(player)

    

    ppg_multiplier = 1.0

    if is_defenseman(player):

        if ppg >= DEFENSE_PPG.get("elite_ppg",999):

            ppg_multiplier = DEFENSE_PPG.get(
                "elite_bonus",
                1
            )

        elif ppg >= DEFENSE_PPG.get("good_ppg",999):

            ppg_multiplier = DEFENSE_PPG.get(
                "good_bonus",
                1
            )
            
    else:

        if ppg >= FORWARD_PPG.get("elite_ppg",999):

            ppg_multiplier = FORWARD_PPG.get(
                "elite_bonus",
                1
            )

        elif ppg >= FORWARD_PPG.get("high_ppg",999):

            ppg_multiplier = FORWARD_PPG.get(
                "high_bonus",
                1
            )

        elif ppg >= FORWARD_PPG.get("good_ppg",999):

            ppg_multiplier = FORWARD_PPG.get(
                "good_bonus",
                1
            )

        elif ppg >= FORWARD_PPG.get("solid_ppg",999):

            ppg_multiplier = FORWARD_PPG.get(
                "solid_bonus",
                1
            )

    score *= ppg_multiplier
    
    breakdown["ppgMultiplier"] = ppg_multiplier

    goal_bonus = 1.0

    goals = safe_number(stats.get("goals"))
    points = safe_number(stats.get("points"))
    gp = safe_number(stats.get("gp"))
    
    if GOAL_SCORING.get("enabled", True):

        goal_ratio = goals / max(points, 1)
        goals_per_game = goals / max(gp, 1)

        if goals_per_game >= GOAL_SCORING.get(
            "minimum_goals_per_game",
            0.45
        ):

            if goal_ratio >= GOAL_SCORING.get(
                "elite_goal_ratio",
                0.55
            ):

                goal_bonus = GOAL_SCORING.get(
                    "elite_bonus",
                    1.06
                )

            elif goal_ratio >= GOAL_SCORING.get(
                "good_goal_ratio",
                0.45
            ):

                goal_bonus = GOAL_SCORING.get(
                    "good_bonus",
                    1.03
                )

    score *= goal_bonus

    breakdown["goalScoring"] = goal_bonus

    position = get_primary_position(
        player
    )

    position_multiplier = POSITION_BONUS.get(
        position,
        1.0
    )

    breakdown["positionProduction"] = 1.0
    
    score *= position_multiplier

    position_production = config.get(
        "position_production_bonus",
        {}
    ).get(
        position,
        1.0
    )

    score *= position_production

    breakdown["positionProduction"] = position_production


    breakdown["position"] = position_multiplier

    if is_defenseman(player):
        
        score *= DEFENSE_SCORING_BONUS

        breakdown["defenseScoring"] = DEFENSE_SCORING_BONUS

        breakdown["defenseRarity"] = DEFENSE_RARITY_BONUS


        if player.get(
            "shoots"
        ) == "R":


            score *= RHD_BONUS

            breakdown["rhd"] = RHD_BONUS


        else:

            breakdown["rhd"] = 1.0

        if ppg >= ELITE_DEFENSE_PPG:

            score *= ELITE_DEFENSE_BONUS

            breakdown["eliteDefense"] = ELITE_DEFENSE_BONUS

    else:
        
        if ppg >= ELITE_PPG:

            score *= ELITE_FORWARD_BONUS

            breakdown["eliteForward"] = ELITE_FORWARD_BONUS

    # ---------------------------------------------------------
# Archetype-specific adjustments
# ---------------------------------------------------------

    size_multiplier, size_label = calculate_size_profile(player)

    size_effect = 1.0
    discipline_effect = 1.0
    rhd_effect = 1.0

    if is_defenseman(player):
        if player_type == "Shutdown Defenseman":

            size_effect = 1.75
            discipline_effect = 0.50
            rhd_effect = 1.08

        elif player_type == "Two-Way Defenseman":

            size_effect = 1.40
            discipline_effect = 0.75
            rhd_effect = 1.05

        elif player_type == "Offensive Defenseman":

            size_effect = 0.75
            discipline_effect = 1.00
            rhd_effect = 1.03

    # Apply size weighting
    adjusted_size = (
        1 +
        ((size_multiplier - 1) * size_effect)
    )

    score *= adjusted_size

    breakdown["size"] = round(adjusted_size, 3)
    breakdown["sizeProfile"] = size_label

# Upgrade RHD bonus based on archetype
    if is_defenseman(player) and player.get("shoots") == "R":

        score /= RHD_BONUS
        score *= rhd_effect

        breakdown["rhd"] = rhd_effect

    archetype_multiplier = 1.0


    archetype_config = config.get(
        "archetypes",
        {}
    )

    if player_type in archetype_config:

        archetype_multiplier = archetype_config[player_type].get(
            "bonus",
            1.0
        )

    breakdown["archetype"] = player_type
    breakdown["archetypeMultiplier"] = archetype_multiplier

    score *= archetype_multiplier

    pm_pg = calculate_pm_pg(player)

    plus_minus_multiplier = 1.0


    if PLUS_MINUS_WEIGHT > 0:

        if is_defenseman(player):
            plus_minus_multiplier = (
                1 +
                (pm_pg * PLUS_MINUS_WEIGHT * 0.25)
            )
        else:
            plus_minus_multiplier += (
                pm_pg *
                PLUS_MINUS_WEIGHT
            )

        score *= plus_minus_multiplier


    breakdown["plusMinus"] = round(
        plus_minus_multiplier,
        3
    )

    gp = stats.get(
        "sampleGames",
        stats.get("gp", 0)
    )

    if gp < MIN_SAMPLE_GAMES:

        score *= SMALL_SAMPLE_PENALTY

        breakdown["sampleSize"] = SMALL_SAMPLE_PENALTY

    else:

        reliability = min(

            gp / FULL_SEASON_GAMES,

            1.0

        )

        reliability_bonus = (

            1
            +

            reliability
            *
            RELIABILITY_STRENGTH
        )

        score *= reliability_bonus

        breakdown["sampleSize"] = reliability_bonus

    return (
        round(score,2),
        breakdown
    )

def calculate_forward_production(player):

    stats = player.get(
        "weightedStats",
        {}
    )

    points = safe_number(stats.get("points"))
    goals = safe_number(stats.get("goals"))
    assists = safe_number(stats.get("assists"))

    production_score = math.sqrt(

        (
            points
            *
            SCORING_WEIGHTS.get(
                "points",
                1
            )

            +

            goals
            *
            SCORING_WEIGHTS.get(
                "goals",
                1
            )

            +

            assists
            *
            SCORING_WEIGHTS.get(
                "assists",
                1
            )
        )

    ) * 10

    return production_score



def determine_player_type(player):

    ppg = calculate_ppg(player)

    pm_pg = calculate_pm_pg(player)

    height = height_to_inches(
        player.get("height")
    )

    weight = safe_number(
        player.get("weight")
    )

    positions = player.get(
        "position",
        []
    )

    if isinstance(positions, str):
        positions = [positions]


    positions = [
        p.strip()
        for p in positions
    ]


    if "D" in positions:

        if ppg >= 0.75:
            return "Offensive Defenseman"

        elif (
            height >= 74
            and weight >= 180
            and ppg < 0.50
        ):
            return "Shutdown Defenseman"

        else:
            return "Two-Way Defenseman"
            
    if "G" in positions:

        return "Goaltender"


    if any(
        pos in ["C","LW","RW"]
        for pos in positions
    ):

        # Don't classify based only on size.
        # Large + productive = power forward candidate.
        # Large + elite scoring = scorer with size.

        if (
            height >= 74
            and
            weight >= 200
            and
            ppg >= 0.75
        ):
            return "Power Forward"

        if (
            pm_pg >= 0.25
            and
            ppg < 0.75
        ):

            return "Defensive Forward"

        if (
            pm_pg >= 0.25
            and
            ppg >= 0.85
        ):

            return "Two-Way Forward"


        points = safe_number(
            player.get("weightedStats", {}).get("points")
        )

        assists = safe_number(
            player.get("weightedStats", {}).get("assists")
        )

        assist_rate = 0

        if points > 0:
            assist_rate = assists / points


        if (
            ppg >= 0.75
            and
            assist_rate >= 0.55
        ):
            return "Playmaker"


        if ppg >= 1.0:
            return "Offensive Forward"

    return "Balanced Forward"

def generate_projection(player):

    player_type = determine_player_type(player)

    stats = player.get(
        "weightedStats",
        {}
    )


    score = player.get(
        "draftScore",
        0
    )

    gp = stats.get(
        "sampleGames",
        stats.get("gp", 0)
    )


    ppg = calculate_actual_ppg(
        player
    )


    stars = 2.5

    tier = "Depth Prospect"

    role = "Development Player"

    style = []

    summary = []

    if is_goalie(player):

        if score >= 220:

            stars = 5
            tier = "Franchise Goaltender"
            role = "Elite Starter"

        elif score >= 175:

            stars = 4.5
            tier = "Elite Goaltender"
            role = "Starting Goaltender"

        elif score >= 125:

            stars = 4
            tier = "NHL Starter Candidate"
            role = "Tandem Goaltender"

        elif score >= 75:

            stars = 3.5
            tier = "Tandem Goaltender"
            role = "Backup Goaltender"

        else:
            
            stars = 3
            tier = "Development Goaltender"
            role = "Depth"

        style.append(
            "Butterfly"
        )

    elif is_defenseman(player):

        if score >= 240:

            stars = 5
            tier = "Franchise Defenseman"
            role = "Franchise Defenseman"


        elif score >= 190:

            stars = 4.5
            tier = "Elite Defenseman"
            role = "Top 2 Defenseman"


        elif score >= 150:

            stars = 4
            tier = "Top Four Defenseman"
            role = "Top 4 Defenseman"


        elif score >= 110:

            stars = 3.5
            tier = "Middle Pair Defenseman"
            role = "Top 6 Defenseman"

        elif score >= 80:
            stars = 3
            role = "Depth Defenseman"

        else:

            stars = 2
            tier = "Depth Defenseman"
            role = "Long-Shot Prospect"

        if player.get(
            "shoots"
        ) == "R":

            style.append(
                "Right Shot"
            )


        if ppg >= ELITE_DEFENSE_PPG:

            style.append(
                "Offensive Driver"
            )

    else:

        if score >= 250:
            
            stars = 5
            tier = "Franchise Forward"
            role = "Franchise Forward"

        elif score >= 190:

            stars = 4.5
            tier = "Elite Prospect"
            role = "Top Line Forward"

        elif score >= 150:

            stars = 4
            tier = "Top Six Forward"
            role = "Top Six Forward"

        elif score >= 115:

            stars = 3.5
            tier = "Middle Six Forward"
            role = "Secondary Scorer"

        elif score >= 85:

            stars = 3
            tier = "Depth Forward"
            role = "Depth Forward"

        else:
            stars = 2
            role = "Longshot Prospect"

        if player_type == "Power Forward":

            style.append(
                "Power Forward"
            )


        elif player_type == "Defensive Forward":
            
            style.append(
                "Shutdown Forward"
            )

        elif player_type == "Two-Way Forward":

            style.append(
                "Two-Way"
            )

        elif stats.get("goals",0) > stats.get("assists",0):

            style.append(
                "Goal Scorer"
            )

        else:

            style.append(
                "Playmaker"
            )

    confidence = "Medium"

    if is_goalie(player):
        if gp >= 30:
            confidence = "High"
    else:
        if gp >= 50:
            confidence = "High"

    return {

        "stars": stars,

        "role": role,

        "confidence": confidence,

        "summary": " | ".join(summary)

    }

def calculate_nhl_translation(player):

    multiplier = 1.0

    if is_defenseman(player):

        height = height_to_inches(player.get("height"))
        weight = safe_number(player.get("weight"))
        age = player.get("age", 18)

        if height >= 74:
            multiplier += 0.02

        if weight >= 185:
            multiplier += 0.02

    return multiplier

def generate_scouting_report(player):

    stats = player.get("weightedStats", {})

    score = player.get(
        "draftScore",
        0
    )


    gp = stats.get(
        "sampleGames",
        stats.get("gp", 0)
    )   

    traits = []

    if is_defenseman(player):

        if player.get(
            "shoots"
        ) == "R":

            traits.append(
                "Right-shot defenseman"
            )

    if gp >= 60:

        traits.append(
            "Full-season sample"
        )


    elif gp < 20:

        traits.append(
            "Limited sample size"
        )

    if calculate_actual_ppg(player) >= 1.0:

        traits.append(
            "Elite offensive production"
        )

    if is_goalie(player):

        if score >= 150:

            traits.append(
                "High-end goaltending profile"
            )

    return traits

for index, player in enumerate(players):

    print(
        f"{index + 1}/{len(players)}",
        player.get(
            "name"
        )
    )

    player["age"] = calculate_age(
        player.get("dateOfBirth")
    )

    weighted_stats = calculate_weighted_stats(player)

    player["weightedStats"] = weighted_stats
    
    latest_teams = get_display_stats(player)
    player["primaryStats"] = latest_teams

    player["ppg"] = round(
        calculate_actual_ppg(player),
        3
    )
    player["weightedPPG"] = round(
        calculate_ppg(player),
        3
    )

    score, breakdown = calculate_score(
        player
    )

    player["draftScore"] = score

    player["scoreBreakdown"] = breakdown

    player["projection"] = generate_projection(
        player
    )

    player["playerType"] = determine_player_type(
    player
    )
    
    player["scoutingReport"] = generate_scouting_report(
        player
    )

    player["leagueBreakdown"] = weighted_stats.get(
        "breakdown",
        []
    )

players.sort(

    key=lambda x:
        x.get(
            "draftScore",
            0
        ),

    reverse=True
)


for index, player in enumerate(players):

    player["customRank"] = index + 1

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

print(
    "Saved:",
    OUTPUT_FILE
)
