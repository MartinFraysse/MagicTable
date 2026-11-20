"""
Statistiques par commandant, calculées depuis les tournois archivés (format JSON brut).

Le classement final utilisé (victoires, podiums) est celui de core.ranking,
identique au reste de l'application.
"""

from __future__ import annotations

from core.ranking import final_ranking
from core.tournament import Tournament


def _is_duel(t: dict) -> bool:
    return "Duel" in t.get("format", "")


def rank_by_player_id(t: dict) -> dict[int, int]:
    """{player_id: rang final} — bracket (même partiel) prioritaire, sinon classement des rondes."""
    tournament = Tournament.from_dict(t)
    return {p.id: rank for rank, p in enumerate(final_ranking(tournament), 1)}


def _table_result(pid: int, tbl: dict) -> str:
    """Retourne 'W', 'L' ou 'D' pour un joueur dans une table terminée."""
    results = tbl.get("results", {})
    # Les clés peuvent être int ou str selon la sérialisation JSON
    my_pos = results.get(pid) or results.get(str(pid))
    player_ids = tbl.get("player_ids", [])

    if my_pos == 1:
        return "W"

    # Égalité en 1v1 : aucun joueur n'a la position 1 et les deux ont la même position
    if len(player_ids) == 2 and my_pos is not None:
        other_id = next((x for x in player_ids if x != pid), None)
        other_pos = results.get(other_id) or results.get(str(other_id)) if other_id is not None else None
        if other_pos is not None and other_pos == my_pos:
            return "D"

    return "L"


def stats_for_tournaments(commander_name: str, tournaments: list) -> dict | None:
    """Calcule les stats d'un commandant sur une liste de tournois. Retourne None si aucun."""
    tournois_joues = 0
    victoires = 0
    podiums = 0
    match_w = match_l = match_d = 0
    joueurs: dict[str, dict] = {}
    matchups: dict[str, dict] = {}
    derniere_date = ""

    for t in tournaments:
        players_with_cmd = [
            p for p in t.get("players", [])
            if p.get("commander", "") == commander_name
        ]
        if not players_with_cmd:
            continue

        tournois_joues += 1
        date = t.get("date", "")
        if date > derniere_date:
            derniere_date = date

        rank_by_id = rank_by_player_id(t)
        bracket_matches = (t.get("bracket") or {}).get("matches", [])
        pid_to_commander = {p["id"]: p.get("commander", "") for p in t.get("players", [])}

        for p in players_with_cmd:
            name = p.get("name", "?")
            pid = p.get("id")

            pw = pl = pd = 0
            for r in t.get("rounds", []):
                for tbl in r.get("tables", []):
                    if pid not in tbl.get("player_ids", []) or not tbl.get("finished"):
                        continue
                    res = _table_result(pid, tbl)
                    if res == "W":   pw += 1
                    elif res == "D": pd += 1
                    else:            pl += 1
                    for opp_id in tbl.get("player_ids", []):
                        if opp_id == pid:
                            continue
                        opp_cmd = pid_to_commander.get(opp_id, "")
                        if not opp_cmd:
                            continue
                        if opp_cmd not in matchups:
                            matchups[opp_cmd] = {"w": 0, "l": 0, "d": 0}
                        if res == "W":   matchups[opp_cmd]["w"] += 1
                        elif res == "D": matchups[opp_cmd]["d"] += 1
                        else:            matchups[opp_cmd]["l"] += 1

            for m in bracket_matches:
                if not m.get("finished") or pid not in (m.get("player1_id"), m.get("player2_id")):
                    continue
                if m.get("winner_id") == pid: pw += 1
                else:                          pl += 1
                opp_id = m.get("player2_id") if m.get("player1_id") == pid else m.get("player1_id")
                opp_cmd = pid_to_commander.get(opp_id, "")
                if opp_cmd:
                    if opp_cmd not in matchups:
                        matchups[opp_cmd] = {"w": 0, "l": 0, "d": 0}
                    if m.get("winner_id") == pid:
                        matchups[opp_cmd]["w"] += 1
                    else:
                        matchups[opp_cmd]["l"] += 1

            match_w += pw; match_l += pl; match_d += pd

            rank = rank_by_id.get(pid)
            won = rank == 1
            podium = rank is not None and rank <= 3
            if won:    victoires += 1
            if podium: podiums += 1

            if name not in joueurs:
                joueurs[name] = {"w": 0, "l": 0, "d": 0, "victoires": 0, "podiums": 0}
            joueurs[name]["w"] += pw
            joueurs[name]["l"] += pl
            joueurs[name]["d"] += pd
            if won:    joueurs[name]["victoires"] += 1
            if podium: joueurs[name]["podiums"] += 1

    if tournois_joues == 0:
        return None

    total_m = match_w + match_l + match_d
    taux = f"{match_w / total_m * 100:.0f} %" if total_m else "—"

    return {
        "tournois_joues": tournois_joues,
        "victoires": victoires,
        "podiums": podiums,
        "match_w": match_w,
        "match_l": match_l,
        "match_d": match_d,
        "taux_victoire": taux,
        "derniere_date": derniere_date or "—",
        "joueurs": dict(sorted(joueurs.items(), key=lambda x: -(x[1]["w"] + x[1]["l"] + x[1]["d"]))),
        "matchups": dict(sorted(matchups.items(), key=lambda x: -(x[1]["w"] + x[1]["l"] + x[1]["d"]))),
    }


