import os
import sys
import json
from pathlib import Path
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

# Accès aux modules MagicTable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from storage.leagues import LeagueStorage
from storage.tournaments import TournamentStorage
from core.league import League, compute_league_standings
from core.tournament import Tournament

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

COLOR = 0x3ad68a  # vert MagicTable

DATA_DIR = Path(__file__).parent / "data"
PENDING_FILE = DATA_DIR / "pending_starts.json"

TOURNAMENT_CATEGORY_NAME = "Tournoi en cours"
CHANNEL_RESULTATS = "resultats-rounds"
CHANNEL_CLASSEMENT = "classement"


# ── Helpers canaux tournoi ────────────────────────────────────────────────────

async def _cleanup_tournament_category(guild: discord.Guild) -> None:
    """Supprime la catégorie et ses canaux s'ils existent déjà."""
    cat = discord.utils.get(guild.categories, name=TOURNAMENT_CATEGORY_NAME)
    if cat:
        for ch in cat.channels:
            try:
                await ch.delete(reason="Nouveau tournoi")
            except discord.Forbidden:
                pass
        try:
            await cat.delete(reason="Nouveau tournoi")
        except discord.Forbidden:
            pass


async def _create_tournament_channels(guild: discord.Guild, tournament) -> None:
    """
    Crée la catégorie 'Tournoi en cours' avec :
    - #resultats-rounds  (lecture seule @everyone, écriture joueurs inscrits + bot)
    - #classement        (lecture seule @everyone, écriture bot uniquement)
    """
    await _cleanup_tournament_category(guild)

    # Récupérer les membres Discord des joueurs inscrits
    player_members = []
    for p in tournament.players:
        discord_id = getattr(p, "discord_id", None)
        if not discord_id:
            continue
        try:
            member = await guild.fetch_member(int(discord_id))
            player_members.append(member)
        except Exception:
            pass

    # Créer la catégorie
    try:
        category = await guild.create_category(TOURNAMENT_CATEGORY_NAME)
    except discord.Forbidden:
        print("[bot] Impossible de créer la catégorie : droits insuffisants")
        return

    # Permissions #resultats-rounds
    ow_resultats = {
        guild.default_role: discord.PermissionOverwrite(send_messages=False, read_messages=True),
        guild.me: discord.PermissionOverwrite(send_messages=True, read_messages=True),
    }
    for member in player_members:
        ow_resultats[member] = discord.PermissionOverwrite(send_messages=True, read_messages=True)

    # Permissions #classement
    ow_classement = {
        guild.default_role: discord.PermissionOverwrite(send_messages=False, read_messages=True),
        guild.me: discord.PermissionOverwrite(send_messages=True, read_messages=True),
    }

    try:
        await guild.create_text_channel(
            CHANNEL_RESULTATS,
            category=category,
            overwrites=ow_resultats,
            topic=f"Résultats des rounds — {tournament.name}",
        )
        await guild.create_text_channel(
            CHANNEL_CLASSEMENT,
            category=category,
            overwrites=ow_classement,
            topic=f"Classement en direct — {tournament.name}",
        )
    except discord.Forbidden as e:
        print(f"[bot] Erreur création canaux : {e}")
        return

    # Message d'annonce dans #resultats-rounds
    chan = discord.utils.get(category.channels, name=CHANNEL_RESULTATS)
    if chan:
        joueurs = ", ".join(p.name for p in tournament.players) or "—"
        embed = discord.Embed(
            title=f"🎲 Tournoi lancé : {tournament.name}",
            description=f"**Format :** {tournament.format}\n**Joueurs :** {joueurs}",
            color=COLOR,
        )
        embed.set_footer(text="Entrez vos résultats ici après chaque round.")
        try:
            await chan.send(embed=embed)
        except discord.Forbidden:
            pass

    print(f"[bot] Canaux tournoi créés pour « {tournament.name} »")


# ── Polling automatique démarrage tournoi ─────────────────────────────────────

@tasks.loop(seconds=10)
async def check_pending_starts():
    """Vérifie pending_starts.json toutes les 10 s et crée les canaux si besoin."""
    if not PENDING_FILE.exists():
        return

    try:
        pending = json.loads(PENDING_FILE.read_text(encoding="utf-8"))
    except Exception:
        return

    if not pending:
        return

    tournaments = [Tournament.from_dict(d) for d in TournamentStorage.load()]
    remaining = []

    for tid in pending:
        tournament = next((t for t in tournaments if t.id == tid), None)
        if tournament is None:
            print(f"[bot] pending_starts: tournoi {tid} introuvable, ignoré")
            continue

        handled = False
        for guild in bot.guilds:
            try:
                await _create_tournament_channels(guild, tournament)
                handled = True
            except Exception as e:
                print(f"[bot] Erreur création canaux ({guild.name}): {e}")

        if not handled:
            remaining.append(tid)

    # Réécrire la file (vide si tout traité)
    PENDING_FILE.write_text(json.dumps(remaining, indent=2), encoding="utf-8")


