"""Sdílená utilita pro bezpečnou perzistenci souborů na disk."""

from __future__ import annotations

import os
from pathlib import Path


def atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    """Zapíše text do souboru atomicky (přes dočasný soubor + rename).

    Bez tohoto kroku by pád procesu nebo výpadek uprostřed zápisu (např.
    během probíhající RZ) mohl nechat na disku napůl zapsaný, nevalidní
    JSON. `os.replace` provede přejmenování jako jednu atomickou operaci
    na Windows i Linuxu, takže čtenář vždy najde buď starou, nebo celou
    novou verzi souboru.

    Args:
        path: Cílová cesta souboru.
        content: Obsah k zápisu.
        encoding: Kódování textu.
    """
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(content, encoding=encoding)
    os.replace(tmp_path, path)
