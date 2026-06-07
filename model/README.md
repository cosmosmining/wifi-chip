# model/ — Python fixed-point golden model

**The golden model is law** (see `CLAUDE.md`). It is the bit-accurate reference the RTL
is checked against in lockstep. It is **never** edited to make a failing RTL test pass —
the spec arbitrates disagreements, and any model change cites a spec section and a
`DECISIONS.md` entry.

Lands in **Phase 1**:
- `barkerlink_model.py` — fixed-point TX (scrambler/DBPSK/DQPSK/Barker spread) and RX
  (soft correlator/peak/demod/descramble) + PLCP framing.
- `test_model.py` — model unit tests (golden vectors, scrambler inverse, CRC, etc.).
- `ber_theory.py` — theoretical DBPSK/DQPSK BER curves + plots used as the DV acceptance
  band (±1 dB-equivalent) and pre-registered in `PREDICTIONS.md` (Phase 7).

Install: `pip install -r model/requirements.txt`.