@bot.event
async def on_ready():
    print(f"✅ Bot connecté en tant que {bot.user}")
    check_pending_starts.start()


# ── !ping ─────────────────────────────────────────────────────────────────────

@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong ! 🏓 ({round(bot.latency * 1000)}ms)")


# ── !classement ───────────────────────────────────────────────────────────────

@bot.command()
async def classement(ctx, *, nom_ligue: str = None):
    """Affiche le classement d'une ligue. !classement [nom]"""
    leagues = [League.from_dict(d) for d in LeagueStorage.load()]
    tournaments = [Tournament.from_dict(d) for d in TournamentStorage.load()]

    if not leagues:
        await ctx.send("Aucune ligue créée pour l'instant.")
        return

    # Si pas de nom précisé, montre la liste des ligues disponibles
    if nom_ligue is None:
        embed = discord.Embed(title="🏅 Ligues disponibles", color=COLOR)
        for lg in leagues:
            embed.add_field(
                name=f"{lg.name}  •  {lg.season}",
                value=f"Format : {lg.format}\n`!classement {lg.name}`",
                inline=False
            )
        await ctx.send(embed=embed)
        return

    # Cherche la ligue par nom (insensible à la casse)
    league = next(
        (lg for lg in leagues if lg.name.lower() == nom_ligue.lower()), None
    )
    if league is None:
        await ctx.send(f"Ligue « {nom_ligue} » introuvable. Tape `!classement` pour voir la liste.")
        return

    entries = compute_league_standings(league, tournaments)
    if not entries:
        await ctx.send(f"Aucun résultat pour la ligue **{league.name}** pour l'instant.")
        return

    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    lines = []
    for e in entries:
        rank = medals.get(e.rank, f"`#{e.rank}`")
        lines.append(f"{rank} **{e.player_name}** — {e.total_points} pts ({e.tournaments_played} tournois)")

    embed = discord.Embed(
        title=f"🏅 {league.name}  •  {league.season}",
        description="\n".join(lines),
        color=COLOR
    )
    embed.set_footer(text=f"Format : {league.format}")
    await ctx.send(embed=embed)


# ── !resultats ────────────────────────────────────────────────────────────────

@bot.command()
async def resultats(ctx):
    """Affiche les résultats du dernier tournoi archivé."""
    tournaments = [Tournament.from_dict(d) for d in TournamentStorage.load()]
    archived = [t for t in tournaments if t.archived]

    if not archived:
        await ctx.send("Aucun tournoi archivé pour l'instant.")
        return

    # Dernier tournoi archivé par date
    last = sorted(archived, key=lambda t: t.date, reverse=True)[0]

    from core.league import get_tournament_final_ranking
    ranking = get_tournament_final_ranking(last)

    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    lines = []
    for i, name in enumerate(ranking, 1):
        rank = medals.get(i, f"`#{i}`")
        lines.append(f"{rank} {name}")

    embed = discord.Embed(
        title=f"🏆 {last.name}",
        description="\n".join(lines) if lines else "Aucun résultat.",
        color=COLOR
    )
    embed.set_footer(text=f"{last.format}  •  {last.date}  •  {len(last.players)} joueurs")
    await ctx.send(embed=embed)


# ── !joueur ───────────────────────────────────────────────────────────────────

@bot.command()
async def joueur(ctx, *, nom: str):
    """Affiche les stats d'un joueur dans toutes les ligues. !joueur <nom>"""
    leagues = [League.from_dict(d) for d in LeagueStorage.load()]
    tournaments = [Tournament.from_dict(d) for d in TournamentStorage.load()]

    from core.league import get_player_league_history

    embed = discord.Embed(title=f"👤 {nom}", color=COLOR)
    found = False

    for league in leagues:
        history = get_player_league_history(league, nom, tournaments)
        if not history:
            continue
        found = True
        total = sum(pts for _, _, pts in history)
        best = min(rank for _, rank, _ in history)
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        lines = [
            f"{medals.get(rank, f'#{rank}')} {t.name}  •  {t.date}  •  **{pts} pts**"
            for t, rank, pts in history
        ]
        embed.add_field(
            name=f"🏅 {league.name}  •  {league.season}  —  {total} pts",
            value="\n".join(lines),
            inline=False
        )

    if not found:
        await ctx.send(f"Joueur « {nom} » introuvable dans les ligues.")
        return

    await ctx.send(embed=embed)


bot.run(TOKEN)
