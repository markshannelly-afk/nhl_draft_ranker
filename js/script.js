/*
    Stores loaded player data, current draft year,
    available leagues, and comparison data.
*/

let allPlayers = [];

let currentYear = "2027"; //This is just the default for the dropdown. It is not overwriting any data.

let allowedLeagues = [];

let allComps = {};

let currentSort = "";
let sortAscending = true;

/*
    Determines player categories used throughout
    the application.
*/

function isGoalie(player) {
    return (player.position ?? []).includes("G");
}


/*
    Application Startup
    Loads required data before displaying rankings.
*/

loadLeagues().then(() => {

    loadPlayers(currentYear);
    loadComps(currentYear);

});


/*
 Loads JSON for the selected
    draft year.
*/

function loadComps(year) {

    return fetch(`../data/ranked_${year}.json?v=${Date.now()}`)
        .then(response => {

            if (!response.ok) {

                throw new Error(
                    `comps_${year}.json returned HTTP ${response.status}`
                );
            }

            return response.json();

        })

        .then(data => {

            allComps = data;
        })

        .catch(error => {
            console.error(
                "Comps loading failed:",
                error.message
            );

            allComps = {};
        });
}


/*
    Team Filtering
    Returns only teams belonging to leagues
    included in league_weights.json. If leagues are added to the json file, this will still find them....hopefully.
*/

function getDisplayTeams(player) {

    const teams =
        player.performanceStats?.teams ?? [];


    return teams
        .filter(
            t => allowedLeagues.includes(t.league)
        )
        .sort(
            (a, b) => {

                // newest season first
                const seasonCompare =
                    b.season.localeCompare(a.season);


                if (seasonCompare !== 0) {
                    return seasonCompare;
                }


                // If a player has stats from more than one league in the same season
                // prioritize strongest league
                const leagueA =
                    player.leagueBreakdown?.find(
                        x =>
                        x.team === a.team &&
                        x.league === a.league
                    )?.weight ?? 0;


                const leagueB =
                    player.leagueBreakdown?.find(
                        x =>
                        x.team === b.team &&
                        x.league === b.league
                    )?.weight ?? 0;


                return leagueB - leagueA;

            }
        );

}


function loadLeagues() {

    return fetch("../data/league_weights.json")

        .then(response => response.json())

        .then(data => {

            allowedLeagues = Object.keys(data);

        })

        .catch(error => {

            console.error(
                "League loading failed:",
                error
            );
        });
}


/*
    Calculates current player age from
    date of birth to today. This was weirdly a pain in the ass
*/

function calculateAge(dateOfBirth) {

    if (!dateOfBirth)

        return "";

    const birthDate = new Date(dateOfBirth);

    const today = new Date();


    const milliseconds =
        today - birthDate;

    const years =
        milliseconds /
        (1000 * 60 * 60 * 24 * 365.25);

    return years.toFixed(1);

}


/*
    Nationality Flags
    Converts country names into flag icons.
    I DID NOT KNOW YOU COULD DO THIS UNTIL I STARTED WORKING ON THIS. Same with the coloured emojis.
*/

function getFlag(country) {

    const flags = {

        "Canada": "ca",
        "USA": "us",
        "United States": "us",
        "Russia": "ru",
        "Sweden": "se",
        "Finland": "fi",
        "Czech Republic": "cz",
        "Czechia": "cz",
        "Slovakia": "sk",
        "Germany": "de",
        "Switzerland": "ch",
        "Latvia": "lv",
        "Denmark": "dk",
        "Norway": "no",
        "France": "fr",
        "Austria": "at",
        "Belarus": "by",
        "Kazakhstan": "kz",
        "Ukraine": "ua"

    };

    const code = flags[country];

    if (!code) {

        return "";

    }

    return `<span class="fi fi-${code}"></span>`;

}

/*
    Loads ranked player JSON and populates
    the table.
*/

function loadPlayers(year) {

    fetch(`../data/ranked_${year}.json`)

        .then(response => response.json())

        .then(players => {

            allPlayers = players;

            addPlayerBadges();

            redrawTable();

        })

        .catch(error => {

            console.error(
                "Player loading failed:",
                error
            );

        });

}

