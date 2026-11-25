"""Valida o motor nas capturas reais (nome do arquivo = ID esperado da seed)."""
import logging, random, sys, time
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nrseed.engine.detector import MapDetector, MapDetectParam

logging.disable(logging.INFO)
det = MapDetector(language="en_US")
ok = 0; files = sorted(Path(__file__).parent.joinpath("samples").glob("*.jpg"))
for f in files:
    exp = [int(v) for v in f.stem.split("_")[0].split("-")]
    img = np.array(Image.open(f).convert("RGB"))
    random.seed(42); t = time.perf_counter()
    full = det.detect(MapDetectParam(map_region=(0, 0, *img.shape[1::-1]), img=img, do_match_full_map=True, do_match_earth_shifting=True))
    res = det.detect(MapDetectParam(map_region=(0, 0, *img.shape[1::-1]), img=img, earth_shifting=full.earth_shifting, do_match_pattern=True, return_pattern_topk=3))
    ids = [p.id for p in res.patterns]
    good = ids and ids[0] in exp; ok += good
    print(f"{f.name:22} full={full.is_full_map!s:5} terreno={full.earth_shifting} nightlord={res.nightlord} top3={ids} {'OK' if good else 'X'} {time.perf_counter()-t:.1f}s")
print(f"{ok}/{len(files)} corretos")
