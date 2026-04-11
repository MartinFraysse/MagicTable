import os
import json
import urllib.request
import urllib.parse
import uuid
from pathlib import Path
from datetime import datetime
import re
import aiohttp
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

load_dotenv()
TOKEN   = os.getenv("DISCORD_TOKEN")
API_KEY = os.getenv("API_KEY", "")
API_URL = os.getenv("API_URL", "http://localhost:8000")

DATA_DIR     = Path(__file__).parent / "data"
PENDING_FILE              = DATA_DIR / "pending_starts.json"
PENDING_ROUND_STARTS_FILE = DATA_DIR / "pending_round_starts.json"
PENDING_NEXT_ROUNDS_FILE  = DATA_DIR / "pending_next_rounds.json"
PENDING_FINISHES_FILE     = DATA_DIR / "pending_finishes.json"

BRACKET_ROUND_LABELS = {
    "quart":       "Quarts de finale",
    "demi":        "Demi-finales",
    "final":       "Finale",
    "third_place": "Petite finale",
}

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

COLOR         = 0x3ad68a   # vert principal
COLOR_START   = 0x2ecc71   # vert vif — lancement tournoi
COLOR_CHRONO  = 0x5865f2   # blurple — chrono lancé
COLOR_RANK    = 0xf1c40f   # or — classement
COLOR_PAIRING = 0x9b59b6   # violet — pairings Swiss
COLOR_BRACKET = 0x1abc9c   # teal — bracket
COLOR_ELIM    = 0xe74c3c   # rouge — élimination
COLOR_FINISH  = 0xffd700   # or vif — fin de tournoi
TIMEOUT = 60


# ── Helpers ───────────────────────────────────────────────────────────────────

def save_json(filename: str, data: list) -> None:
    path = DATA_DIR / filename
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_json(filename: str) -> list:
    path = DATA_DIR / filename
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_via_api(resource: str, data: list) -> bool:
    filename_map = {
        "players":     "regular_players.json",
        "tournaments": "tournaments.json",
        "leagues":     "leagues.json",
        "commanders":  "commanders.json",
    }
    url = f"{API_URL.rstrip('/')}/{resource}"
    try:
        body = json.dumps(data, ensure_ascii=False).encode()
        req  = urllib.request.Request(url, data=body, method="PUT")
        req.add_header("Content-Type", "application/json")
        req.add_header("x-api-key", API_KEY)
        with urllib.request.urlopen(req, timeout=5):
            if resource in filename_map:
                path = DATA_DIR / filename_map[resource]
                path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            return True
    except Exception as e:
        print(f"Erreur API save {resource}: {e}")
        return False


def parse_date(date_str: str):
    try:
        return datetime.strptime(date_str, "%d/%m/%Y")
    except Exception:
        return None


def _match_discord(stored, lookup) -> bool:
    """Compare un discord_id stocké (str ou int) avec un id Discord (str ou int)."""
    return str(stored) == str(lookup)


def get_player_by_discord(discord_id) -> dict | None:
    """Retourne le premier joueur permanent lié à ce compte Discord, ou None."""
    return next(
        (p for p in load_json("regular_players.json") if p.get("discord_id") and _match_discord(p["discord_id"], discord_id)),
        None
    )

def unlink_all_discord(discord_id, all_players: list) -> list[str]:
    """Retire discord_id de TOUS les profils qui le portent. Retourne les pseudos déliés."""
    unlinked = []
    for p in all_players:
        if p.get("discord_id") and _match_discord(p["discord_id"], discord_id):
            p.pop("discord_id", None)
            unlinked.append(p.get("pseudo", "?"))
    return unlinked


async def send_error(ctx, message: str, delay: int = 15) -> None:
    """Envoie un message d'erreur visible seulement quelques secondes dans le canal."""
    try:
        await ctx.message.delete()
    except Exception:
        pass
    await ctx.send(f"{ctx.author.mention} {message}", delete_after=delay)


async def ask(ctx, question: str, channel=None) -> str | None:
    """Envoie une question et attend la réponse de l'auteur (60s).
    Si channel est précisé, envoie et écoute dans ce channel (ex: DM)."""
    dest = channel if channel is not None else ctx.channel
    if question:
        await dest.send(question)
    try:
        msg = await bot.wait_for(
            "message",
            timeout=TIMEOUT,
            check=lambda m: m.author == ctx.author and m.channel == dest
        )
        return msg.content.strip()
    except Exception:
        await dest.send("⏱️ Temps écoulé, opération annulée.")
        return None


# ── Events ────────────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    print(f"Bot connecté : {bot.user} (ID: {bot.user.id})")
    print("------")
    check_pending_starts.start()
    check_pending_quits.start()
    check_pending_round_starts.start()
    check_pending_next_rounds.start()
    check_pending_finishes.start()



# ── !ping ─────────────────────────────────────────────────────────────────────

@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong ! 🏓 Latence : {round(bot.latency * 1000)}ms")


# ── !hello ────────────────────────────────────────────────────────────────────

@bot.command()
async def hello(ctx):
    await ctx.send(f"Bonjour {ctx.author.mention} ! 👋 Je suis opérationnel.")


# ── !players ──────────────────────────────────────────────────────────────────

@bot.command()
async def players(ctx):
    """Affiche la liste des joueurs permanents MagicTable."""
    data = sorted(load_json("regular_players.json"), key=lambda p: p.get("points", 0), reverse=True)
    if not data:
        await ctx.send("Aucun joueur enregistré pour l'instant.")
        return
    medals  = {1: "🥇", 2: "🥈", 3: "🥉"}
    lines   = [
        f"{medals.get(i, f'`#{i}`')} **{p.get('pseudo','?')}** — {p.get('points',0)} pts "
        f"· {p.get('tournaments_played',0)} tournois · 🏆 {p.get('top_1',0)}"
        for i, p in enumerate(data, 1)
    ]
    embed = discord.Embed(title="👥 Joueurs MagicTable", description="\n".join(lines), color=COLOR)
    embed.set_footer(text=f"{len(data)} joueur{'s' if len(data)>1 else ''} enregistré{'s' if len(data)>1 else ''}")
    await ctx.send(embed=embed)


# ── !tournois ─────────────────────────────────────────────────────────────────

@bot.command()
async def tournois(ctx):
    """Affiche les tournois à venir."""
    upcoming = sorted(
        [t for t in load_json("tournaments.json") if not t.get("archived", False)],
        key=lambda t: parse_date(t.get("date","")) or datetime.max
    )
    if not upcoming:
        await ctx.send("Aucun tournoi prévu pour l'instant.")
        return
    embed = discord.Embed(title="🏆 Tournois à venir", color=COLOR)
    for t in upcoming:
        nb      = len(t.get("players", []))
        pairing = "Swiss" if t.get("pairing_system") == "swiss" else "Standard"
        embed.add_field(
            name  = f"{t.get('format','')}  —  {t.get('name','?')}",
            value = (
                f"📅 {t.get('date','?')}\n"
                f"👥 {nb} joueur{'s' if nb>1 else ''} inscrit{'s' if nb>1 else ''}\n"
                f"🔄 {t.get('max_rounds','?')} rounds · {pairing}"
            ),
            inline=False
        )
    embed.set_footer(text=f"{len(upcoming)} tournoi{'s' if len(upcoming)>1 else ''} à venir")
    await ctx.send(embed=embed)


# ── !inscrits ─────────────────────────────────────────────────────────────────

@bot.command()
async def inscrits(ctx, *, nom_tournoi: str = None):
    """Joueurs inscrits à un tournoi. Usage : !inscrits <nom>"""
    all_t    = load_json("tournaments.json")
    upcoming = [t for t in all_t if not t.get("archived", False)]

    if nom_tournoi is None:
        if not upcoming:
            await send_error(ctx, "Aucun tournoi disponible.")
            return
        noms = "\n".join(f"• **{t['name']}**" for t in upcoming)
        await send_error(ctx, f"Précise le nom du tournoi :\n{noms}\n\nExemple : `!inscrits {upcoming[0]['name']}`")
        return

    tournament = next((t for t in all_t if t.get("name","").lower() == nom_tournoi.lower()), None)
    if tournament is None:
        noms = ", ".join(f"**{t['name']}**" for t in upcoming) or "aucun"
        await send_error(ctx, f"Tournoi « {nom_tournoi} » introuvable.\nTournois disponibles : {noms}")
        return

    pl = [p for p in tournament.get("players",[]) if not p.get("dropped", False)]
    embed = discord.Embed(title=f"👥 Inscrits — {tournament['name']}", color=COLOR)
    embed.add_field(name="Format", value=tournament.get("format","?"), inline=True)
    embed.add_field(name="Date",   value=tournament.get("date","?"),   inline=True)
    embed.add_field(name="Rounds", value=str(tournament.get("max_rounds","?")), inline=True)
    if not pl:
        embed.description = "Aucun joueur inscrit pour l'instant."
    else:
        embed.add_field(
            name  = f"Joueurs ({len(pl)})",
            value = "\n".join(f"`{i}.` **{p.get('name','?')}**" for i, p in enumerate(pl, 1)),
            inline=False
        )
    await ctx.send(embed=embed)


# ── !register ─────────────────────────────────────────────────────────────────

@bot.command()
async def register(ctx):
    """Créer ou lier ton profil de joueur permanent MagicTable."""

    # Ouvrir le DM
    try:
        dm = await ctx.author.create_dm()
    except discord.Forbidden:
        await send_error(ctx, "❌ Je ne peux pas t'envoyer de message privé. Vérifie tes paramètres Discord.")
        return

    await ctx.send(f"📬 {ctx.author.mention} Je t'ai envoyé un message privé pour la suite !")

    async def ask_dm(question: str) -> str | None:
        """Envoie une question en DM et attend la réponse."""
        await dm.send(question)
        try:
            msg = await bot.wait_for(
                "message",
                timeout=TIMEOUT,
                check=lambda m: m.author == ctx.author and isinstance(m.channel, discord.DMChannel)
            )
            return msg.content.strip()
        except Exception:
            await dm.send("⏱️ Temps écoulé, inscription annulée.")
            return None

    all_players = load_json("regular_players.json")

    # ── Afficher les profils existants ────────────────────────────────────────
    if all_players:
        lines = [f"`{i}.` **{p.get('pseudo','?')}**" for i, p in enumerate(all_players, 1)]
        embed_list = discord.Embed(
            title="👥 Profils existants sur MagicTable",
            description="\n".join(lines),
            color=COLOR
        )
        embed_list.set_footer(text="Si ton pseudo est dans la liste, utilise-le à l'étape suivante pour lier ton Discord.")
        await dm.send(embed=embed_list)

    # ── Vérifier si déjà lié à un profil ─────────────────────────────────────
    current_profile = get_player_by_discord(ctx.author.id)
    if current_profile:
        confirm = await ask_dm(
            f"⚠️ Tu es déjà lié au profil **{current_profile['pseudo']}**.\n"
            f"Continuer te fera **perdre cette liaison**.\n\n"
            f"Tape `oui` pour changer de profil, ou `non` pour annuler."
        )
        if confirm is None:
            return
        if confirm.lower() != "oui":
            await dm.send(f"Opération annulée. Ton profil **{current_profile['pseudo']}** est conservé.")
            return
        unlink_all_discord(ctx.author.id, all_players)

    await dm.send(
        f"👋 Bienvenue ! Créons ton profil MagicTable.\n"
        f"*(Tu as {TIMEOUT}s pour répondre à chaque étape)*"
    )

    # ── Étape 1 : pseudo ──────────────────────────────────────────────────────
    pseudo = await ask_dm("**Étape 1/3** — Quel pseudo veux-tu utiliser ?")
    if pseudo is None:
        return

    taken = next((p for p in all_players if p.get("pseudo","").lower() == pseudo.lower()), None)

    if taken:
        linked_id = taken.get("discord_id")

        if linked_id and linked_id != ctx.author.id:
            await dm.send(
                f"❌ Le profil **{pseudo}** est déjà lié à un autre compte Discord.\n"
                f"Contacte un organisateur si c'est une erreur."
            )
            save_via_api("players", all_players)
            return

        if linked_id == ctx.author.id:
            await dm.send(f"✅ **{pseudo}** est déjà ton profil MagicTable !")
            save_via_api("players", all_players)
            return

        # Profil existant non lié → on lie
        taken["discord_id"] = str(ctx.author.id)
        save_via_api("players", all_players)
        embed = discord.Embed(
            title="🔗 Profil lié à ton Discord !",
            description=f"Le profil **{pseudo}** t'appartient maintenant.",
            color=COLOR
        )
        embed.add_field(name="Points",   value=str(taken.get("points",0)),             inline=True)
        embed.add_field(name="Tournois", value=str(taken.get("tournaments_played",0)), inline=True)
        await dm.send(embed=embed)
        return

    # ── Étape 2 : prénom nom ──────────────────────────────────────────────────
    full_name = await ask_dm("**Étape 2/3** — Prénom et nom ? (ex: Jean Dupont)")
    if full_name is None:
        return

    # ── Étape 3 : téléphone (optionnel) ───────────────────────────────────────
    phone_raw = await ask_dm("**Étape 3/3** — Numéro de téléphone ? *(tape `skip` pour passer)*")
    if phone_raw is None:
        return
    phone = "" if phone_raw.lower() == "skip" else phone_raw

    # ── Création du joueur ────────────────────────────────────────────────────
    new_id = max((p.get("id", 0) for p in all_players), default=0) + 1
    all_players.append({
        "id":                 new_id,
        "pseudo":             pseudo,
        "full_name":          full_name,
        "phone":              phone,
        "discord_id":         str(ctx.author.id),
        "top_1":              0,
        "top_2":              0,
        "top_3":              0,
        "points":             0,
        "tournaments_played": 0
    })

    if save_via_api("players", all_players):
        embed = discord.Embed(
            title="🎉 Profil créé avec succès !",
            description=f"Bienvenue dans MagicTable, **{pseudo}** !",
            color=COLOR
        )
        embed.add_field(name="Pseudo",    value=pseudo,       inline=True)
        embed.add_field(name="Nom",       value=full_name,    inline=True)
        embed.add_field(name="Téléphone", value=phone or "—", inline=True)
        embed.set_footer(text="Tu peux maintenant t'inscrire aux tournois avec !inscription")
        await dm.send(embed=embed)
    else:
        await dm.send("❌ Erreur lors de la création du profil, réessaie dans un instant.")