/*
    Reloads player rankings when the selected
    draft year changes.
*/

document
    .getElementById("draft-year")
    .addEventListener(
        "change",
        function () {

            currentYear = this.value;

            loadPlayers(currentYear);

        }
    );


/*
    Adds visual badges to notable prospects. At the moment, only flags top 10 players.
*/

function addPlayerBadges() {

    allPlayers.forEach(player => {

        player.badges = [];


        if (player.customRank <= 10) {

            player.badges.push(
                "&#128293; Top 10 Prospect"
            );

        }

    });

}


/*
    Detects player links and opens
    the selected player's profile card
*/

document.addEventListener(
    "click",
    function (event) {


        if (
            event.target.classList.contains(
                "player-link"
            )
        ) {


            event.preventDefault();


            const name =
                event.target.dataset.name;


            const player =
                allPlayers.find(
                    p => p.name === name
                );


            showPlayer(player);

        }

    }
);


/*
    Creates season history data for
    the player profile card.

    Filters duplicate teams and matches
    weighted scoring information from
    the ranker.
*/

function getLeagueScores(player) {

    return player.leagueBreakdown ?? [];

}


/*
    Builds the player's scouting card
*/

function showPlayer(player) {

    if (!player)
        return;


    const breakdown = player.scoreBreakdown ?? {};

    const isDefenseman =
        (player.position ?? []).includes("D");


    const leagueScores =
        getLeagueScores(player)
        .slice()
        .sort((a, b) => {

            return b.season.localeCompare(a.season);

        });



    document.getElementById(
        "profile-content"
    ).innerHTML = `


<div class="profile-header">


<div class="profile-bio">

<h2>
<a href="${player.url}" target="_blank">
${player.name}
</a>
</h2>


<h3>
Rank #${player.customRank}
</h3>


<div class="badges">

${
(player.badges ?? [])
.map(
b => `<span class="badge">${b}</span>`
)
.join("")
}

</div>


<p>
${getFlag(player.nationality)}
${player.nationality ?? ""}
|
${(player.position ?? []).join(", ")}
</p>


<p>
Born:
${player.dateOfBirth ?? ""}
|
Age:
${calculateAge(player.dateOfBirth)}
</p>


<p>
Height:
${player.height ?? "N/A"}
|
Weight:
${player.weight ?? "N/A"} lbs
</p>


<p>
<b>Size Profile:</b>
${breakdown.sizeProfile ?? "Average"}
</p>


</div>



<div class="profile-scouting">


<h3 class="section-title">
Draft Projection
</h3>


<div class="stars">
${renderStars(player.projection?.stars)}
</div>


<div class="score-header-card">

<div class="score-label">
Draft Score
</div>

<div class="score-number">
${Number(player.draftScore ?? 0).toFixed(2)}
</div>

</div>



<p>
<b>Player Type:</b>
${player.playerType ?? "Unknown"}
</p>


<p>
<b>Projected Role:</b>
${player.projection?.role ?? ""}
</p>


${
player.projection?.summary
?
`<p>${player.projection.summary}</p>`
:
""
}

</div>

</div>

<hr>

<div class="score-card">

<h3 class="section-title">
Draft Score Breakdown
</h3>
<p class="score-note">
Adjustments are applied as multipliers to the base production score.
</p>

<div class="score-row">
<span class="tooltip" data-tooltip="Weighted offensive production based on points, goals, and assists. Production is adjusted by league strength and uses diminishing returns so extreme totals do not dominate the ranking.">Production</span>
<span>${Number(breakdown.production ?? 0).toFixed(1)}</span>
</div>


<div class="score-row">
<span class="tooltip" data-tooltip="League strength multiplier. Players producing in stronger leagues receive more value because competition level is higher.">League Strength</span>
<span>

${
(player.leagueBreakdown ?? [])

.map(

l => `

<div class="league-weight-row">

    <span>
        ${l.league}
    </span>

    <span>
        x${Number(l.weight ?? 1).toFixed(2)}
    </span>

</div>

`

)

.join("")

}

</span>
</div>

<div class="score-row">
<span class="tooltip" data-tooltip="Age adjustment. Younger players receive a boost because producing at the same level against older competition is more significant. Overage players may receive a slight reduction.">Age</span>
<span>x${Number(breakdown.age ?? 1).toFixed(2)}</span>
</div>

<div class="score-row">
<span class="tooltip" data-tooltip="D and C have slightly higher value than wingers. Sorry, wingers.">Position</span>
<span>x${Number(breakdown.position ?? 1).toFixed(2)}</span>
</div>


<div class="score-row">
<span class="tooltip" data-tooltip="Position-specific production adjustment. High offensive output is weighted differently depending on position, such as scoring defensemen receiving additional value.">Position Production</span>
<span>x${Number(breakdown.positionProduction ?? 1).toFixed(2)}</span>
</div>


<div class="score-row">
<span class="tooltip" data-tooltip="Sample size reliability adjustment. Larger samples provide more confidence, while small samples are discounted due to increased uncertainty. For example, tournament scoring is scaled down due to the small sample size">Games Played Sample Size</span>
<span>x${Number(breakdown.sampleSize ?? 1).toFixed(2)}</span>
</div>


<div class="score-row">
<span class="tooltip" data-tooltip="Size adjustment based on height, weight, and offensive production. Larger players may receive a boost, while smaller players can offset size concerns through elite scoring.">Size Profile</span>
<span>x${Number(breakdown.size ?? 1).toFixed(2)}</span>
</div>


<div class="score-row">
<span class="tooltip" data-tooltip="Discipline adjustment based on penalty minutes per game. Players who take fewer penalties receive a positive adjustment.">Discipline</span>
<span>x${Number(breakdown.discipline ?? 1).toFixed(2)}</span>
</div>


<div class="score-row">
<span class="tooltip" data-tooltip="I know it's an imperfect stat, but it turns out junior leagues generally don't track Corsi.">Plus / Minus</span>
<span>x${Number(breakdown.plusMinus ?? 1).toFixed(2)}</span>
</div>


${
isDefenseman
?
`

<div class="score-row">
<span class="tooltip" data-tooltip="Additional adjustment due to the relative scarcity of high-end defense prospects.">Defense Rarity</span>
<span>
x${Number(breakdown.defenseRarity ?? 1).toFixed(2)}
</span>
</div>


<div class="score-row">
<span class="tooltip" data-tooltip="Additional boost for being a right-handed defenseman. Parents: teach your kids to play righty!">RHD Bonus</span>
<span>
x${Number(breakdown.rhd ?? 1).toFixed(2)}
</span>
</div>

`
:
""
}


</div>

<hr>

<h3 class="section-title">
Season History
</h3>

<div class="season-history">


${
leagueScores.map(t => `


<p>

<b>${t.season}</b>

<br>

${t.team}
(${t.league})

<br>

GP:
${t.gp}

|

G:
${t.goals ?? 0}

|

A:
${t.assists ?? 0}

|

PTS:
${t.points ?? 0}

|

PIM:
${t.pim ?? 0}


<br>


<b>
Draft Contribution:
${Number(t.weightedPoints ?? 0).toFixed(2)}
</b>


</p>


<hr>


`).join("")
}

</div>

`;

    //That was a big function...



    //Custom function to draw stars for draft ranking. CSS does the filling. There are unicodes for empty stars and full stars, but not half-filled.
    function renderStars(value) {

        const stars = Number(value) || 0;

        const full = Math.floor(stars);
        const half = stars % 1 >= 0.5;
        const empty = 5 - full - (half ? 1 : 0);

        return (
            '<span class="star filled">★</span>'.repeat(full) +
            (half ? '<span class="star half">★</span>' : '') +
            '<span class="star empty">☆</span>'.repeat(empty)
        );
    }


    //Forces the profile to display properly (like a fake popup, I suppose)
    document.getElementById(
        "profile"
    ).style.display = "block";
}