def compute_commander_stats(commander_name: str, tournaments: list[dict]) -> dict:
    """Stats d'un commandant par format : {'multi': ..., 'duel': ...} (None si jamais joué)."""
    archived = [t for t in tournaments if t.get("archived", False)]
    return {
        "multi": stats_for_tournaments(commander_name, [t for t in archived if not _is_duel(t)]),
        "duel":  stats_for_tournaments(commander_name, [t for t in archived if _is_duel(t)]),
    }


def compute_global_stats(tournaments: list[dict], commanders_raw: list[dict]) -> dict:
    """
    Calcule les stats globales sur les tournois archivés.
    Retourne :
        {
            'wins':       [(name, count, img_path), ...],  # triés par nb victoires totales
            'wins_multi': [(name, count, img_path), ...],  # triés par nb victoires Multi
            'wins_duel':  [(name, count, img_path), ...],  # triés par nb victoires Duel
            'multi':      [(name, count, img_path), ...],  # triés par nb tournois Multi joués
            'duel':       [(name, count, img_path), ...],  # triés par nb tournois Duel joués
        }
    """
    tournaments = [t for t in tournaments if t.get("archived", False)]
    img_map: dict[str, str | None] = {c["name"]: c.get("image_path") for c in commanders_raw}

    wins:       dict[str, int] = {}
    wins_multi: dict[str, int] = {}
    wins_duel:  dict[str, int] = {}
    multi: dict[str, int] = {}
    duel:  dict[str, int] = {}

    for t in tournaments:
        is_duel = _is_duel(t)
        target = duel if is_duel else multi

        # Compte chaque commandant une seule fois par tournoi
        cmds_seen: set[str] = set()
        for p in t.get("players", []):
            cmd = p.get("commander", "")
            if cmd and cmd not in cmds_seen:
                cmds_seen.add(cmd)
                target[cmd] = target.get(cmd, 0) + 1

        # Victoires : rang 1 du classement final
        rank_by_id = rank_by_player_id(t)
        pid_to_cmd = {p["id"]: p.get("commander", "") for p in t.get("players", [])}
        wins_target = wins_duel if is_duel else wins_multi
        for pid, rank in rank_by_id.items():
            if rank == 1:
                cmd = pid_to_cmd.get(pid, "")
                if cmd:
                    wins[cmd]        = wins.get(cmd, 0) + 1
                    wins_target[cmd] = wins_target.get(cmd, 0) + 1

    def to_ranked(d: dict) -> list[tuple[str, int, str | None]]:
        return [
            (name, count, img_map.get(name))
            for name, count in sorted(d.items(), key=lambda x: -x[1])
        ]

    return {
        "wins":       to_ranked(wins),
        "wins_multi": to_ranked(wins_multi),
        "wins_duel":  to_ranked(wins_duel),
        "multi":      to_ranked(multi),
        "duel":       to_ranked(duel),
    }