# ── Scryfall ──────────────────────────────────────────────────────────────────

async def _fetch_scryfall(name: str) -> dict | None:
    """Interroge l'API Scryfall (fuzzy) — même algo que l'application MagicTable."""
    encoded = urllib.parse.quote(name)
    url     = f"https://api.scryfall.com/cards/named?fuzzy={encoded}"
    headers = {"User-Agent": "MagicTable/1.0", "Accept": "application/json"}
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    return await resp.json()
    except Exception:
        pass
    return None


async def _download_image(url: str, dest: Path) -> bool:
    """Télécharge l'art_crop — même algo que l'application MagicTable."""
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(await resp.read())
                    return True
    except Exception:
        pass
    return False


async def _create_commander(ctx, all_commanders: list, is_duel: bool, channel=None) -> str:
    """Demande le nom, interroge Scryfall, crée le commandant et retourne son nom.
    Si channel est précisé, tous les messages sont envoyés dans ce channel (ex: DM)."""
    dest = channel if channel is not None else ctx.channel

    name = await ask(ctx,
        "✏️ Donne le **nom du commandant** (en anglais, approximatif accepté) :\n"
        "*(ex: Aragorn King Gondor — Scryfall corrigera l'orthographe)*",
        channel=channel
    )
    if not name:
        return ""

    # Déjà dans la liste ?
    exists = next((c for c in all_commanders if c.get("name","").lower() == name.lower()), None)
    if exists:
        await dest.send(f"👑 **{exists['name']}** existe déjà dans la liste !")
        return exists["name"]

    await dest.send(f"🔍 Recherche de **{name}** sur Scryfall...")

    card     = await _fetch_scryfall(name)
    colors   = []
    img_path = ""

    if card is None:
        await dest.send(
            f"⚠️ Introuvable sur Scryfall.\n"
            f"Commandant **{name}** ajouté sans image ni couleurs.\n"
            f"*(Complète-les depuis l'application)*"
        )
    else:
        # Nom exact depuis Scryfall (corrige coquilles / casse)
        name   = card.get("name", name)
        colors = card.get("color_identity", [])

        # Image art_crop — même logique que l'app (double-face : card_faces[0])
        image_uris = card.get("image_uris") or {}
        if not image_uris:
            faces      = card.get("card_faces", [])
            image_uris = faces[0].get("image_uris", {}) if faces else {}

        art_url = image_uris.get("art_crop", "")

        if art_url:
            filename = f"{uuid.uuid4().hex}.jpg"           # UUID comme l'app
            file_dest = DATA_DIR / "commander_images" / filename
            ok        = await _download_image(art_url, file_dest)
            if ok:
                img_path  = f"commander_images/{filename}"
                color_str = " ".join(colors) if colors else "incolore"
                await dest.send(f"🎨 Image récupérée · Couleurs : **{color_str}**")
            else:
                await dest.send("⚠️ Impossible de télécharger l'image. Commandant ajouté sans image.")
        else:
            color_str = " ".join(colors) if colors else "incolore"
            await dest.send(f"ℹ️ Pas d'image disponible · Couleurs : **{color_str}**")

    new_id = max((c.get("id", 0) for c in all_commanders), default=0) + 1
    all_commanders.append({
        "id":         new_id,
        "name":       name,
        "colors":     colors,
        "image_path": img_path,
        "duel":       is_duel
    })
    save_via_api("commanders", all_commanders)

    await dest.send(f"✅ **{name}** ajouté à MagicTable !")
    return name


# ── !inscription ──────────────────────────────────────────────────────────────

@bot.command()
async def inscription(ctx, *, nom_tournoi: str = None):
    """S'inscrire à un tournoi. Usage : !inscription [nom du tournoi]"""
    all_t    = load_json("tournaments.json")
    upcoming = [t for t in all_t if not t.get("archived", False)]

    if not upcoming:
        await send_error(ctx, "Aucun tournoi disponible. Tape `!tournois` pour vérifier.")
        return

    # dm sera ouvert seulement si nécessaire
    dm   = None
    dest = None   # None = canal public, sinon = DM

    async def open_dm():
        """Ouvre le DM une seule fois et annonce dans le canal."""
        nonlocal dm, dest
        if dm is not None:
            return True
        try:
            dm   = await ctx.author.create_dm()
            dest = dm
            await ctx.send(f"📬 {ctx.author.mention} Je t'ai envoyé un message privé pour la suite !")
            return True
        except discord.Forbidden:
            await send_error(ctx, "❌ Je ne peux pas t'envoyer de message privé. Vérifie tes paramètres Discord.")
            return False

    # ── Sélection du tournoi ──────────────────────────────────────────────────
    if nom_tournoi is None:
        # Besoin d'interaction → DM
        if not await open_dm():
            return

        lines = [
            f"`{i}.` {t.get('format','')} — **{t.get('name','?')}** · 📅 {t.get('date','?')}"
            for i, t in enumerate(upcoming, 1)
        ]
        embed = discord.Embed(title="🏆 Choisir un tournoi", description="\n".join(lines), color=COLOR)
        embed.set_footer(text="Entre le numéro du tournoi (tu as 60s)")
        await dm.send(embed=embed)

        rep = await ask(ctx, "", channel=dm)
        if rep is None:
            return
        try:
            idx = int(rep.strip()) - 1
            if not (0 <= idx < len(upcoming)):
                raise ValueError
            tournament = upcoming[idx]
        except ValueError:
            await dm.send("❌ Numéro invalide, inscription annulée.")
            return
    else:
        tournament = next((t for t in all_t if t.get("name","").lower() == nom_tournoi.lower()), None)
        if tournament is None:
            noms = ", ".join(f"**{t['name']}**" for t in upcoming) or "aucun"
            await send_error(ctx, f"Tournoi « {nom_tournoi} » introuvable.\nTournois disponibles : {noms}")
            return
        if tournament.get("archived", False):
            await send_error(ctx, f"Le tournoi **{tournament['name']}** est déjà terminé.")
            return

    # ── Profil joueur ─────────────────────────────────────────────────────────
    profile     = get_player_by_discord(ctx.author.id)
    player_name = profile["pseudo"] if profile else ctx.author.display_name

    if not profile:
        warn = (
            f"⚠️ Tu n'as pas encore de profil MagicTable.\n"
            f"Tape `!register` pour en créer un et suivre tes stats.\n\n"
            f"*(Inscription continue avec ton pseudo Discord : **{player_name}**)*"
        )
        await (dest or ctx).send(warn)

    # Déjà inscrit ?
    players_list = tournament.get("players", [])
    if any(p.get("name","").lower() == player_name.lower() for p in players_list):
        await (dest or ctx).send(f"{ctx.author.mention} Tu es déjà inscrit à **{tournament['name']}** ! ✅")
        return

    # ── Sélection du commandant si format Commander/Duel ─────────────────────
    fmt          = tournament.get("format", "")
    is_duel      = "⚔️" in fmt or "duel" in fmt.lower()
    is_commander = "👑" in fmt or is_duel
    chosen_commander = ""

    if is_commander:
        # Besoin d'interaction → DM
        if not await open_dm():
            return

        all_commanders = load_json("commanders.json")
        if is_duel and "👑" not in fmt:
            filtered = sorted([c for c in all_commanders if c.get("duel", False)], key=lambda c: c.get("name",""))
            title    = "⚔️ Commandants Duel Commander"
        else:
            filtered = sorted(all_commanders, key=lambda c: c.get("name",""))
            title    = "👑 Commandants Commander"

        COLORS_EMOJI = {"W":"⚪","U":"🔵","B":"⚫","R":"🔴","G":"🟢"}

        if not filtered:
            await dm.send("⚠️ Aucun commandant enregistré.")
            create = await ask(ctx, "Veux-tu ajouter ton commandant maintenant ? (`oui` / `non`)", channel=dm)
            if create and create.lower() == "oui":
                chosen_commander = await _create_commander(ctx, all_commanders, is_duel, channel=dm)
        else:
            lines = []
            for i, c in enumerate(filtered, 1):
                colors = "".join(COLORS_EMOJI.get(col,"") for col in c.get("colors",[]))
                lines.append(f"`{i:>2}.` {colors} {c.get('name','?')}")
            lines.append(f"`  0.` ➕ Mon commandant n'est pas dans la liste")

            chunks = [lines[j:j+20] for j in range(0, len(lines), 20)]
            for k, chunk in enumerate(chunks):
                embed = discord.Embed(
                    title       = title if k == 0 else "\u200b",
                    description = "\n".join(chunk),
                    color       = COLOR
                )
                if k == len(chunks) - 1:
                    embed.set_footer(text="Entre le numéro de ton commandant · 0 pour en ajouter un nouveau (tu as 60s)")
                await dm.send(embed=embed)

            rep = await ask(ctx, "", channel=dm)
            if rep is None:
                return

            if rep.strip() == "0":
                chosen_commander = await _create_commander(ctx, all_commanders, is_duel, channel=dm)
            else:
                try:
                    idx = int(rep.strip()) - 1
                    if not (0 <= idx < len(filtered)):
                        raise ValueError
                    chosen_commander = filtered[idx].get("name","")
                except ValueError:
                    await dm.send("❌ Numéro invalide, inscription annulée.")
                    return

    # ── Inscription ───────────────────────────────────────────────────────────
    new_id = max((p.get("id",-1) for p in players_list), default=-1) + 1
    players_list.append({
        "id": new_id, "name": player_name, "score": 0, "robustness": 0,
        "reward_claimed": False, "commander": chosen_commander,
        "buchholz": 0.0, "sos": 0.0, "had_bye": False, "dropped": False
    })
    tournament["players"] = players_list

    if save_via_api("tournaments", all_t):
        embed = discord.Embed(title="✅ Inscription confirmée !", color=COLOR)
        embed.add_field(name="Tournoi",          value=tournament["name"],         inline=True)
        embed.add_field(name="Format",           value=fmt,                        inline=True)
        embed.add_field(name="Date",             value=tournament.get("date","?"), inline=True)
        embed.add_field(name="Joueurs inscrits", value=str(len(players_list)),     inline=True)
        if chosen_commander:
            embed.add_field(name="Commandant", value=chosen_commander, inline=True)
        embed.set_footer(text=f"Inscrit sous le pseudo : {player_name}")

        if dest:
            # Toute la conversation était en DM → confirmation en DM
            await dest.send(embed=embed)
        else:
            # Inscription directe sans interaction → confirmation dans le canal
            await ctx.send(f"{ctx.author.mention}", embed=embed)
    else:
        await send_error(ctx, "❌ Erreur lors de l'inscription, réessaie dans un instant.")


# ── !ligue ────────────────────────────────────────────────────────────────────

def _tournament_ranking(t: dict) -> list[str]:
    """Retourne les noms des joueurs dans l'ordre du classement final."""
    players = [p for p in t.get("players", []) if not p.get("dropped", False)]
    if not players:
        return []

    is_commander = "commander" in t.get("format", "").lower() and t.get("pairing_system") == "standard"

    if is_commander:
        ranked = sorted(players, key=lambda p: (-p.get("score", 0), -p.get("robustness", 0), p.get("name", "")))
    else:
        ranked = sorted(players, key=lambda p: (
            -p.get("score", 0),
            -p.get("buchholz", 0),
            -p.get("sos", 0),
            p.get("name", "")
        ))
    return [p.get("name", "?") for p in ranked]