//Used when the player clicks on a header for sorting the table.
function redrawTable() {
    const table = document.getElementById("players");

    table.innerHTML = "";

    allPlayers
        .slice(0, 100)
        .forEach(player => {

            const stats = player.primaryStats ?? {};

            table.innerHTML += `

<tr>

<td>${player.customRank ?? ""}</td>

<td>
<a href="#" class="player-link" data-name="${player.name}">
${player.name}
</a>
</td>

<td>${(player.position ?? []).join(", ")}</td>

<td>${player.shoots ?? ""}</td>

<td>${player.height ?? ""}</td>

<td>${player.weight ?? ""}</td>

<td>${player.dateOfBirth ?? ""}</td>

<td>${getFlag(player.nationality)}</td>

<td>${stats.league ?? ""}</td>

<td>${getDisplayTeams(player)[0]?.team ?? ""}</td>

<td>${Math.round(stats.gp ?? 0)}</td>

<td>${isGoalie(player) ? "" : Math.round(stats.goals ?? 0)}</td>

<td>${isGoalie(player) ? "" : Math.round(stats.assists ?? 0)}</td>

<td>${isGoalie(player) ? "" : Math.round(stats.points ?? 0)}</td>

<td>${isGoalie(player) ? "" : Math.round(stats.plusMinus ?? 0)}</td>

<td>${Math.round(stats.pim ?? 0)}</td>

<td>${isGoalie(player) ? "" : Number(player.ppg ?? 0).toFixed(2)}</td>

<td>${isGoalie(player) ? (stats.goalsAgainstAverage ?? "NA") : ""}</td>

<td>${isGoalie(player) ? (stats.wins ?? 0) : ""}</td>

<td>${isGoalie(player) ? (stats.losses ?? 0) : ""}</td>

<td>${isGoalie(player) ? (stats.shutouts ?? 0) : ""}</td>

<td>${Number(player.draftScore ?? 0).toFixed(2)}</td>

</tr>

`;
        });
}



