"""
Export PDF d'un tournoi : doit fonctionner même sans police Unicode installée
(repli Helvetica, cas systématique sous Windows), avec des formats à emoji.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

pytest.importorskip("fpdf")

from core.tournament import Tournament  # noqa: E402
from export import pdf_export  # noqa: E402


@pytest.mark.parametrize("fmt", ["⚔️ Duel Commander", "⚡ Pokemon", "👑 Commander", "🏆 AP"])
def test_export_without_unicode_font(tmp_path, monkeypatch, fmt):
    # Aucune police DejaVu trouvée → repli Helvetica (latin-1)
    real_exists = os.path.exists
    monkeypatch.setattr(os.path, "exists", lambda p: False if "DejaVu" in str(p) else real_exists(p))
    t = Tournament.create_tournament(
        tournament_id=0, name="Tournoi ⚔ Été", format=fmt, date="01/01/2026", max_rounds=1
    )
    t.pairing_system = "standard" if fmt == "👑 Commander" else "swiss"
    for name in ["Léa", "Zoë ⭐", "Bob", "Ana", "Éric", "Noé"]:
        t.add_player(name)
    t.create_round()
    out = tmp_path / "t.pdf"
    assert pdf_export.export_tournament_pdf(t, str(out)) is True
    assert out.stat().st_size > 0