def _compute_league_standings(league: dict, tournaments: list[dict]) -> list[dict]:
    """Calcule le classement d'une ligue depuis les JSON bruts."""
    league_ids = set(league.get("tournament_ids", []))
    scoring    = {int(k): int(v) for k, v in league.get("scoring", {}).items()}
    part_pts   = league.get("participation_pts", 1)

    relevant = [t for t in tournaments if t.get("id") in league_ids and t.get("archived", False)]

    stats: dict[str, dict] = {}
    for t in relevant:
        ranking = _tournament_ranking(t)
        for rank, name in enumerate(ranking, 1):
            if name not in stats:
                stats[name] = {"points": 0, "played": 0, "best": rank}
            pts = scoring.get(rank, part_pts)
            stats[name]["points"] += pts
            stats[name]["played"] += 1
            stats[name]["best"]    = min(stats[name]["best"], rank)

    sorted_stats = sorted(
        stats.items(),
        key=lambda x: (-x[1]["points"], x[1]["best"], x[0])
    )
    return [
        {"rank": i + 1, "name": name, **s}
        for i, (name, s) in enumerate(sorted_stats)
    ]


@bot.command(name="ligue")
async def ligue_cmd(ctx, *, nom_ligue: str = None):
    """Affiche les ligues ou le classement d'une ligue. Usage : !ligue [nom]"""
    leagues     = load_json("leagues.json")
    tournaments = load_json("tournaments.json")

    if not leagues:
        await send_error(ctx, "Aucune ligue créée pour l'instant.")
        return

    # ── Sans argument : liste des ligues ─────────────────────────────────────
    if nom_ligue is None:
        embed = discord.Embed(title="🏅 Ligues en cours", color=COLOR)
        for lg in leagues:
            t_count   = len(lg.get("tournament_ids", []))
            part_pts  = lg.get("participation_pts", 1)
            top_scores = lg.get("scoring", {})
            best = next(iter(top_scores.values()), "?") if top_scores else "?"
            embed.add_field(
                name  = f"{lg.get('format', '')}  —  {lg.get('name', '?')}",
                value = (
                    f"📅 Saison {lg.get('season', '?')}\n"
                    f"🏆 {t_count} tournoi{'s' if t_count > 1 else ''}\n"
                    f"🥇 {best} pts max · participation : {part_pts} pt{'s' if part_pts > 1 else ''}\n"
                    f"`!ligue {lg.get('name', '')}` pour le classement"
                ),
                inline=False
            )
        await ctx.send(embed=embed)
        return

    # ── Avec argument : classement de la ligue ────────────────────────────────
    league = next((lg for lg in leagues if lg.get("name", "").lower() == nom_ligue.lower()), None)
    if league is None:
        noms = ", ".join(f"**{lg['name']}**" for lg in leagues)
        await send_error(ctx, f"Ligue « {nom_ligue} » introuvable.\nLigues disponibles : {noms}")
        return

    standings = _compute_league_standings(league, tournaments)

    if not standings:
        await send_error(ctx, f"Aucun résultat pour la ligue **{league['name']}** pour l'instant.")
        return

    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    lines  = []
    for e in standings:
        rank     = medals.get(e["rank"], f"`#{e['rank']}`")
        best_str = f"· meilleur : #{e['best']}" if e["best"] > 1 else "· 🏆 déjà 1er"
        lines.append(
            f"{rank} **{e['name']}** — {e['points']} pts "
            f"· {e['played']} tournoi{'s' if e['played'] > 1 else ''} {best_str}"
        )

    embed = discord.Embed(
        title       = f"🏅 {league.get('name')}  —  Saison {league.get('season', '?')}",
        description = "\n".join(lines),
        color       = COLOR
    )
    scoring = league.get("scoring", {})
    barème  = " · ".join(f"#{k}→{v}pts" for k, v in sorted(scoring.items(), key=lambda x: int(x[0])))
    embed.add_field(name="Format",  value=league.get("format", "?"), inline=True)
    embed.add_field(name="Barème",  value=barème or "—",             inline=False)
    embed.set_footer(text=f"{len(standings)} joueur{'s' if len(standings) > 1 else ''} au classement")
    await ctx.send(embed=embed)


# ── !stats ────────────────────────────────────────────────────────────────────

@bot.command(name="stats")
async def stats_cmd(ctx, *, pseudo: str = None):
    """Stats d'un joueur. Usage : !stats [pseudo]"""

    all_players  = load_json("regular_players.json")
    all_tournois = load_json("tournaments.json")
    all_leagues  = load_json("leagues.json")

    # ── Trouver le joueur ─────────────────────────────────────────────────────
    if pseudo is None:
        player = get_player_by_discord(ctx.author.id)
        if player is None:
            await send_error(
                ctx,
                "❌ Tu n'as pas de profil lié.\n"
                "Tape `!register` pour créer ou lier ton profil, "
                "ou utilise `!stats <pseudo>` pour voir les stats d'un joueur."
            )
            return
    else:
        player = next((p for p in all_players if p.get("pseudo","").lower() == pseudo.lower()), None)
        if player is None:
            noms = ", ".join(f"**{p['pseudo']}**" for p in all_players) or "aucun"
            await send_error(ctx, f"Joueur « {pseudo} » introuvable.\nJoueurs disponibles : {noms}")
            return

    name = player.get("pseudo", "?")

    # ── Stats de base ─────────────────────────────────────────────────────────
    pts          = player.get("points", 0)
    played       = player.get("tournaments_played", 0)
    top1         = player.get("top_1", 0)
    top2         = player.get("top_2", 0)
    top3         = player.get("top_3", 0)
    total_podium = top1 + top2 + top3

    # ── Historique tournois + commandants ─────────────────────────────────────
    multi_cmds: dict[str, int] = {}   # 👑 Commander
    duel_cmds:  dict[str, int] = {}   # ⚔️ Duel Commander
    tournament_history = []

    for t in all_tournois:
        fmt      = t.get("format", "")
        t_players = t.get("players", [])
        p_data   = next((p for p in t_players if p.get("name","").lower() == name.lower()), None)
        if p_data is None:
            continue

        cmd = p_data.get("commander", "").strip()
        if cmd:
            if "👑" in fmt:
                multi_cmds[cmd] = multi_cmds.get(cmd, 0) + 1
            elif "⚔️" in fmt or "duel" in fmt.lower():
                duel_cmds[cmd] = duel_cmds.get(cmd, 0) + 1

        ranking = _tournament_ranking(t)
        rank    = ranking.index(name) + 1 if name in ranking else None

        if t.get("archived", False) and rank is not None:
            tournament_history.append({
                "name":   t.get("name", "?"),
                "format": fmt,
                "date":   t.get("date", "?"),
                "rank":   rank,
            })

    tournament_history.sort(
        key=lambda x: parse_date(x["date"]) or datetime.min,
        reverse=True
    )

    # ── Ligues ────────────────────────────────────────────────────────────────
    league_lines = []
    for lg in all_leagues:
        standings = _compute_league_standings(lg, all_tournois)
        entry     = next((e for e in standings if e["name"].lower() == name.lower()), None)
        if entry:
            medals   = {1: "🥇", 2: "🥈", 3: "🥉"}
            rank_str = medals.get(entry["rank"], f"#{entry['rank']}")
            league_lines.append(
                f"{rank_str} **{lg.get('name')}** — {entry['points']} pts "
                f"· {entry['played']} tournoi{'s' if entry['played']>1 else ''}"
            )

    # ── Embed ─────────────────────────────────────────────────────────────────
    embed = discord.Embed(title=f"📊 Stats — {name}", color=COLOR)

    embed.add_field(name="🏆 Points globaux",  value=str(pts),          inline=True)
    embed.add_field(name="🎮 Tournois joués",  value=str(played),        inline=True)
    embed.add_field(name="🏅 Podiums",         value=str(total_podium),  inline=True)

    embed.add_field(name="🥇 Victoires",   value=str(top1), inline=True)
    embed.add_field(name="🥈 2ème place",  value=str(top2), inline=True)
    embed.add_field(name="🥉 3ème place",  value=str(top3), inline=True)

    # Commandants multi
    if multi_cmds:
        sorted_multi = sorted(multi_cmds.items(), key=lambda x: -x[1])
        top  = sorted_multi[0]
        lines = [f"**{top[0]}** ({top[1]} fois)"]
        for cmd, n in sorted_multi[1:4]:
            lines.append(f"• {cmd} ({n})")
        if len(sorted_multi) > 4:
            lines.append(f"*+ {len(sorted_multi)-4} autre{'s' if len(sorted_multi)-4>1 else ''}*")
        embed.add_field(name="👑 Commandants Multi", value="\n".join(lines), inline=True)

    # Commandants duel
    if duel_cmds:
        sorted_duel = sorted(duel_cmds.items(), key=lambda x: -x[1])
        top  = sorted_duel[0]
        lines = [f"**{top[0]}** ({top[1]} fois)"]
        for cmd, n in sorted_duel[1:4]:
            lines.append(f"• {cmd} ({n})")
        if len(sorted_duel) > 4:
            lines.append(f"*+ {len(sorted_duel)-4} autre{'s' if len(sorted_duel)-4>1 else ''}*")
        embed.add_field(name="⚔️ Commandants Duel", value="\n".join(lines), inline=True)

    # Ligues
    if league_lines:
        embed.add_field(name="🏅 Ligues", value="\n".join(league_lines), inline=False)

    # 5 derniers tournois
    if tournament_history:
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        lines  = []
        for t in tournament_history[:5]:
            rank_str = medals.get(t["rank"], f"#{t['rank']}")
            lines.append(f"{rank_str} {t['name']} — {t['format']} · {t['date']}")
        embed.add_field(
            name  = f"📜 Derniers tournois ({min(5,len(tournament_history))}/{len(tournament_history)})",
            value = "\n".join(lines),
            inline=False
        )

    full_name = player.get("full_name", "")
    linked    = "🔗 Lié Discord" if player.get("discord_id") else "—"
    embed.set_footer(text=f"{full_name}  ·  {linked}" if full_name else linked)

    await ctx.send(embed=embed)


# ── !help ─────────────────────────────────────────────────────────────────────

@bot.command(name="help")
async def help_cmd(ctx):
    """Affiche toutes les commandes disponibles."""
    embed = discord.Embed(
        title="📖 Commandes MagicTable",
        description="Voici toutes les commandes disponibles :",
        color=COLOR
    )

    embed.add_field(
        name="👤 Profil joueur",
        value=(
            "`!register` — Créer ou lier ton profil MagicTable\n"
            "*(La procédure se déroule en message privé)*"
        ),
        inline=False
    )

    embed.add_field(
        name="🏆 Tournois",
        value=(
            "`!tournois` — Liste des tournois à venir\n"
            "`!inscription <nom>` — S'inscrire (en MP si choix nécessaire)\n"
            "`!desinscrire <nom>` — Se désinscrire d'un tournoi\n"
            "`!inscrits <nom>` — Voir les joueurs inscrits à un tournoi"
        ),
        inline=False
    )

    embed.add_field(
        name="🏅 Ligues",
        value=(
            "`!ligue` — Liste des ligues en cours\n"
            "`!ligue <nom>` — Classement d'une ligue"
        ),
        inline=False
    )

    embed.add_field(
        name="👥 Joueurs",
        value=(
            "`!players` — Classement des joueurs permanents\n"
            "`!commandants` — Liste des commandants (filtrable par couleur)\n"
            "`!stats` — Tes stats personnelles\n"
            "`!stats <pseudo>` — Stats d'un joueur"
        ),
        inline=False
    )

    embed.add_field(
        name="📜 Tournois passés",
        value=(
            "`!result <nom>` — Résultats complets d'un tournoi archivé\n"
            "`!historique` — Liste de tous les tournois passés"
        ),
        inline=False
    )

    embed.add_field(
        name="🔔 Organisation",
        value=(
            "`!starttournoi <nom>` — Lance un tournoi et crée le channel dédié\n"
            "`!rappel <nom>` — Envoie un rappel en DM à tous les inscrits"
        ),
        inline=False
    )

    embed.add_field(
        name="🃏 Deckbuilding",
        value=(
            "`!commander <nom>` — Infos + image + liens EDHRec/Scryfall"
        ),
        inline=False
    )

    embed.add_field(
        name="🔧 Utilitaires",
        value=(
            "`!ping` — Tester la latence du bot\n"
            "`!help` — Afficher ce message"
        ),
        inline=False
    )

    embed.set_footer(text="MagicTable — Tournament Manager")
    await ctx.send(embed=embed)


# ── !desinscrire ──────────────────────────────────────────────────────────────