// Enables clicking column headers to sort rankings. You can sort by anything if you add it to the list. 

const sortColumns = [
    "rank", "name", "position", "shoots", "height", "weight",
    "dateOfBirth", "nationality", "league", "team", "gp",
    "goals", "assists", "points", "plusMinus", "pim",
    "ppg", "gaa", "wins", "losses", "shutouts", "draftScore"
];

document.querySelectorAll("#rankings-table th").forEach((header, index) => {

    header.style.cursor = "pointer";

    header.addEventListener("click", () => {
        sortPlayers(sortColumns[index]);
    });

});

function sortPlayers(key) {

    if (currentSort === key) {
        sortAscending = !sortAscending;
    } else {
        currentSort = key;
        sortAscending = true;
    }

    allPlayers.sort((a, b) => {

        let valueA;
        let valueB;

        const statsA = a.primaryStats ?? {};
        const statsB = b.primaryStats ?? {};

        switch (key) {

            case "rank":
                valueA = a.customRank ?? 9999;
                valueB = b.customRank ?? 9999;
                break;

            case "name":
            case "position":
            case "shoots":
            case "dob":
            case "height":
            case "weight":
            case "nationality":
                valueA = key === "position" ? (a.position ?? []).join(",") : (a[key] ?? "");
                valueB = key === "position" ? (b.position ?? []).join(",") : (b[key] ?? "");
                break;

            case "league":
                valueA = statsA.league ?? "";
                valueB = statsB.league ?? "";
                break;

            case "team":
                valueA = getDisplayTeams(a)[0]?.team ?? "";
                valueB = getDisplayTeams(b)[0]?.team ?? "";
                break;

            case "ppg":
            case "draftScore":
                valueA = Number(a[key] ?? 0);
                valueB = Number(b[key] ?? 0);
                break;

            case "gaa":
                valueA = Number(statsA.goalsAgainstAverage ?? 999);
                valueB = Number(statsB.goalsAgainstAverage ?? 999);
                break;

            default:
                valueA = Number(statsA[key] ?? 0);
                valueB = Number(statsB[key] ?? 0);
        }

        if (typeof valueA === "string") {
            return sortAscending ?
                valueA.localeCompare(valueB) :
                valueB.localeCompare(valueA);
        }

        return sortAscending ? valueA - valueB : valueB - valueA;
    });

    redrawTable();
}

// Close button
document
    .getElementById("close-profile")
    .addEventListener(
        "click",
        function () {

            document.getElementById(
                "profile"
            ).style.display = "none";

        }
    );

window.addEventListener("click", function (event) {

    const modal = document.getElementById("profile");

    if (event.target === modal) {

        modal.style.display = "none";

    }

});
