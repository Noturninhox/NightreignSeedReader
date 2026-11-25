"""Nomes em PT-BR e resumo das seeds."""

from __future__ import annotations

from dataclasses import dataclass

from nrseed.engine.map_info import MapInfo, MapPattern
from nrseed.engine.resources import get_data_path

NIGHTLORDS: dict[int, tuple[str, str]] = {
    0: ("Gladius", "Tricephalos"),
    1: ("Adel", "Gaping Jaw"),
    2: ("Gnoster", "Sentient Pest"),
    3: ("Maris", "Augur"),
    4: ("Libra", "Equilibrious Beast"),
    5: ("Fulghor", "Darkdrift Knight"),
    6: ("Caligo", "Fissure in the Fog"),
    7: ("Heolstor", "Night Aspect"),
    8: ("Harmonia", "Balancers · DLC"),
    9: ("Straghess", "Dreglord · DLC"),
}

TERRAINS: dict[int, str] = {
    0: "Normal",
    1: "Mountaintop",
    2: "Crater",
    3: "Rotted Woods",
    4: "Great Hollow",
    5: "Noklateo",
}

TERRAIN_PT: dict[int, str] = {
    0: "Sem Terra Mutável",
    1: "Topo da Montanha",
    2: "Cratera",
    3: "Bosque Podre",
    4: "Grande Vazio (DLC)",
    5: "Noklateo, Cidade Oculta",
}

SITE_URL = "https://nightreign-seed-finder.com/result/{:03d}"


def nightlord_label(nl: int | None) -> str:
    if nl is None:
        return "Desconhecido"
    name, epithet = NIGHTLORDS.get(nl, (str(nl), ""))
    return f"{name} — {epithet}" if epithet else name


def nightlord_icon_path(nl: int | None) -> str:
    return get_data_path("icons/nightlord/unk.png" if nl is None else f"icons/nightlord/{nl}.png")


def terrain_icon_path(es: int) -> str:
    return get_data_path(f"maps/{es}.jpg")


@dataclass
class SeedSummary:
    seed_id: int
    nightlord: int
    terrain: int
    day1: str
    day2: str
    day1_extra: str | None
    day2_extra: str | None
    event: str | None
    site_url: str | None


def summarize(info: MapInfo, p: MapPattern) -> SeedSummary:
    def name(i: int) -> str:
        return info.get_name(i) or "Desconhecido"

    event = None
    if p.event_flag:
        flag_name = name(p.event_flag)
        event = f"{flag_name} {name(p.event_value)}" if p.event_flag in (7705, 7725) else flag_name
    return SeedSummary(
        seed_id=p.id,
        nightlord=p.nightlord,
        terrain=p.earth_shifting,
        day1=name(p.day1_boss),
        day2=name(p.day2_boss),
        day1_extra=name(p.day1_extra_boss) if p.day1_extra_boss != -1 else None,
        day2_extra=name(p.day2_extra_boss) if p.day2_extra_boss != -1 else None,
        event=event,
        # Numeração do jogo base coincide com a do site; padrões DLC (>=1000) não têm link confirmado.
        site_url=SITE_URL.format(p.id) if p.id < 1000 else None,
    )