@bot.command()
async def desinscrire(ctx, *, nom_tournoi: str = None):
    """Se désinscrire d'un tournoi. Usage : !desinscrire <nom>"""
    all_t    = load_json("tournaments.json")
    upcoming = [t for t in all_t if not t.get("archived", False)]

    if nom_tournoi is None:
        if not upcoming:
            await ctx.send("Aucun tournoi disponible.")
            return
        noms = "\n".join(f"• **{t['name']}**" for t in upcoming)
        await ctx.send(f"Précise le nom du tournoi :\n{noms}\n\nExemple : `!desinscrire {upcoming[0]['name']}`")
        return

    tournament = next((t for t in all_t if t.get("name","").lower() == nom_tournoi.lower()), None)
    if tournament is None:
        noms = ", ".join(f"**{t['name']}**" for t in upcoming) or "aucun"
        await send_error(ctx, f"Tournoi « {nom_tournoi} » introuvable.\nTournois disponibles : {noms}")
        return
    if tournament.get("archived", False):
        await send_error(ctx, f"Le tournoi **{tournament['name']}** est déjà terminé.")
        return

    profile     = get_player_by_discord(ctx.author.id)
    player_name = profile["pseudo"] if profile else ctx.author.display_name

    players_list = tournament.get("players", [])
    player_entry = next(
        (p for p in players_list if p.get("name","").lower() == player_name.lower() and not p.get("dropped", False)),
        None
    )

    if player_entry is None:
        await send_error(ctx, f"❌ Tu n'es pas inscrit à **{tournament['name']}**.")
        return

    confirm = await ask(ctx,
        f"⚠️ {ctx.author.mention} Tu vas te désinscrire de **{tournament['name']}**.\n"
        f"Tape `oui` pour confirmer, ou `non` pour annuler."
    )
    if confirm is None:
        return
    if confirm.lower() != "oui":
        await send_error(ctx, "Désinscription annulée.")
        return

    player_entry["dropped"] = True
    tournament["players"] = players_list

    if save_via_api("tournaments", all_t):
        await ctx.send(f"✅ {ctx.author.mention} Tu es désinscrit de **{tournament['name']}**.")
    else:
        await send_error(ctx, "❌ Erreur lors de la désinscription, réessaie dans un instant.")


# ── !commandants ──────────────────────────────────────────────────────────────

def _parse_color_filter(filtre: str) -> list[str] | None:
    """Parse une chaîne couleur en liste de codes MTG.
    Accepte : "WU", "WUB", "blanc bleu", "blanc bleu noir", etc.
    Retourne None si un token est inconnu."""
    COLOR_NAMES = {
        "blanc": "W", "white": "W", "w": "W",
        "bleu":  "U", "blue":  "U", "u": "U",
        "noir":  "B", "black": "B", "b": "B",
        "rouge": "R", "red":   "R", "r": "R",
        "vert":  "G", "green": "G", "g": "G",
        "incolore": "C", "colorless": "C", "c": "C",
    }
    VALID_CODES = set("WUBRG")

    filtre = filtre.strip()

    if " " in filtre:
        # Mots séparés par espaces : "blanc bleu", "blanc bleu noir"
        codes = []
        for word in filtre.split():
            code = COLOR_NAMES.get(word.lower())
            if code is None:
                return None
            codes.append(code)
        return codes
    else:
        # Essayer d'abord comme mot unique : "blanc", "bleu"
        code = COLOR_NAMES.get(filtre.lower())
        if code:
            return [code]
        # Puis caractère par caractère : "WU", "WUB", "WUBRG"
        codes = []
        for ch in filtre.upper():
            if ch not in VALID_CODES:
                return None
            codes.append(ch)
        return codes


@bot.command(name="commandants")
async def commandants_cmd(ctx, *, filtre: str = None):
    """Liste des commandants. Usage : !commandants [couleur(s)]"""
    all_commanders = load_json("commanders.json")

    COLORS_EMOJI = {"W": "⚪", "U": "🔵", "B": "⚫", "R": "🔴", "G": "🟢"}

    # ── Filtre couleur ────────────────────────────────────────────────────────
    color_filters = None   # list[str] ou None
    if filtre:
        color_filters = _parse_color_filter(filtre)
        if color_filters is None:
            await ctx.send(
                f"❌ Filtre « {filtre} » non reconnu.\n"
                f"Exemples : `WU` · `blanc bleu` · `rouge` · `R` · `incolore`"
            )
            return

    # ── Séparer multi / duel ──────────────────────────────────────────────────
    multi = sorted([c for c in all_commanders if not c.get("duel", False)], key=lambda c: c.get("name",""))
    duel  = sorted([c for c in all_commanders if c.get("duel", False)],     key=lambda c: c.get("name",""))

    if color_filters:
        if color_filters == ["C"]:
            # Incolore : pas de couleurs du tout
            multi = [c for c in multi if not c.get("colors")]
            duel  = [c for c in duel  if not c.get("colors")]
        else:
            # Le commandant doit contenir TOUTES les couleurs demandées
            multi = [c for c in multi if all(col in c.get("colors", []) for col in color_filters)]
            duel  = [c for c in duel  if all(col in c.get("colors", []) for col in color_filters)]

    if not multi and not duel:
        suffix = f" en **{filtre}**" if filtre else ""
        await ctx.send(f"Aucun commandant enregistré{suffix}.")
        return

    def make_lines(cmds: list) -> list[str]:
        lines = []
        for c in cmds:
            colors_str = "".join(COLORS_EMOJI.get(col, "") for col in c.get("colors", []))
            if not colors_str:
                colors_str = "⬜"
            lines.append(f"{colors_str} **{c.get('name','?')}**")
        return lines

    suffix_title = f" — {filtre}" if filtre else ""

    async def send_section(title: str, cmds: list):
        lines  = make_lines(cmds)
        chunks = [lines[i:i+20] for i in range(0, len(lines), 20)]
        for k, chunk in enumerate(chunks):
            embed = discord.Embed(
                title       = title if k == 0 else "\u200b",
                description = "\n".join(chunk),
                color       = COLOR
            )
            if k == 0:
                embed.set_footer(text=f"{len(cmds)} commandant{'s' if len(cmds)>1 else ''}")
            await ctx.send(embed=embed)

    if multi:
        await send_section(f"👑 Commander{suffix_title}", multi)
    if duel:
        await send_section(f"⚔️ Duel Commander{suffix_title}", duel)


# ── !result ───────────────────────────────────────────────────────────────────

@bot.command(name="result")
async def result_cmd(ctx, *, nom_tournoi: str = None):
    """Résultats détaillés d'un tournoi archivé. Usage : !result <nom>"""
    all_t    = load_json("tournaments.json")
    archived = sorted(
        [t for t in all_t if t.get("archived", False)],
        key=lambda t: parse_date(t.get("date","")) or datetime.min
    )

    if nom_tournoi is None:
        if not archived:
            await send_error(ctx, "Aucun tournoi archivé pour l'instant.")
            return
        lines = [
            f"`{i}.` {t.get('format','')} — **{t.get('name','?')}** · 📅 {t.get('date','?')}"
            for i, t in enumerate(archived, 1)
        ]
        embed = discord.Embed(title="📜 Tournois archivés", description="\n".join(lines), color=COLOR)
        embed.set_footer(text="Usage : !result <nom du tournoi>")
        await ctx.send(embed=embed)
        return

    # Chercher TOUS les tournois avec ce nom (éditions multiples possible)
    matches = sorted(
        [t for t in archived if t.get("name","").lower() == nom_tournoi.lower()],
        key=lambda t: parse_date(t.get("date","")) or datetime.min
    )

    if not matches:
        noms = ", ".join(f"**{t['name']}**" for t in archived) or "aucun"
        await send_error(ctx, f"Tournoi « {nom_tournoi} » introuvable.\nTournois archivés : {noms}")
        return

    if len(matches) > 1:
        lines = [
            f"`{i}.` 📅 {t.get('date','?')} · "
            f"{len([p for p in t.get('players',[]) if not p.get('dropped',False)])} joueurs"
            for i, t in enumerate(matches, 1)
        ]
        embed = discord.Embed(
            title=f"📋 Plusieurs éditions de « {nom_tournoi} »",
            description="\n".join(lines),
            color=COLOR
        )
        embed.set_footer(text="Entre le numéro de l'édition (tu as 60s)")
        await ctx.send(embed=embed)

        rep = await ask(ctx, "")
        if rep is None:
            return
        try:
            idx = int(rep.strip()) - 1
            if not (0 <= idx < len(matches)):
                raise ValueError
            tournament = matches[idx]
        except ValueError:
            await send_error(ctx, "❌ Numéro invalide.")
            return
    else:
        tournament = matches[0]

    ranking = _tournament_ranking(tournament)
    if not ranking:
        await send_error(ctx, f"Aucun résultat disponible pour **{tournament['name']}**.")
        return

    players_map  = {p.get("name",""): p for p in tournament.get("players", [])}
    fmt          = tournament.get("format", "")
    is_commander = "👑" in fmt or "⚔️" in fmt or "duel" in fmt.lower()
    is_swiss     = tournament.get("pairing_system") == "swiss"
    medals       = {1: "🥇", 2: "🥈", 3: "🥉"}

    # ── Header ────────────────────────────────────────────────────────────────
    header = discord.Embed(title=f"🏆 Résultats — {tournament['name']}", color=COLOR)
    header.add_field(name="Format",  value=fmt,                        inline=True)
    header.add_field(name="Date",    value=tournament.get("date","?"), inline=True)
    header.add_field(name="Joueurs", value=str(len(ranking)),          inline=True)
    await ctx.send(embed=header)

    # ── Classement complet (paginé par 10) ────────────────────────────────────
    lines = []
    for rank, name in enumerate(ranking, 1):
        p      = players_map.get(name, {})
        prefix = medals.get(rank, f"`#{rank}`")

        if is_swiss:
            score   = p.get("score", 0)
            details = f"{score} pts"
        else:
            score      = p.get("score", 0)
            robustness = p.get("robustness", 0)
            details    = f"{score} pts · Robustesse {robustness}"

        cmd  = p.get("commander","")
        line = f"{prefix} **{name}** — {details}"
        if cmd and is_commander:
            line += f"\n　👑 {cmd}"
        lines.append(line)

    chunks = [lines[i:i+10] for i in range(0, len(lines), 10)]
    for k, chunk in enumerate(chunks):
        embed = discord.Embed(
            title       = f"📋 Classement ({k*10+1}–{k*10+len(chunk)})" if len(chunks) > 1 else "📋 Classement",
            description = "\n".join(chunk),
            color       = COLOR
        )
        await ctx.send(embed=embed)


# ── !historique ───────────────────────────────────────────────────────────────

MOIS_NOMS = {
    "janvier": 1,  "jan": 1,
    "février": 2,  "fevrier": 2, "fev": 2,
    "mars":    3,
    "avril":   4,  "avr": 4,
    "mai":     5,
    "juin":    6,
    "juillet": 7,  "juil": 7,
    "août":    8,  "aout": 8,
    "septembre": 9, "sep": 9, "sept": 9,
    "octobre":  10, "oct": 10,
    "novembre": 11, "nov": 11,
    "décembre": 12, "decembre": 12, "dec": 12,
}

def _parse_month_arg(arg: str) -> tuple[int, int] | None:
    """Parse un argument mois → (mois, annee) ou None si invalide.
    Accepte : 'mars', 'mars 2026', '03/2026', '3', '3 2026'.
    Si aucune année n'est précisée, utilise l'année courante — mais si le mois
    est encore dans le futur cette année, recule automatiquement d'un an."""
    arg   = arg.strip().lower()
    now   = datetime.now()

    # Format "03/2026" ou "3/2026"
    if "/" in arg:
        parts = arg.split("/")
        if len(parts) == 2:
            try:
                m, y = int(parts[0]), int(parts[1])
                if 1 <= m <= 12:
                    return (m, y)
            except ValueError:
                pass
        return None

    parts      = arg.split()
    month_part = parts[0]

    # Nom de mois français ou numéro
    m = MOIS_NOMS.get(month_part)
    if m is None:
        try:
            m = int(month_part)
            if not (1 <= m <= 12):
                return None
        except ValueError:
            return None

    # Année explicite fournie
    if len(parts) >= 2:
        try:
            y = int(parts[1])
        except ValueError:
            return None
        return (m, y)

    # Pas d'année : prendre l'année courante, mais reculer d'un an
    # si le mois est encore dans le futur (ex: juin demandé en avril → juin N-1)
    y = now.year
    if m > now.month:
        y -= 1

    return (m, y)


