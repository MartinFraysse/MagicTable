"""
Export PDF des résultats de tournoi.
Nécessite: pip install fpdf2
"""

import re
from core.tournament import Tournament


# Palette de couleurs harmonisée
COLORS = {
    'primary': (26, 26, 46),        # #1a1a2e - Fond foncé
    'secondary': (22, 33, 62),      # #16213e - Bleu foncé
    'accent': (15, 52, 96),         # #0f3460 - Bleu
    'highlight': (233, 69, 96),     # #e94560 - Rose/rouge
    'success': (63, 210, 125),      # #3fd27d - Vert
    'gold': (255, 193, 7),          # #ffc107 - Or
    'silver': (176, 190, 197),      # #b0bec5 - Argent
    'bronze': (205, 127, 50),       # #cd7f32 - Bronze
    'text_dark': (33, 33, 33),      # #212121
    'text_light': (255, 255, 255),  # #ffffff
    'text_muted': (120, 120, 120),  # #787878
    'bg_light': (248, 249, 250),    # #f8f9fa
    'bg_alt': (233, 236, 239),      # #e9ecef
    'border': (206, 212, 218),      # #ced4da
}


def _clean_text_for_pdf(text: str) -> str:
    """Supprime les emojis et caractères non supportés pour l'export PDF."""
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F700-\U0001F77F"
        "\U0001F780-\U0001F7FF"
        "\U0001F800-\U0001F8FF"
        "\U0001F900-\U0001F9FF"
        "\U0001FA00-\U0001FA6F"
        "\U0001FA70-\U0001FAFF"
        "\U00002702-\U000027B0"
        "\U0001F1E0-\U0001F1FF"
        "]+",
        flags=re.UNICODE
    )
    return emoji_pattern.sub("", text).strip()


def _clean_format(fmt: str) -> str:
    """Nettoie le format du tournoi (supprime les emojis)."""
    return _clean_text_for_pdf(fmt)


