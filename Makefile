# SIH26081 — Multi-Model Weather Blend
# make env · make data · make inventory · make test · make results · make rasters · make sync · make reproduce

PYTHON = python
FRONTEND = frontend

.PHONY: env data inventory static test results rasters sync reproduce clean

## Environment
env:
	mamba env create -f environment.yml --force
	@echo "Activate with: mamba activate sih26081"

## Data download (WB2 → data/raw/)
data:
	$(PYTHON) -m ingestion.download

## Inventory check
inventory:
	$(PYTHON) -m ingestion.inventory

## Static layers (districts, population, land mask)
static:
	$(PYTHON) -m ingestion.static

## Tests
test:
	$(PYTHON) -m pytest tests/ -v

## Full pipeline → results/
results:
	$(PYTHON) -m experiments.run --cycle 2022-06-14

## Rasters only (re-render from existing results)
rasters:
	$(PYTHON) -c "from outputs.render_png import write_bounds; write_bounds()"

## Sync results → frontend/public/data/
sync:
ifeq ($(OS),Windows_NT)
	robocopy results $(FRONTEND)/public/data /MIR /NFL /NDL /NJH /NJS || exit 0
else
	rsync -av --delete results/ $(FRONTEND)/public/data/
endif
	@echo "Synced results/ → $(FRONTEND)/public/data/"

## Full reproducibility run
reproduce: data static results rasters sync
	@echo "DONE — all results regenerated from raw data"

## Clean generated files (keeps raw data)
clean:
	rm -rf results/*.json results/rasters/*.png results/points/
	@echo "Cleaned results/"