@bot.command(name="historique")
async def historique_cmd(ctx, *, filtre_mois: str = None):
    """Tournois passés. Usage : !historique [mois] [année]"""
    all_t    = load_json("tournaments.json")
    now      = datetime.now()
    archived = sorted(
        [t for t in all_t if t.get("archived", False)],
        key=lambda t: parse_date(t.get("date","")) or datetime.min,
        reverse=True
    )

    if not archived:
        await send_error(ctx, "Aucun tournoi archivé pour l'instant.")
        return

    # ── Appliquer le filtre ───────────────────────────────────────────────────
    if filtre_mois:
        parsed = _parse_month_arg(filtre_mois)
        if parsed is None:
            await send_error(
                ctx,
                f"❌ Mois « {filtre_mois} » non reconnu.\n"
                f"Exemples : `!historique mars` · `!historique mars 2026` · `!historique 03/2026`"
            )
            return
        m, y       = parsed
        filtered   = [t for t in archived if (d := parse_date(t.get("date",""))) and d.month == m and d.year == y]
        MOIS_FR    = {v: k.capitalize() for k, v in MOIS_NOMS.items() if len(k) > 4}
        titre_mois = f"{MOIS_FR.get(m, str(m))} {y}"
    else:
        # Par défaut : 2 derniers mois
        cutoff   = datetime(now.year, now.month, 1)
        # Reculer de 2 mois
        m2 = now.month - 2
        y2 = now.year
        if m2 <= 0:
            m2 += 12
            y2 -= 1
        cutoff   = datetime(y2, m2, 1)
        filtered = [t for t in archived if (d := parse_date(t.get("date",""))) and d >= cutoff]
        titre_mois = "2 derniers mois"

    if not filtered:
        if filtre_mois:
            await send_error(ctx, f"Aucun tournoi trouvé pour **{filtre_mois}**.")
        else:
            await send_error(ctx, "Aucun tournoi dans les 2 derniers mois.\nEssaie `!historique <mois>` pour chercher plus loin.")
        return

    # ── Construire les lignes ─────────────────────────────────────────────────
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    lines  = []
    for t in filtered:
        ranking     = _tournament_ranking(t)
        winner      = ranking[0] if ranking else "—"
        players_map = {p.get("name",""): p for p in t.get("players", [])}
        cmd         = players_map.get(winner, {}).get("commander","")
        cmd_str     = f" · 👑 {cmd}" if cmd else ""
        nb          = len([p for p in t.get("players",[]) if not p.get("dropped",False)])
        lines.append(
            f"**{t.get('name','?')}** · {t.get('format','')} · 📅 {t.get('date','?')}\n"
            f"  {medals[1]} {winner}{cmd_str} · {nb} joueurs"
        )

    chunks = [lines[i:i+10] for i in range(0, len(lines), 10)]
    for k, chunk in enumerate(chunks):
        title = f"📜 Historique — {titre_mois}" if k == 0 else "\u200b"
        embed = discord.Embed(title=title, description="\n\n".join(chunk), color=COLOR)
        if k == 0:
            embed.set_footer(text=f"{len(filtered)} tournoi{'s' if len(filtered)>1 else ''} · !historique <mois> pour filtrer")
        await ctx.send(embed=embed)


# ── !rappel ───────────────────────────────────────────────────────────────────


# ── !commander ────────────────────────────────────────────────────────────────

def _edhrec_slug(name: str) -> str:
    """Convertit un nom de carte en slug EDHRec (ex: Aragorn, the Uniter → aragorn-the-uniter)."""
    slug   = name.lower()
    result = []
    for ch in slug:
        if ch.isalnum():
            result.append(ch)
        elif ch in " -,'":
            result.append("-")
        # apostrophes et autres caractères ignorés
    slug = "".join(result)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


@bot.command(name="commander")
async def commander_cmd(ctx, *, nom: str = None):
    """Infos sur un commandant. Usage : !commander <nom>"""
    if nom is None:
        await send_error(ctx, "Usage : `!commander <nom>` — ex: `!commander Aragorn`")
        return

    COLORS_EMOJI = {"W":"⚪","U":"🔵","B":"⚫","R":"🔴","G":"🟢"}

    all_commanders = load_json("commanders.json")
    def _match_commander(c: dict, search: str) -> bool:
        """Retourne True si le commandant correspond à la recherche.
        Gère les cartes double-face (ex: 'Valki' matche 'Valki // Tibalt')."""
        c_name = c.get("name", "").lower().strip()
        s      = search.lower().strip()
        if c_name == s:
            return True
        # Double-face : comparer la première face uniquement
        if " // " in c_name and c_name.split(" // ")[0].strip() == s:
            return True
        return False

    nom_low = nom.lower().strip()

    # Chercher d'abord dans la base locale (match exact, DFC, ou sous-chaîne)
    db_matches = [
        c for c in all_commanders
        if _match_commander(c, nom)
        or nom_low in c.get("name","").lower()
    ]
    local = db_matches[0] if db_matches else None

    async with ctx.typing():
        card = await _fetch_scryfall(nom)
        # Si Scryfall échoue (nom ambigu) mais qu'on a un nom complet en base,
        # relancer avec ce nom précis pour récupérer l'image
        if card is None and db_matches:
            full_name = db_matches[0]["name"].split(" // ")[0].strip()
            if full_name.lower() != nom.lower():
                card = await _fetch_scryfall(full_name)

    # Ajouter les résultats Scryfall aux db_matches si le nom diffère
    if card:
        scryfall_name = card.get("name", nom)
        for c in all_commanders:
            if _match_commander(c, scryfall_name) and c not in db_matches:
                db_matches.append(c)

    if card is None and not db_matches:
        await send_error(ctx, f"❌ Commandant « {nom} » introuvable sur Scryfall et absent de la base locale.")
        return

    if card:
        name   = card.get("name", nom)
        colors = card.get("color_identity", [])

        image_uris = card.get("image_uris") or {}
        if not image_uris:
            faces      = card.get("card_faces", [])
            image_uris = faces[0].get("image_uris", {}) if faces else {}
        img_url = image_uris.get("art_crop","")

        edhrec_url   = f"https://edhrec.com/commanders/{_edhrec_slug(name)}"
        scryfall_url = card.get("scryfall_uri", "")
    else:
        # Scryfall introuvable mais présent en base locale
        name         = local.get("name", nom)
        colors       = local.get("colors", [])
        img_url      = ""
        edhrec_url   = f"https://edhrec.com/commanders/{_edhrec_slug(name)}"
        scryfall_url = ""

    # Image locale en fallback (servie par l'API)
    if not img_url and local and local.get("image_path"):
        img_url = f"{API_URL.rstrip('/')}/{local['image_path']}"

    colors_str = "".join(COLORS_EMOJI.get(c,"") for c in colors) or "⬜ Incolore"

    if db_matches:
        shown = db_matches[0]["name"]
        extra = f" *(+{len(db_matches)-1})*" if len(db_matches) > 1 else ""
        db_str = f"✅ **{shown}**{extra}"
    else:
        db_str = "❌ Pas encore ajouté"

    links = f"[EDHRec]({edhrec_url})"
    if scryfall_url:
        links += f"  ·  [Scryfall]({scryfall_url})"

    embed = discord.Embed(title=f"👑 {name}", color=COLOR)
    embed.add_field(name="Couleurs",    value=colors_str, inline=True)
    embed.add_field(name="MagicTable",  value=db_str,     inline=True)
    embed.add_field(name="Liens",       value=links,       inline=False)
    if img_url:
        embed.set_image(url=img_url)

    await ctx.send(embed=embed)


# ── !starttournoi ─────────────────────────────────────────────────────────────

TOURNAMENT_CATEGORY_NAME     = "🏆 TOURNOIS"
CHANNEL_RESULTATS_SUFFIX     = "résultats"
CHANNEL_CLASSEMENT_SUFFIX    = "classement"
TOURNAMENT_ROLE_NAMES        = ["Tournoi 1", "Tournoi 2", "Tournoi 3"]
MAX_SIMULTANEOUS_TOURNAMENTS = 3
SLOTS_FILE                   = DATA_DIR / "tournament_slots.json"


