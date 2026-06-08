"""BarkerLink RP2040 bring-up + characterization (MicroPython).

Run on the Tiny Tapeout carrier RP2040:
  1. read ID (expect 0x424C0100),
  2. internal-loopback a known packet and verify,
  3. BER sweep vs the on-chip noise injector -> compare to model/ber_curve.csv & PREDICTIONS.

    >>> import bringup; bringup.main()
"""
import barkerlink as bl


def check_id(dev):
    val = dev.ident()
    print("ID = 0x%08X %s" % (val, "OK" if val == 0x424C0100 else "FAIL"))
    return val == 0x424C0100


def loopback_demo(dev, payload=b"BarkerLink!"):
    dev.tx_frame(payload, loopback=True)
    got = dev.rx_drain(len(payload))
    ok = got == payload
    print("loopback %r -> %r  %s" % (payload, got, "OK" if ok else "FAIL"))
    return ok


def ber_sweep(dev, probs=(0x0400, 0x0800, 0x1000, 0x2000, 0x3000),
              frames=200, payload=None):
    payload = payload or bytes(range(32))
    print("p_chip(Q16)   BER")
    for p in probs:
        errs = bits = 0
        for _ in range(frames):
            dev.tx_frame(payload, loopback=True, noise_prob=p)
            got = dev.rx_drain(len(payload))
            for i in range(min(len(got), len(payload))):
                errs += bin(got[i] ^ payload[i]).count("1")
            bits += len(payload) * 8
        print("  %5d      %.3e" % (p, errs / bits if bits else 0.0))


def main():
    dev = bl.make()
    if not check_id(dev):
        return
    loopback_demo(dev)
    ber_sweep(dev)


if __name__ == "__main__":
    main()