def export_tournament_pdf(tournament: Tournament, filepath: str) -> bool:
    """
    Exporte les résultats d'un tournoi en PDF avec un style moderne.
    """
    try:
        from fpdf import FPDF
        import os

        class TournamentPDF(FPDF):
            def __init__(self):
                super().__init__()
                self.set_auto_page_break(auto=True, margin=25)
                self._setup_unicode_font()
                self.tournament_name = ""
                self.tournament_format = ""

            def _setup_unicode_font(self):
                """Configure une police Unicode."""
                font_paths = [
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                    "/usr/share/fonts/TTF/DejaVuSans.ttf",
                    "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf",
                    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
                ]
                for font_path in font_paths:
                    if os.path.exists(font_path):
                        self.add_font("DejaVu", "", font_path)
                        self.add_font("DejaVu", "B", font_path.replace(".ttf", "-Bold.ttf"))
                        self.add_font("DejaVu", "I", font_path.replace(".ttf", "-Oblique.ttf"))
                        self.unicode_font = "DejaVu"
                        return
                self.unicode_font = "Helvetica"

            def get_font(self):
                return self.unicode_font

            def header(self):
                if self.page_no() == 1:
                    return
                # Header pour pages suivantes
                self.set_fill_color(*COLORS['secondary'])
                self.rect(0, 0, 210, 15, 'F')
                self.set_font(self.unicode_font, 'B', 10)
                self.set_text_color(*COLORS['text_light'])
                self.set_y(4)
                self.cell(0, 8, f"{self.tournament_name} - {self.tournament_format}", align='C')
                self.ln(15)

            def footer(self):
                self.set_y(-20)
                # Ligne de séparation
                self.set_draw_color(*COLORS['border'])
                self.line(20, self.get_y(), 190, self.get_y())
                self.ln(5)
                # Texte du footer
                self.set_font(self.unicode_font, 'I', 8)
                self.set_text_color(*COLORS['text_muted'])
                self.cell(0, 10, f'MagicTable Tournament Manager  |  Page {self.page_no()}', align='C')

            def draw_rounded_rect(self, x, y, w, h, r, style='', color=None):
                """Dessine un rectangle avec coins arrondis."""
                if color:
                    self.set_fill_color(*color)
                    self.set_draw_color(*color)
                # Simulation avec un rectangle simple (fpdf2 basique)
                if 'F' in style:
                    self.rect(x, y, w, h, 'F')
                if 'D' in style:
                    self.rect(x, y, w, h, 'D')

        pdf = TournamentPDF()
        pdf.tournament_name = _clean_text_for_pdf(tournament.name)
        pdf.tournament_format = _clean_format(tournament.format)
        pdf.add_page()
        pdf.set_margins(20, 20, 20)
        font = pdf.get_font()

        # ========================================
        # BANDEAU HEADER
        # ========================================
        pdf.set_fill_color(*COLORS['primary'])
        pdf.rect(0, 0, 210, 50, 'F')

        # Accent coloré en haut
        pdf.set_fill_color(*COLORS['highlight'])
        pdf.rect(0, 0, 210, 4, 'F')

        # Titre du tournoi
        pdf.set_y(12)
        pdf.set_font(font, 'B', 28)
        pdf.set_text_color(*COLORS['text_light'])
        pdf.cell(0, 12, _clean_text_for_pdf(tournament.name), align='C', new_x='LMARGIN', new_y='NEXT')

        # Sous-titre avec infos
        pdf.set_font(font, '', 11)
        pdf.set_text_color(*COLORS['silver'])
        info_text = f"{_clean_format(tournament.format)}   |   {tournament.date}   |   {len(tournament.players)} joueurs   |   {len(tournament.rounds)} rounds"
        pdf.cell(0, 8, info_text, align='C', new_x='LMARGIN', new_y='NEXT')

        pdf.ln(20)

        # ========================================
        # PODIUM (Top 3)
        # ========================================
        ranked_players = sorted(
            tournament.players,
            key=lambda p: (-p.score, -p.robustness, p.name)
        )

        if len(ranked_players) >= 3:
            pdf.set_font(font, 'B', 14)
            pdf.set_text_color(*COLORS['text_dark'])
            pdf.cell(0, 10, 'PODIUM', align='C', new_x='LMARGIN', new_y='NEXT')
            pdf.ln(3)

            # Dessiner les 3 podiums
            podium_width = 50
            podium_spacing = 8
            start_x = (210 - (podium_width * 3 + podium_spacing * 2)) / 2

            podium_colors = [COLORS['gold'], COLORS['silver'], COLORS['bronze']]
            podium_heights = [35, 28, 24]
            podium_labels = ['1er', '2e', '3e']

            for i, (player, color, height, label) in enumerate(zip(ranked_players[:3], podium_colors, podium_heights, podium_labels)):
                x = start_x + i * (podium_width + podium_spacing)
                y = pdf.get_y() + (35 - height)

                # Bloc coloré
                pdf.set_fill_color(*color)
                pdf.rect(x, y, podium_width, height, 'F')

                # Rang
                pdf.set_xy(x, y + 3)
                pdf.set_font(font, 'B', 16)
                pdf.set_text_color(*COLORS['text_dark'])
                pdf.cell(podium_width, 8, label, align='C')

                # Nom du joueur
                pdf.set_xy(x, y + 12)
                pdf.set_font(font, 'B', 10)
                player_name = _clean_text_for_pdf(player.name)
                if len(player_name) > 12:
                    player_name = player_name[:11] + "."
                pdf.cell(podium_width, 6, player_name, align='C')

                # Score
                pdf.set_xy(x, y + 19)
                pdf.set_font(font, '', 9)
                pdf.cell(podium_width, 5, f"{player.score} pts", align='C')

            pdf.ln(42)

        # ========================================
        # CLASSEMENT COMPLET
        # ========================================
        pdf.set_font(font, 'B', 14)
        pdf.set_text_color(*COLORS['text_dark'])
        pdf.cell(0, 10, 'CLASSEMENT COMPLET', align='C', new_x='LMARGIN', new_y='NEXT')
        pdf.ln(5)

        # Tableau
        col_widths = [18, 82, 35, 35]
        row_height = 9
        table_width = sum(col_widths)
        table_x = (210 - table_width) / 2

        # En-tête du tableau
        pdf.set_x(table_x)
        pdf.set_fill_color(*COLORS['secondary'])
        pdf.set_text_color(*COLORS['text_light'])
        pdf.set_font(font, 'B', 10)
        headers = ['#', 'Joueur', 'Score', 'Robustesse']
        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], row_height + 2, header, border=0, align='C', fill=True)
        pdf.ln()

        # Données
        pdf.set_font(font, '', 9)
        for rank, player in enumerate(ranked_players, 1):
            # Vérifier saut de page
            if pdf.get_y() > 260:
                pdf.add_page()
                pdf.set_y(25)

            # Couleur de fond alternée
            if rank <= 3:
                colors_map = {1: COLORS['gold'], 2: COLORS['silver'], 3: COLORS['bronze']}
                pdf.set_fill_color(*colors_map[rank])
                pdf.set_text_color(*COLORS['text_dark'])
            elif rank % 2 == 0:
                pdf.set_fill_color(*COLORS['bg_light'])
                pdf.set_text_color(*COLORS['text_dark'])
            else:
                pdf.set_fill_color(*COLORS['bg_alt'])
                pdf.set_text_color(*COLORS['text_dark'])

            pdf.set_x(table_x)
            pdf.set_font(font, 'B' if rank <= 3 else '', 9)
            pdf.cell(col_widths[0], row_height, str(rank), border=0, align='C', fill=True)
            pdf.set_font(font, '', 9)
            pdf.cell(col_widths[1], row_height, _clean_text_for_pdf(player.name), border=0, align='L', fill=True)
            pdf.cell(col_widths[2], row_height, f"{player.score} pts", border=0, align='C', fill=True)
            pdf.cell(col_widths[3], row_height, str(player.robustness), border=0, align='C', fill=True)
            pdf.ln()

        pdf.ln(10)

        # ========================================
        # DÉTAILS DES ROUNDS
        # ========================================
        pdf.add_page()

        pdf.set_font(font, 'B', 14)
        pdf.set_text_color(*COLORS['text_dark'])
        pdf.cell(0, 10, 'DETAILS DES ROUNDS', align='C', new_x='LMARGIN', new_y='NEXT')
        pdf.ln(8)

        for rnd in tournament.rounds:
            if pdf.get_y() > 240:
                pdf.add_page()
                pdf.set_y(25)

            # Titre du round avec bandeau
            pdf.set_fill_color(*COLORS['accent'])
            pdf.set_text_color(*COLORS['text_light'])
            pdf.set_font(font, 'B', 12)
            pdf.cell(0, 10, f"  Round {rnd.number}", border=0, align='L', fill=True, new_x='LMARGIN', new_y='NEXT')
            pdf.ln(3)

            # Tables en grille (2 colonnes)
            tables = rnd.tables
            table_card_width = 82
            spacing = 6
            start_x = 20

            for idx, table in enumerate(tables):
                col = idx % 2
                if col == 0 and idx > 0:
                    pdf.ln(2)

                if pdf.get_y() > 250:
                    pdf.add_page()
                    pdf.set_y(25)

                x = start_x + col * (table_card_width + spacing)
                y = pdf.get_y()

                # Fond de la carte table
                pdf.set_fill_color(*COLORS['bg_light'])
                card_height = 6 + len(table.players) * 5 + 2
                pdf.rect(x, y, table_card_width, card_height, 'F')

                # Bordure gauche colorée
                pdf.set_fill_color(*COLORS['highlight'])
                pdf.rect(x, y, 3, card_height, 'F')

                # Titre de la table
                pdf.set_xy(x + 5, y + 1)
                pdf.set_font(font, 'B', 9)
                pdf.set_text_color(*COLORS['text_dark'])
                pdf.cell(table_card_width - 10, 5, f"Table {table.number}", align='L')

                # Joueurs
                if table.results:
                    sorted_players = sorted(
                        table.players,
                        key=lambda p: table.results.get(p.id, 99)
                    )
                else:
                    sorted_players = table.players

                pdf.set_font(font, '', 8)
                for i, player in enumerate(sorted_players):
                    pdf.set_xy(x + 5, y + 6 + i * 5)
                    player_name = _clean_text_for_pdf(player.name)

                    if table.results and player.id in table.results:
                        position = table.results[player.id]
                        pos_label = {1: "1er", 2: "2e", 3: "3e", 4: "4e"}.get(position, f"{position}e")
                        # Couleur selon position
                        if position == 1:
                            pdf.set_text_color(*COLORS['success'])
                        elif position == 2:
                            pdf.set_text_color(*COLORS['accent'])
                        else:
                            pdf.set_text_color(*COLORS['text_muted'])
                        pdf.set_font(font, 'B', 8)
                        pdf.cell(12, 5, pos_label, align='L')
                        pdf.set_font(font, '', 8)
                        pdf.set_text_color(*COLORS['text_dark'])
                        pdf.cell(table_card_width - 22, 5, player_name, align='L')
                    else:
                        pdf.set_text_color(*COLORS['text_dark'])
                        pdf.cell(table_card_width - 10, 5, f"  {player_name}", align='L')

                # Si colonne impaire, passer à la ligne suivante
                if col == 1:
                    pdf.set_y(y + card_height + 3)
                else:
                    # Garder la position Y pour la prochaine carte
                    if idx == len(tables) - 1:
                        pdf.set_y(y + card_height + 3)

            # Si nombre impair de tables, finaliser la position
            if len(tables) % 2 == 1:
                pdf.ln(len(tables[-1].players) * 5 + 10)

            pdf.ln(8)

        # Générer le PDF
        pdf.output(filepath)
        return True

    except Exception as e:
        print(f"Erreur lors de l'export PDF: {e}")
        return False
