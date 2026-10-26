<p align="center"><img src="docs/logo_256.png" width="128" alt="Vendémiaire"></p>

# Vendémiaire

**A complete, offline wine cellar manager**: every bottle, its place in the cellar, the cellar book of
ins and outs, and soon drinking windows, serving advice and food pairings. French / English,
Windows, macOS and Linux. No data ever leaves the computer.

*Version française : [README.md](README.md).*

> **Status: phase 1 (foundations and cellar), not released yet.** See [PROGRESSION.md](PROGRESSION.md) (in French).

![Dashboard](docs/captures/en-tableau-de-bord.png)

## What phase 1 does

- **Cellar**: wines (producer, cuvée, appellation, region, country, colour, type, grapes with
  percentages, vintage, ABV, LWIN, barcode) and **individual bottles** — sizes from piccolo to
  Melchizedek, status (in cellar, awaiting delivery, en primeur, drunk, given away, sold, broken,
  corked), purchase price and place, dates, fill level (auction scale or in cm), label, capsule and
  cork condition, original wooden case, provenance.
- **Rack plan**: cellars › units › racks in rows and columns, several cellars; drag and drop a
  bottle (swap when the slot is taken), select several bottles and **move them as a batch**; every
  move is kept in the history.
- **Cellar book**: every in and out with occasion, guests, dish, score (out of 20, 100 or stars)
  and comment.
- **Wine sheet**: "cover" (label photo, or a drawn label), drinking windows (mine, critics'; the
  computed one comes in phase 3), critics' scores with their scale, dated and sourced value.
- **Dashboard**: bottles, litres, value paid and estimated, breakdowns, futures to be delivered,
  restock thresholds.
- **No locked-in data**: CSV export (one row per bottle) that re-imports losslessly, full JSON
  export, **CellarTracker** export import ([details, in French](docs/import_cellartracker.md)).
  An import never overwrites manually entered data.
- **Automatic backups** (at start-up, every 30 minutes when the database changed, on exit, before
  every import) with rotation; restore from the File menu.

![Cellar](docs/captures/en-cave.png)

## Run from source

```bash
python -m pip install -r requirements.txt
python run.py            # your cellar
python run.py --demo     # a demo cellar (made-up data)
python run.py --lang fr  # French interface
```

## Tests

```bash
xvfb-run -a python -m pytest -q tests/
```

## Licence

MIT — see [LICENSE](LICENSE). Embedded fonts under the SIL Open Font License.