def _channel_slug(tournament_name: str) -> str:
    """Transforme un nom de tournoi en slug valide pour un canal Discord."""
    import re
    slug = tournament_name.lower().strip()
    slug = re.sub(r"[^\w\s\-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:85]

def _channel_names(tournament_name: str) -> tuple[str, str]:
    """Retourne (nom_résultats, nom_classement) pour un tournoi."""
    slug = _channel_slug(tournament_name)
    return f"{slug}-{CHANNEL_RESULTATS_SUFFIX}", f"{slug}-{CHANNEL_CLASSEMENT_SUFFIX}"

# ── Gestion des slots (max 3 tournois simultanés) ─────────────────────────────

def _load_slots() -> dict:
    """Charge le mapping tournament_id → {slot, slug}."""
    if SLOTS_FILE.exists():
        try:
            return json.loads(SLOTS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

def _save_slots(slots: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SLOTS_FILE.write_text(json.dumps(slots, indent=2, ensure_ascii=False), encoding="utf-8")

def _assign_slot(tournament_id: str, slug: str) -> "int | None":
    """Attribue un slot 1-3 au tournoi. Retourne None si tous occupés."""
    slots = _load_slots()
    if tournament_id in slots:
        return slots[tournament_id]["slot"]
    used = {v["slot"] for v in slots.values()}
    for slot in range(1, MAX_SIMULTANEOUS_TOURNAMENTS + 1):
        if slot not in used:
            slots[tournament_id] = {"slot": slot, "slug": slug}
            _save_slots(slots)
            return slot
    return None

def _release_slot(tournament_id: str) -> None:
    """Libère le slot du tournoi."""
    slots = _load_slots()
    if tournament_id in slots:
        del slots[tournament_id]
        _save_slots(slots)

def _get_slot_entry(tournament_id: str) -> "dict | None":
    """Retourne {slot, slug} pour ce tournoi, ou None."""
    return _load_slots().get(str(tournament_id))

def _resolve_unique_slug(guild, base_slug: str) -> str:
    """Retourne un slug unique dans la catégorie (ajoute '2', '3'... si conflit)."""
    cat = discord.utils.get(guild.categories, name=TOURNAMENT_CATEGORY_NAME)
    if not cat:
        return base_slug
    existing = {ch.name for ch in cat.text_channels}
    slug    = base_slug
    counter = 2
    while (f"{slug}-{CHANNEL_RESULTATS_SUFFIX}" in existing or
           f"{slug}-{CHANNEL_CLASSEMENT_SUFFIX}" in existing):
        slug    = f"{base_slug}{counter}"
        counter += 1
    return slug

def _find_channels(guild, tournament_name: str, tournament_id: str = None):
    """Trouve les deux canaux du tournoi dans la catégorie TOURNAMENT_CATEGORY_NAME."""
    cat = discord.utils.get(guild.categories, name=TOURNAMENT_CATEGORY_NAME)
    if not cat:
        return None, None
    if tournament_id:
        entry = _get_slot_entry(str(tournament_id))
        if entry:
            slug     = entry["slug"]
            name_res = f"{slug}-{CHANNEL_RESULTATS_SUFFIX}"
            name_cl  = f"{slug}-{CHANNEL_CLASSEMENT_SUFFIX}"
        else:
            name_res, name_cl = _channel_names(tournament_name)
    else:
        name_res, name_cl = _channel_names(tournament_name)
    ch_res = discord.utils.get(cat.text_channels, name=name_res)
    ch_cl  = discord.utils.get(cat.text_channels, name=name_cl)
    return ch_res, ch_cl

async def _remove_tournoi_role(guild, role_name: str) -> None:
    """Retire le rôle donné à tous les joueurs liés (via regular_players.json)."""
    role = discord.utils.get(guild.roles, name=role_name)
    if not role:
        return
    all_regular = load_json("regular_players.json")
    for p in all_regular:
        did = p.get("discord_id")
        if not did:
            continue
        try:
            member = await guild.fetch_member(int(did))
            if role in member.roles:
                await member.remove_roles(role, reason="Fin/reset tournoi")
        except Exception:
            pass


async def _cleanup_tournament_channels(
    guild,
    tournament_name: str = None,
    tournament_id: str = None,
) -> None:
    """Supprime les canaux du tournoi et retire le rôle associé, puis libère le slot."""
    # Récupérer le slot pour connaître le rôle et le slug exact
    entry     = _get_slot_entry(str(tournament_id)) if tournament_id else None
    role_name = TOURNAMENT_ROLE_NAMES[entry["slot"] - 1] if entry else None

    cat = discord.utils.get(guild.categories, name=TOURNAMENT_CATEGORY_NAME)
    if cat:
        if tournament_name or entry:
            # Supprimer uniquement les canaux de ce tournoi (via slug stocké ou nom)
            if entry:
                slug     = entry["slug"]
                name_res = f"{slug}-{CHANNEL_RESULTATS_SUFFIX}"
                name_cl  = f"{slug}-{CHANNEL_CLASSEMENT_SUFFIX}"
            else:
                name_res, name_cl = _channel_names(tournament_name)
            for ch in cat.text_channels:
                if ch.name in (name_res, name_cl):
                    try:
                        await ch.delete(reason="Tournoi terminé")
                    except Exception:
                        pass
        else:
            # Fallback : supprimer tous les canaux tournoi
            for ch in cat.text_channels:
                if ch.name.endswith(f"-{CHANNEL_RESULTATS_SUFFIX}") or ch.name.endswith(f"-{CHANNEL_CLASSEMENT_SUFFIX}"):
                    try:
                        await ch.delete(reason="Tournoi terminé")
                    except Exception:
                        pass

    if role_name:
        await _remove_tournoi_role(guild, role_name)
    if tournament_id:
        _release_slot(str(tournament_id))





# ── Helper bracket ──────────────────────────────────────────────────────────

def _record_bracket_result(bracket: dict, match_id: int, winner_id: int) -> None:
    """Enregistre le résultat d'un match de bracket et propage aux rounds suivants."""
    matches = bracket.get("matches", [])
    match   = next((m for m in matches if m.get("match_id") == match_id), None)
    if not match:
        return

    match["winner_id"] = winner_id
    match["finished"]  = True

    loser_id = (match.get("player2_id") if winner_id == match.get("player1_id")
                else match.get("player1_id"))

    # Propager le gagnant au match suivant
    next_mid = match.get("next_match_id")
    if next_mid is not None:
        next_m = next((m for m in matches if m.get("match_id") == next_mid), None)
        if next_m:
            if next_m.get("player1_id") is None:
                next_m["player1_id"] = winner_id
            else:
                next_m["player2_id"] = winner_id

    # Propager le perdant à la petite finale si applicable
    loser_mid = match.get("loser_next_match_id")
    if loser_mid is not None and loser_id is not None:
        loser_m = next((m for m in matches if m.get("match_id") == loser_mid), None)
        if loser_m:
            if loser_m.get("player1_id") is None:
                loser_m["player1_id"] = loser_id
            else:
                loser_m["player2_id"] = loser_id


# ── !score — Saisie résultat par le joueur (channel résultats uniquement) ─────

@bot.command(name="score")
async def score_cmd(ctx, *, resultat: str = None):
    """Enregistre ton résultat du round en cours. Usage : !score victoire | !score 1"""

    # Supprimer le message pour garder le channel propre
    try:
        await ctx.message.delete()
    except discord.Forbidden:
        pass

    async def err(msg: str):
        await ctx.send(f"{ctx.author.mention} {msg}", delete_after=15)

    # 1. Vérifier le bon channel
    if not ctx.channel.name.endswith(f"-{CHANNEL_RESULTATS_SUFFIX}"):
        await err(f"❌ `!score` fonctionne uniquement dans le canal résultats du tournoi.")
        return

    # 2. Trouver le tournoi actif dans cette catégorie
    all_t   = load_json("tournaments.json")
    actives = [t for t in all_t if not t.get("archived", False) and t.get("rounds")]
    if not actives:
        await err("❌ Aucun tournoi actif avec des rounds en cours.")
        return
    tournament = actives[-1]
    rounds     = tournament.get("rounds", [])
    cur_round  = rounds[-1]
    round_num  = cur_round.get("number", len(rounds))

    # 3. Identifier le joueur par Discord ID
    discord_id  = ctx.author.id
    all_regular = load_json("regular_players.json")
    regular     = next((p for p in all_regular if p.get("discord_id") and _match_discord(p["discord_id"], discord_id)), None)
    if not regular:
        await err("❌ Ton compte Discord n'est pas lié. Utilise `!register` d'abord.")
        return

    pseudo       = regular.get("pseudo", "").lower()
    t_players    = tournament.get("players", [])
    player       = next((p for p in t_players if p.get("name","").lower() == pseudo), None)
    if not player:
        await err(f"❌ Tu n'es pas inscrit au tournoi **{tournament.get('name','?')}**.")
        return

    player_id  = player["id"]
    player_name = player["name"]

    # 4. Trouver la table du joueur dans le round actuel
    tables = cur_round.get("tables", [])

    # Vérifier que le round a bien été démarré (chrono lancé)
    if cur_round.get("state", "preparation") == "preparation":
        await err(
            f"⏳ Le round {round_num} n'a pas encore démarré.\n"
            "Attends que le TO lance le chrono avant d'entrer ton résultat."
        )
        return

    table  = next((t for t in tables if player_id in t.get("player_ids", [])), None)
    if table is None:
        await err(f"❌ Tu n'as pas de table assignée au round {round_num}.")
        return

    table_num  = table.get("number", "?")
    player_ids = table.get("player_ids", [])
    results    = dict(table.get("results", {}))
    fmt          = tournament.get("format", "")
    is_commander = "👑" in fmt
    is_bracket   = bool(tournament.get("bracket")) and not tournament.get("bracket", {}).get("finished", False)

    # 4.5 Mode bracket : logique différente
    if is_bracket:
        bracket_data  = tournament.get("bracket", {})
        active_match  = next(
            (m for m in bracket_data.get("matches", [])
             if not m.get("finished")
             and m.get("player1_id") is not None
             and m.get("player2_id") is not None
             and player_id in (m.get("player1_id"), m.get("player2_id"))),
            None
        )

        if active_match is None:
            await err("❌ Tu n'as pas de match actif en phase finale.")
            return

        round_label   = BRACKET_ROUND_LABELS.get(active_match.get("round_name", ""), "match de bracket")
        started_round = bracket_data.get("started_round")
        if started_round != active_match.get("round_name"):
            await err(
                f"⏳ Le round **{round_label}** n'a pas encore démarré.\n"
                "Attends que le TO lance le chrono avant d'entrer ton résultat."
            )
            return

        if resultat is None:
            await err(
                f"Usage en phase finale : `!score victoire` ou `!score défaite`\n"
                f"Match en cours : **{round_label}**"
            )
            return

        res = resultat.strip().lower()

        # Rejeter le format X-Y
        if re.match(r'^\d+-\d+$', res):
            await err(
                "❌ Le format `X-Y` n'est **pas valide** en phase éliminatoire.\n"
                "Utilise : `!score victoire` ou `!score défaite`"
            )
            return

        if res in ("victoire", "v", "win", "w", "gagne", "gagné"):
            winner_id  = player_id
            label      = "🏆 Victoire"
        elif res in ("défaite", "defaite", "d", "loss", "l", "perdu"):
            winner_id  = (active_match.get("player2_id") if player_id == active_match.get("player1_id")
                         else active_match.get("player1_id"))
            label = "❌ Défaite"
        else:
            await err("❌ Résultat non reconnu. Utilise : `!score victoire` ou `!score défaite`")
            return

        opp_id   = (active_match.get("player2_id") if player_id == active_match.get("player1_id")
                    else active_match.get("player1_id"))
        opp_name = next((p["name"] for p in t_players if p["id"] == opp_id), "?")

        # Enregistrer le résultat
        _record_bracket_result(bracket_data, active_match.get("match_id"), winner_id)
        tournament["bracket"] = bracket_data

        if not save_via_api("tournaments", all_t):
            save_json("tournaments.json", all_t)

        confirm_msg = (
            f"✅ **{player_name}** — {label} en **{round_label}** "
            f"contre **{opp_name}** (Round {round_num})."
        )
        embed = discord.Embed(description=confirm_msg, color=0x2ecc71)
        await ctx.send(embed=embed, delete_after=30)
        return

    # 5. Afficher l'usage si pas d'argument
    if resultat is None:
        if is_commander:
            names = [next((p["name"] for p in t_players if p["id"] == pid), "?") for pid in player_ids]
            ex1 = names[0] if names else "Alice"
            ex2 = names[1] if len(names) > 1 else "Bob"
            await err(f"Usage : `!score <1er> <2ème>` — ex: `!score {ex1} {ex2}`")
        else:
            await err("Usage : `!score <wins>-<losses>` — ex: `!score 2-1` ou `!score 0-2`")
        return

    res = resultat.strip()

    # 6. Traitement selon le format
    if is_commander:
        # Résoudre un argument (mention ou nom) vers un player_id de la table
        def resolve(arg: str) -> int | None:
            arg = arg.strip()
            # Mention Discord → chercher via discord_id
            m = re.match(r'<@!?(\d+)>', arg)
            if m:
                did = m.group(1)
                all_reg = load_json("regular_players.json")
                pseudo  = next((p.get("pseudo","") for p in all_reg if _match_discord(p.get("discord_id",""), did)), None)
                if pseudo:
                    return next((p["id"] for p in t_players if p.get("name","").lower() == pseudo.lower()), None)
                return None
            # Nom partiel (insensible à la casse)
            arg_low = arg.lower()
            matches = [pid for pid in player_ids
                       if arg_low in next((p["name"] for p in t_players if p["id"] == pid), "").lower()]
            return matches[0] if len(matches) == 1 else None

        # Découper en deux arguments (gère les noms composés si besoin)
        parts = res.split()
        if len(parts) < 2:
            names = [next((p["name"] for p in t_players if p["id"] == pid), "?") for pid in player_ids]
            await err(f"❌ Précise le 1er **et** le 2ème — ex: `!score {names[0]} {names[1] if len(names) > 1 else '...'}`")
            return

        # Essayer d'abord chaque moitié comme un seul token, puis combiner si besoin
        winner_id = second_id = None
        for split_at in range(1, len(parts)):
            a1 = " ".join(parts[:split_at])
            a2 = " ".join(parts[split_at:])
            r1 = resolve(a1)
            r2 = resolve(a2)
            if r1 is not None and r2 is not None and r1 != r2:
                winner_id, second_id = r1, r2
                break

        if winner_id is None or second_id is None:
            names = [next((p["name"] for p in t_players if p["id"] == pid), "?") for pid in player_ids]
            await err(
                f"❌ Joueur(s) introuvable(s) à ta table.\n"
                f"Joueurs de la table : " + ", ".join(f"**{n}**" for n in names)
            )
            return

        if winner_id == second_id:
            await err("❌ Le 1er et le 2ème ne peuvent pas être la même personne.")
            return

        # Remplir les positions : 1er, 2ème, et le reste à la dernière place
        results[winner_id] = 1
        results[second_id] = 2
        last_pos = len(player_ids)
        for pid in player_ids:
            if pid not in (winner_id, second_id):
                results[pid] = last_pos

        table["results"]  = results
        table["finished"] = True

        winner_name = next((p["name"] for p in t_players if p["id"] == winner_id), "?")
        second_name = next((p["name"] for p in t_players if p["id"] == second_id), "?")
        others      = [next((p["name"] for p in t_players if p["id"] == pid), "?")
                       for pid in player_ids if pid not in (winner_id, second_id)]
        others_str  = " · ".join(f"**{n}**" for n in others) if others else ""

        confirm_msg = (
            f"✅ Table {table_num} — Round {round_num} enregistrée !\n"
            f"🥇 **{winner_name}** · 🥈 **{second_name}**"
            + (f" · {others_str} (dernière place)" if others_str else "")
        )

    else:
        # 1v1 — format X-Y (ex: 2-1, 0-2, 1-1)
        score_match = re.match(r'^(\d+)-(\d+)$', res)
        if not score_match:
            await err(
                "❌ Format invalide.\n"
                "Utilise : `!score <wins>-<losses>` — ex: `!score 2-1` ou `!score 0-2`\n"
                "Scores valides : `2-0`, `2-1`, `1-1`, `0-2`, `1-2`"
            )
            return

        wins   = int(score_match.group(1))
        losses = int(score_match.group(2))

        if wins > 2:
            await err("❌ Tu ne peux pas avoir plus de **2 games** gagnées.")
            return
        if losses > 2:
            await err("❌ Ton adversaire ne peut pas avoir plus de **2 games** gagnées.")
            return
        if wins + losses > 3:
            await err(f"❌ Total de games ({wins + losses}) trop élevé — maximum 3.")
            return

        if wins > losses:
            my_pos, opp_pos = 1, 2
            label = f"🏆 Victoire ({wins}-{losses})"
        elif wins < losses:
            my_pos, opp_pos = 2, 1
            label = f"❌ Défaite ({wins}-{losses})"
        else:
            my_pos, opp_pos = 1, 1
            label = f"🤝 Nul ({wins}-{losses})"

        opp_ids = [pid for pid in player_ids if pid != player_id]

        # Vérifier conflit : si l'adversaire a déjà déclaré une victoire aussi
        for opp_id in opp_ids:
            opp_pos_existing = results.get(opp_id)
            if opp_pos_existing is not None:
                if my_pos == 1 and opp_pos == 2 and opp_pos_existing == 1:
                    opp_name = next((p["name"] for p in t_players if p["id"] == opp_id), "?")
                    await err(
                        f"⚠️ Conflit : **{opp_name}** a aussi déclaré une victoire. "
                        "Contactez un TO pour trancher."
                    )
                    return

        results[player_id] = my_pos
        if len(opp_ids) == 1:
            results[opp_ids[0]] = opp_pos

        # Stocker les game scores (pour BO3)
        game_scores = dict(table.get("game_scores", {}))
        game_scores[player_id] = wins
        if len(opp_ids) == 1:
            game_scores[opp_ids[0]] = losses
        table["game_scores"] = game_scores

        table["results"]  = results
        table["finished"] = True

        confirm_msg = f"✅ **{player_name}** — {label} enregistrée (Table {table_num}, Round {round_num})."

    # 7. Sauvegarder (local + serveur API pour sync temps réel avec l'app)
    if not save_via_api("tournaments", all_t):
        save_json("tournaments.json", all_t)

    # 8. Confirmer dans le channel
    embed = discord.Embed(description=confirm_msg, color=0x2ecc71)
    await ctx.send(embed=embed, delete_after=30)

    # La table est terminée — la confirmation dans #resultats-rounds suffit



# ── Création canaux auto (appelé par polling et par !starttournoi) ─────────────


def _build_pairings_embed(tournament: dict, round_num: int | None = None) -> "discord.Embed | None":
    """Construit un embed Discord avec les pairings du dernier round."""
    rounds = tournament.get("rounds", [])
    if not rounds:
        return None

    last_round = rounds[-1]
    rnum   = round_num if round_num is not None else last_round.get("number", 1)
    tables = last_round.get("tables", [])
    if not tables:
        return None

    players_by_id = {p["id"]: p for p in tournament.get("players", [])}
    fmt           = tournament.get("format", "")
    is_commander  = "👑" in fmt
    t_name        = tournament.get("name", "")
    max_rounds    = tournament.get("max_rounds", "?")

    lines = []
    for table in sorted(tables, key=lambda t: t.get("number", 0)):
        tnum       = table.get("number", "?")
        player_ids = table.get("player_ids", [])

        if len(player_ids) == 1:
            p = players_by_id.get(player_ids[0], {})
            lines.append(f"> 🪑  **Table {tnum}** — **{p.get('name','?')}** *(bye)*")
        elif is_commander:
            names = [f"**{players_by_id.get(pid, {}).get('name','?')}**" for pid in player_ids]
            lines.append(f"> 🪑  **Table {tnum}** — " + "  ·  ".join(names))
        else:
            if len(player_ids) >= 2:
                p1 = players_by_id.get(player_ids[0], {})
                p2 = players_by_id.get(player_ids[1], {})
                n1 = f"**{p1.get('name','?')}**"
                n2 = f"**{p2.get('name','?')}**"
                lines.append(f"> ⚔️  **Table {tnum}** — {n1}  vs  {n2}")

    if not lines:
        return None

    embed = discord.Embed(
        title       = f"⚔️  Round {rnum} / {max_rounds} — Pairings",
        description = "\n".join(lines),
        color       = COLOR_PAIRING,
    )
    embed.set_footer(text=f"{t_name}  ·  Entrez votre résultat dans #resultats-rounds avec !score")
    return embed


async def _create_tournament_channels_auto(guild: discord.Guild, tournament: dict) -> bool:
    """Crée les canaux du tournoi dans la catégorie existante '🏆 TOURNOIS'."""
    t_name  = tournament.get("name", "?")
    t_id    = str(tournament.get("id", ""))
    fmt     = tournament.get("format", "?")
    players = [p for p in tournament.get("players", []) if not p.get("dropped", False)]

    # Trouver la catégorie existante en premier
    category = discord.utils.get(guild.categories, name=TOURNAMENT_CATEGORY_NAME)
    if not category:
        print(f"[auto-tournoi] Catégorie '{TOURNAMENT_CATEGORY_NAME}' introuvable sur le serveur")
        return False

    # Vérifier la capacité (max 3 tournois simultanés)
    slots = _load_slots()
    existing_entry = slots.get(t_id)
    if not existing_entry and len(slots) >= MAX_SIMULTANEOUS_TOURNAMENTS:
        print(f"[auto-tournoi] Capacité max ({MAX_SIMULTANEOUS_TOURNAMENTS} tournois) atteinte — {t_name} ignoré")
        return False

    # Nettoyer d'éventuels anciens canaux du même tournoi (retry)
    if existing_entry:
        await _cleanup_tournament_channels(guild, t_name, t_id)

    # Résoudre un slug unique (ajoute "2" si conflit de nom)
    base_slug = _channel_slug(t_name)
    slug      = _resolve_unique_slug(guild, base_slug)
    name_res  = f"{slug}-{CHANNEL_RESULTATS_SUFFIX}"
    name_cl   = f"{slug}-{CHANNEL_CLASSEMENT_SUFFIX}"

    # Assigner un slot et un rôle
    slot = _assign_slot(t_id, slug)
    if slot is None:
        print(f"[auto-tournoi] Plus de slot disponible pour {t_name}")
        return False
    role_name    = TOURNAMENT_ROLE_NAMES[slot - 1]
    tournoi_role = discord.utils.get(guild.roles, name=role_name)

    # Résoudre les membres Discord
    all_regular = load_json("regular_players.json")
    discord_map = {p.get("pseudo","").lower(): p.get("discord_id") for p in all_regular if p.get("discord_id")}

    player_members = []
    mentions       = []
    no_account     = []
    for p in players:
        pname      = p.get("name", "")
        discord_id = discord_map.get(pname.lower())
        if discord_id:
            mentions.append(f"<@{discord_id}>")
            try:
                member = await guild.fetch_member(int(discord_id))
                player_members.append(member)
            except Exception:
                pass
        else:
            no_account.append(f"**{pname}**")

    # Attribuer le rôle Tournoi X aux joueurs liés
    if tournoi_role:
        # Nettoyer d'abord : retirer le rôle à TOUS ceux qui l'ont déjà
        # (rôle résiduel d'un tournoi précédent mal clôturé)
        player_member_ids = {m.id for m in player_members}
        for holder in list(tournoi_role.members):
            if holder.id not in player_member_ids:
                try:
                    await holder.remove_roles(tournoi_role, reason="Nettoyage rôle tournoi")
                except Exception:
                    pass

        # Puis attribuer uniquement aux joueurs inscrits à CE tournoi
        for member in player_members:
            try:
                await member.add_roles(tournoi_role, reason="Tournoi démarré")
            except discord.Forbidden:
                print(f"[auto-tournoi] Permission refusée rôle → {member.display_name}")
            except Exception as e:
                print(f"[auto-tournoi] Erreur rôle {member.display_name}: {e}")
    else:
        print(f"[auto-tournoi] Rôle '{role_name}' introuvable")

    # Créer les canaux dans la catégorie existante
    try:
        ow_resultats = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me:           discord.PermissionOverwrite(send_messages=True, read_messages=True),
        }
        if tournoi_role:
            ow_resultats[tournoi_role] = discord.PermissionOverwrite(send_messages=True, read_messages=True)

        ch_resultats = await guild.create_text_channel(
            name       = name_res,
            category   = category,
            overwrites = ow_resultats,
            topic      = f"Résultats de rounds — {t_name} · réservé aux joueurs inscrits",
        )

        _is_cmd_fmt = "👑" in fmt
        if _is_cmd_fmt:
            _score_body = (
                "Un seul joueur de la table entre le résultat pour tout le monde.\n\n"
                "**Format :** `!score <1er> <2ème>`\n\n"
                "**Exemples :**\n"
                "`!score Martin Léo` — Martin 1er, Léo 2ème, les autres à la dernière place\n"
                "`!score @Martin @Léo` — fonctionne aussi avec les mentions Discord\n\n"
                "*(les noms doivent correspondre aux joueurs de ta table)*"
            )
        else:
            _score_body = (
                "Utilise `!score` pour enregistrer le résultat de ton match.\n\n"
                "**Format :** `!score <games_gagnées>-<games_perdues>`\n\n"
                "**Exemples valides :**\n"
                "`!score 2-0` · `!score 2-1` · `!score 1-1` · `!score 0-2` · `!score 1-2`\n\n"
                "**Règles :**\n"
                "• Maximum **2 games** gagnées par joueur · Total ≤ **3**\n"
                "• Entre ton propre résultat — l'adversaire n'a pas besoin de le rentrer"
            )
        _expl_embed = discord.Embed(
            title       = "📝 Comment entrer ton résultat",
            description = _score_body,
            color       = COLOR,
        )
        _expl_embed.set_footer(text="Commande réservée aux joueurs inscrits · canal protégé en écriture")
        _expl_msg = await ch_resultats.send(embed=_expl_embed)
        try:
            await _expl_msg.pin()
        except discord.Forbidden:
            pass

        ow_classement = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me:           discord.PermissionOverwrite(send_messages=True, read_messages=True),
        }
        if tournoi_role:
            ow_classement[tournoi_role] = discord.PermissionOverwrite(send_messages=False, read_messages=True)
        ch_classement = await guild.create_text_channel(
            name       = name_cl,
            category   = category,
            overwrites = ow_classement,
            topic      = f"Classements et pairings — {t_name}",
        )

    except discord.Forbidden as e:
        print(f"[auto-tournoi] Permission refusée : {e}")
        return False
    except Exception as e:
        print(f"[auto-tournoi] Erreur création canaux : {e}")
        return False

    pairing      = "Swiss" if tournament.get("pairing_system") == "swiss" else "Standard"
    is_commander = "👑" in fmt

    embed = discord.Embed(
        title       = f"🏆  {t_name}  — Tournoi lancé !",
        description = "Le tournoi vient de démarrer. Bonne chance à tous ! 🎉",
        color       = COLOR_START,
    )
    embed.add_field(name="🎮 Format",  value=fmt,                                    inline=True)
    embed.add_field(name="📅 Date",    value=tournament.get("date", "?"),            inline=True)
    embed.add_field(name="🔄 Rounds",  value=str(tournament.get("max_rounds", "?")), inline=True)
    embed.add_field(name="⚙️ Système", value=pairing,                                inline=True)
    embed.add_field(name="👥 Joueurs", value=str(len(players)),                      inline=True)

    if players:
        player_lines = []
        for p in players:
            line = f"• **{p.get('name', '?')}**"
            if is_commander and p.get("commander"):
                line += f"  —  👑 {p['commander']}"
            player_lines.append(line)
        embed.add_field(name=f"📋 Participants ({len(players)})", value="\n".join(player_lines), inline=False)

    if no_account:
        embed.add_field(
            name  = "⚠️ Sans compte Discord lié",
            value = ", ".join(no_account) + "\n*Tape `!register` pour lier ton compte.*",
            inline=False,
        )

    embed.set_footer(text=f"📊 #{name_cl}  ·  📝 #{name_res}")
    msg = await ch_classement.send(embed=embed)
    try:
        await msg.pin()
    except discord.Forbidden:
        pass

    if mentions:
        await ch_classement.send("🎮 " + " ".join(mentions) + " — à vos decks, le tournoi commence !")

    pairings_embed = None
    for _ in range(5):
        fresh = next((t for t in load_json("tournaments.json") if t.get("id") == tournament.get("id")), tournament)
        pairings_embed = _build_pairings_embed(fresh)
        if pairings_embed:
            break
        import asyncio
        await asyncio.sleep(1)

    if pairings_embed:
        await ch_classement.send(embed=pairings_embed)
        await ch_resultats.send(embed=pairings_embed)
        print(f"[auto-tournoi] Pairings postés pour « {t_name} »")
    else:
        print(f"[auto-tournoi] Pas de pairings disponibles pour « {t_name} »")

    print(f"[auto-tournoi] Canaux créés pour « {t_name} » dans '{TOURNAMENT_CATEGORY_NAME}'")
    return True


# ── Polling démarrage tournoi (toutes les 10 secondes) ────────────────────────

@tasks.loop(seconds=2)
async def check_pending_starts():
    """Vérifie pending_starts.json et crée les canaux si un tournoi a démarré."""
    if not PENDING_FILE.exists():
        return
    try:
        pending = json.loads(PENDING_FILE.read_text(encoding="utf-8"))
    except Exception:
        return
    if not pending:
        return

    all_t     = load_json("tournaments.json")
    remaining = []

    for tid in pending:
        tournament = next((t for t in all_t if t.get("id") == tid), None)
        if tournament is None:
            print(f"[auto-tournoi] ID {tid} introuvable, ignoré")
            continue

        handled = False
        for guild in bot.guilds:
            ok = await _create_tournament_channels_auto(guild, tournament)
            if ok:
                handled = True

        if not handled:
            remaining.append(tid)

    PENDING_FILE.write_text(json.dumps(remaining, indent=2), encoding="utf-8")



# ── Polling quitter tournoi (suppression canaux) ──────────────────────────────

PENDING_QUITS_FILE = DATA_DIR / "pending_quits.json"

@tasks.loop(seconds=2)
async def check_pending_quits():
    """Vérifie pending_quits.json et supprime les canaux tournoi."""
    if not PENDING_QUITS_FILE.exists():
        return
    try:
        pending = json.loads(PENDING_QUITS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return
    if not pending:
        return

    all_t     = load_json("tournaments.json")
    remaining = []
    for tid in pending:
        t_data    = next((t for t in all_t if t.get("id") == tid), None)
        t_name    = t_data.get("name") if t_data else None
        handled   = False
        for guild in bot.guilds:
            try:
                await _cleanup_tournament_channels(guild, t_name, tournament_id=str(tid))
                handled = True
                print(f"[auto-tournoi] Canaux supprimés (tournoi {tid})")
            except Exception as e:
                print(f"[auto-tournoi] Erreur suppression canaux : {e}")
        if not handled:
            remaining.append(tid)

    PENDING_QUITS_FILE.write_text(json.dumps(remaining, indent=2), encoding="utf-8")




# ── Helpers pour notifications round ─────────────────────────────────────────

def _build_standings_embed(tournament: dict, after_label: str) -> "discord.Embed | None":
    """Classement cumulatif des joueurs après un round."""
    players = [p for p in tournament.get("players", []) if not p.get("dropped", False)]
    if not players:
        return None

    fmt          = tournament.get("format", "")
    is_commander = "👑" in fmt
    t_name       = tournament.get("name", "")

    if is_commander:
        sorted_p = sorted(players, key=lambda p: (-p.get("score", 0), -p.get("robustness", 0), p.get("name", "")))
    else:
        sorted_p = sorted(players, key=lambda p: (-p.get("score", 0), -p.get("buchholz", 0), -p.get("sos", 0), p.get("name", "")))

    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    lines  = []
    for i, p in enumerate(sorted_p, 1):
        prefix = medals.get(i, f"`{i}.`")
        score  = p.get("score", 0)
        name   = p.get("name", "?")
        if is_commander:
            rob    = p.get("robustness", 0)
            detail = f"**{score} pts** · Rob. {rob}"
        else:
            buch   = p.get("buchholz", 0)
            detail = f"**{score} pts** · Buch. {buch}"
        lines.append(f"{prefix} {name} — {detail}")

    embed = discord.Embed(
        title       = f"📊 Classement après {after_label}",
        description = "\n".join(lines),
        color       = COLOR_RANK,
    )
    embed.set_footer(text=t_name)
    return embed


def _build_bracket_pairings_embed(tournament: dict, bracket_round_name: str) -> "discord.Embed | None":
    """Construit l'embed des matchs d'un round de bracket."""
    bracket = tournament.get("bracket", {})
    if not bracket:
        return None

    matches = [m for m in bracket.get("matches", []) if m.get("round_name") == bracket_round_name]
    if not matches:
        return None

    players_by_id = {p["id"]: p for p in tournament.get("players", [])}
    label  = BRACKET_ROUND_LABELS.get(bracket_round_name, bracket_round_name)
    t_name = tournament.get("name", "")

    lines = []
    for m in sorted(matches, key=lambda x: x.get("position", 0)):
        p1 = players_by_id.get(m.get("player1_id"), {})
        p2 = players_by_id.get(m.get("player2_id"), {})
        n1 = p1.get("name", "TBD") if p1 else "TBD"
        n2 = p2.get("name", "TBD") if p2 else "TBD"
        if m.get("is_third_place"):
            lines.append(f"> 🥉  **Petite finale**\n> **{n1}**  vs  **{n2}**")
        else:
            lines.append(f"> 🏆  **{label}**\n> **{n1}**  vs  **{n2}**")

    embed = discord.Embed(
        title       = f"🏆 Phase éliminatoire — {label}",
        description = "\n\n".join(lines),
        color       = COLOR_BRACKET,
    )
    embed.set_footer(text=f"{t_name}  ·  Entrez votre résultat dans #resultats-rounds")
    return embed


# ── Polling : chrono lancé ────────────────────────────────────────────────────

@tasks.loop(seconds=2)
async def check_pending_round_starts():
    """Annonce dans #resultats-rounds que le chrono est lancé."""
    if not PENDING_ROUND_STARTS_FILE.exists():
        return
    try:
        pending = json.loads(PENDING_ROUND_STARTS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return
    if not pending:
        return

    remaining = []
    for entry in pending:
        round_num      = entry.get("round_num")
        bracket_round  = entry.get("bracket_round")
        t_name         = entry.get("tournament_name", "")
        t_fmt          = entry.get("tournament_format", "")
        t_id           = str(entry.get("tournament_id", ""))
        # Fallback : lire le format depuis tournaments.json si absent du payload
        if not t_fmt:
            all_t  = load_json("tournaments.json")
            t_data = next((t for t in all_t if t.get("id") == entry.get("tournament_id")), None)
            if t_data:
                t_fmt = t_data.get("format", "")
        is_commander   = "👑" in t_fmt

        if bracket_round:
            label       = BRACKET_ROUND_LABELS.get(bracket_round, bracket_round)
            title       = f"⏱️  {label} — C'est parti !"
            score_hint  = "`!score victoire` ou `!score défaite`"
        elif is_commander:
            label       = f"Round {round_num}"
            title       = f"⏱️  Round {round_num} — C'est parti !"
            score_hint  = "`!score <1er> <2ème>` — ex: `!score Martin Léo`"
        else:
            label       = f"Round {round_num}"
            title       = f"⏱️  Round {round_num} — C'est parti !"
            score_hint  = "`!score 2-0` · `!score 2-1` · `!score 1-1` · `!score 1-2` · `!score 0-2`"

        handled = False
        for guild in bot.guilds:
            ch_res, _ = _find_channels(guild, t_name, t_id)
            if not ch_res:
                continue

            embed = discord.Embed(
                title       = title,
                description = "Le chrono est lancé ! Jouez votre match et entrez votre résultat ici.",
                color       = COLOR_CHRONO,
            )
            embed.add_field(name="🎯 Commande", value=score_hint, inline=False)
            if t_name:
                embed.set_footer(text=t_name)

            await ch_res.send(embed=embed)
            handled = True

        if not handled:
            remaining.append(entry)

    PENDING_ROUND_STARTS_FILE.write_text(json.dumps(remaining, indent=2), encoding="utf-8")


# ── Polling : round suivant / classement + pairings ──────────────────────────

@tasks.loop(seconds=2)
async def check_pending_next_rounds():
    """Affiche le classement du round précédent + les nouveaux pairings."""
    if not PENDING_NEXT_ROUNDS_FILE.exists():
        return
    try:
        pending = json.loads(PENDING_NEXT_ROUNDS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return
    if not pending:
        return

    remaining = []
    for entry in pending:
        t_data           = entry.get("tournament_data", {})
        prev_round_num   = entry.get("prev_round_num")
        prev_brk         = entry.get("prev_bracket_round")
        new_brk          = entry.get("new_bracket_round")
        eliminated_names = entry.get("eliminated_names", [])

        if prev_brk:
            prev_label = BRACKET_ROUND_LABELS.get(prev_brk, prev_brk)
        elif prev_round_num is not None:
            prev_label = f"Round {prev_round_num}"
        else:
            prev_label = None

        handled = False
        for guild in bot.guilds:
            ch_res, ch_cl = _find_channels(guild, t_data.get("name", ""), str(t_data.get("id", "")))
            if not ch_cl or not ch_res:
                continue

            # ── Séparateur visuel ─────────────────────────────────────────────
            sep_label = f"Fin du {prev_label}" if prev_label else "Nouveau round"
            await ch_cl.send(f"** **\n**─────────────────── {sep_label} ───────────────────**")
            await ch_res.send("** **")

            # 1. Classement du round précédent (si disponible)
            if prev_label:
                standings_embed = _build_standings_embed(t_data, prev_label)
                if standings_embed:
                    await ch_cl.send(embed=standings_embed)

            # 2. Nouveaux pairings
            if new_brk:
                pairings_embed = _build_bracket_pairings_embed(t_data, new_brk)
            else:
                pairings_embed = _build_pairings_embed(t_data)

            if pairings_embed:
                await ch_cl.send(embed=pairings_embed)
                await ch_res.send(embed=pairings_embed)

            # 3. Si phase bracket, info sur comment entrer les résultats
            if new_brk:
                brk_info_embed = discord.Embed(
                    title       = "🏆 Phase éliminatoire — Comment entrer ton résultat",
                    description = (
                        "`!score victoire` — Tu as **gagné** ton match\n"
                        "`!score défaite` — Tu as **perdu** ton match\n\n"
                        "⚠️ Le format `2-1` n'est **pas valide** en phase éliminatoire."
                    ),
                    color = COLOR_BRACKET,
                )
                await ch_res.send(embed=brk_info_embed)

            # 4. Retirer les droits d'écriture aux joueurs éliminés (bracket)
            if eliminated_names:
                all_regular = load_json("regular_players.json")
                discord_map = {p.get("pseudo", "").lower(): p.get("discord_id") for p in all_regular if p.get("discord_id")}
                current_ow  = dict(ch_res.overwrites)
                modified    = False

                for name in eliminated_names:
                    did = discord_map.get(name.lower())
                    if did:
                        try:
                            member = await guild.fetch_member(did)
                            current_ow[member] = discord.PermissionOverwrite(send_messages=False, read_messages=True)
                            modified = True
                        except Exception:
                            pass

                if modified:
                    try:
                        await ch_res.edit(overwrites=current_ow)
                    except Exception as e:
                        print(f"[bracket] Erreur permissions : {e}")

                elim_embed = discord.Embed(
                    title       = "🚫 Joueurs éliminés",
                    description = "\n".join(f"• **{n}**" for n in eliminated_names),
                    color       = COLOR_ELIM,
                )
                elim_embed.set_footer(text="Ces joueurs ne peuvent plus écrire dans ce canal.")
                await ch_res.send(embed=elim_embed)

            handled = True

        if not handled:
            remaining.append(entry)

    PENDING_NEXT_ROUNDS_FILE.write_text(json.dumps(remaining, indent=2), encoding="utf-8")


# ── Polling : fin de tournoi ──────────────────────────────────────────────────

@tasks.loop(seconds=2)
async def check_pending_finishes():
    """Affiche le classement final et clôture le tournoi."""
    if not PENDING_FINISHES_FILE.exists():
        return
    try:
        pending = json.loads(PENDING_FINISHES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return
    if not pending:
        return

    remaining = []
    for entry in pending:
        t_name        = entry.get("tournament_name", "Tournoi")
        t_id          = str(entry.get("tournament_id", ""))
        final_ranking = entry.get("final_ranking", [])

        # Trouver le rôle associé à ce tournoi via le slot
        slot_entry = _get_slot_entry(t_id) if t_id else None
        role_name  = TOURNAMENT_ROLE_NAMES[slot_entry["slot"] - 1] if slot_entry else None

        handled = False
        for guild in bot.guilds:
            _, ch_cl = _find_channels(guild, t_name, t_id)
            if not ch_cl:
                continue

            # ── Séparateur ────────────────────────────────────────────────────
            await ch_cl.send("** **\n**═══════════════════ FIN DU TOURNOI ═══════════════════**")

            # ── Embed classement final ────────────────────────────────────────
            medals = {0: "🥇", 1: "🥈", 2: "🥉"}
            lines  = []
            for i, name in enumerate(final_ranking):
                prefix = medals.get(i, f"`{i+1}.`")
                lines.append(f"{prefix}  **{name}**")

            embed = discord.Embed(
                title       = f"🏆  {t_name} — Classement final",
                description = "\n".join(lines) if lines else "Classement non disponible.",
                color       = COLOR_FINISH,
            )
            embed.set_footer(text="Merci à tous les participants ! 🎉")
            await ch_cl.send(embed=embed)

            # ── Mention du vainqueur ──────────────────────────────────────────
            if final_ranking:
                winner_name = final_ranking[0]
                all_regular = load_json("regular_players.json")
                discord_map = {p.get("pseudo","").lower(): p.get("discord_id") for p in all_regular if p.get("discord_id")}
                did = discord_map.get(winner_name.lower())
                mention = f"<@{did}>" if did else f"**{winner_name}**"
                await ch_cl.send(f"🎊 Félicitations à {mention} pour sa victoire !")

            # ── Retirer le rôle et libérer le slot ───────────────────────────
            if role_name:
                await _remove_tournoi_role(guild, role_name)
            if t_id:
                _release_slot(t_id)

            handled = True

        if not handled:
            remaining.append(entry)

    PENDING_FINISHES_FILE.write_text(json.dumps(remaining, indent=2), encoding="utf-8")


bot.run(TOKEN)
