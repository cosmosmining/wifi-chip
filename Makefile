# BarkerLink - reproduce every result from a clean clone.
# Phase 0: smoke / lint / sim / synth are live. regress / cov / formal / dft /
# harden / sweep / predict are honest stubs tagged with the phase that fills them.
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.ONESHELL:
.DEFAULT_GOAL := help

# ---- layout ----------------------------------------------------------------
TOP        := tt_um_barkerlink
RTL_CORE   := $(wildcard rtl/core/*.v)
RTL_TOP    := $(wildcard rtl/tt_top/*.v)
RTL        := $(RTL_CORE) $(RTL_TOP)
BUILD      := build

# ---- tools (detected; CI provides what this sandbox cannot install) --------
VERILATOR  := $(shell command -v verilator 2>/dev/null)
IVERILOG   := $(shell command -v iverilog 2>/dev/null)
VERIBLE    := $(shell command -v verible-verilog-lint 2>/dev/null)
YOSYS      := $(shell command -v yosys 2>/dev/null)
SBY        := $(shell command -v sby 2>/dev/null)
PYTHON     := python3
PYTEST     := python3 -m pytest

.PHONY: help tools lint sim smoke model ber regs regress cov formal synth dft \
        harden sweep predict metrics clean

help: ## list targets
	@echo "BarkerLink make targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | sort | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-9s\033[0m %s\n",$$1,$$2}'

tools: ## report detected toolchain
	@echo "verilator : $(or $(VERILATOR),MISSING)"
	@echo "iverilog  : $(or $(IVERILOG),MISSING)"
	@echo "verible   : $(or $(VERIBLE),MISSING - enforced in CI)"
	@echo "yosys     : $(or $(YOSYS),MISSING)"
	@echo "sby       : $(or $(SBY),MISSING - enforced in CI)"
	@echo "cocotb    : $$($(PYTHON) -c 'import cocotb;print(cocotb.__version__)' 2>/dev/null || echo MISSING)"

lint: ## RTL lint, zero-warning gate (verilator; verible if present)
	@test -n "$(VERILATOR)" || { echo "verilator missing - cannot lint"; exit 1; }
	mkdir -p $(BUILD)
	echo ">> verilator --lint-only -Wall (zero-warning gate)"
	$(VERILATOR) --lint-only -Wall --top-module $(TOP) $(RTL) 2>&1 | tee $(BUILD)/lint.log
	if grep -qE '%(Warning|Error)' $(BUILD)/lint.log; then \
	  echo "LINT FAIL: warnings/errors above are not waived"; exit 1; fi
	if [ -n "$(VERIBLE)" ]; then \
	  echo ">> verible-verilog-lint"; \
	  $(VERIBLE) --rules_config=dv/lint/verible.rules $(RTL); \
	else echo ">> verible not installed locally (enforced in CI)"; fi
	echo "LINT CLEAN"

smoke: lint ## lint + hello-world cocotb/Icarus sim (Phase 0 gate)
	@test -n "$(IVERILOG)" || { echo "iverilog missing - cannot sim"; exit 1; }
	echo ">> smoke sim (cocotb + Icarus)"
	$(PYTEST) -q dv/cocotb/test_smoke.py
	echo "SMOKE PASS"

sim: ## run the full cocotb bench suite
	@test -n "$(IVERILOG)" || { echo "iverilog missing - cannot sim"; exit 1; }
	$(PYTEST) -q dv/cocotb

model: ## run the Python golden-model unit tests
	$(PYTEST) -q model

ber: ## (re)generate the theoretical BER curve (docs/img/ber_dbpsk.png + csv)
	$(PYTHON) model/ber_theory.py

regs: ## validate regs/barkerlink.rdl + regenerate CSR block / C header / HTML
	@command -v peakrdl >/dev/null || { echo "peakrdl missing (pip install peakrdl)"; exit 0; }
	mkdir -p build/regs
	peakrdl dump     regs/barkerlink.rdl
	peakrdl regblock regs/barkerlink.rdl -o build/regs/regblock --cpuif apb3
	peakrdl c-header regs/barkerlink.rdl -o build/regs/barkerlink_regs.h
	peakrdl html     regs/barkerlink.rdl -o build/regs/html
	@echo "regs generated under build/regs/ (CSR block integrated in Phase 2)"

synth: ## generic Yosys elaborate + cell-count (synthesizability check)
	@test -n "$(YOSYS)" || { echo "yosys missing (CI provides it)"; exit 0; }
	mkdir -p $(BUILD)
	$(YOSYS) -q -l $(BUILD)/synth.log synth/synth.ys
	echo ">> generic cell estimate (sky130 mapping happens in Phase 7):"
	grep -E "Number of cells" $(BUILD)/synth.log | tail -1 || true

regress: ## [Phase 3] constrained-random regression (>=500 seeds)
	@echo "[stub] regress: constrained-random + functional coverage closure lands in Phase 3."

cov: ## [Phase 3] merge + report functional/code coverage
	@echo "[stub] cov: coverage collection/report lands in Phase 3."

formal: ## [Phase 4] SymbiYosys safety proofs (FIFO/FSM/scrambler)
	@echo "[stub] formal: SymbiYosys proofs land in Phase 4 (sby=$${SBY:-not installed})."

dft: ## [Phase 6] Fault scan insertion + ATPG
	@echo "[stub] dft: scan + ATPG (Fault) lands in Phase 6."

harden: ## [Phase 7] LibreLane/ORFS hardening
	@echo "[stub] harden: RTL->GDS hardening lands in Phase 7."

sweep: ## [Phase 7] DSE sweep (util x clk x density)
	@echo "[stub] sweep: parallel DSE sweep lands in Phase 7."

predict: ## [Phase 7] freeze PREDICTIONS.md from STA/area/BER
	@echo "[stub] predict: pre-registered predictions land in Phase 7."

metrics: ## parse logs -> summary.json -> append METRICS.md row
	$(PYTHON) scripts/metrics.py

clean: ## remove build artifacts
	rm -rf $(BUILD) dv/cocotb/sim_build **/__pycache__ .pytest_cache
	@echo "cleaned"
