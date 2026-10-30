"""Dynamics: a gentle "glue" compressor, parallel compression for density
and a true-peak limiter.

Gain envelopes are smoothed at a control rate of a few kHz (a short Python
loop for the attack/release logic) and brought back to the sample rate, so
neither needs a compiled extension.
"""

import numpy as np
from scipy import signal
from scipy.ndimage import minimum_filter1d, uniform_filter1d

from bokin_suno.analysis import db, true_peak_envelope


def _blocks(values: np.ndarray, size: int, reduce) -> np.ndarray:
    """reduce() over consecutive blocks of `size` (the last may be shorter)."""
    whole = len(values) // size * size
    out = reduce(values[:whole].reshape(-1, size), axis=1)
    if whole < len(values):
        out = np.append(out, reduce(values[whole:]))
    return out


def _gain_reduction(x: np.ndarray, sr: int, ratio: float, percentile: float, attack_ms: float,
                    release_ms: float, knee_db: float = 6.0):
    """Gain reduction in dB per sample of a feed-forward compressor whose
    threshold is the level the song stays under `percentile` % of the time.
    Also returns the curve per control block and which blocks are not
    silence (for the report), or None for (near) silence."""
    power = np.mean(x ** 2, axis=1)
    a = np.exp(-1 / (0.010 * sr))  # 10 ms RMS detector
    env = signal.lfilter([1 - a], [1, -a], power)
    step = max(1, sr // 1500)
    level = 10 * np.log10(_blocks(env, step, np.max) + 1e-12)
    active = level > level.max() - 40
    if active.sum() < 10:
        return None
    threshold = float(np.percentile(level[active], percentile))
    over = level - threshold
    # static curve with a soft knee: dB of gain reduction
    gr = np.where(over <= -knee_db / 2, 0.0,
                  np.where(over >= knee_db / 2, over * (1 - 1 / ratio),
                           (1 - 1 / ratio) * (over + knee_db / 2) ** 2 / (2 * knee_db)))
    att = 1 - np.exp(-step / (attack_ms / 1000 * sr))
    rel = 1 - np.exp(-step / (release_ms / 1000 * sr))
    smooth = np.empty(len(gr))
    g = 0.0
    for i, target in enumerate(gr.tolist()):
        g += (target - g) * (att if target > g else rel)
        smooth[i] = g
    centres = np.arange(len(smooth)) * step + step / 2
    return np.interp(np.arange(len(x)), centres, smooth), smooth, active


def glue(x: np.ndarray, sr: int, amount: float, attack_ms: float = 30.0,
         release_ms: float = 250.0, knee_db: float = 6.0) -> tuple[np.ndarray, dict]:
    """Bus compression that makes the mix hang together: ratio 1-3:1 with
    `amount` 0-1, threshold set from the song itself (the level the louder
    30% of it reaches), slow attack so drum hits still punch through."""
    stats = {"max_gr_db": 0.0, "avg_gr_db": 0.0}
    if amount <= 0:
        return x, stats
    found = _gain_reduction(x, sr, 1 + 2 * amount, 70, attack_ms, release_ms, knee_db)
    if found is None:
        return x, stats
    gain_db, smooth, active = found
    stats = {"max_gr_db": round(float(smooth.max()), 2),
             "avg_gr_db": round(float(smooth[active].mean()), 2)}
    return x * 10 ** (-gain_db[:, None] / 20), stats


def density(x: np.ndarray, sr: int, amount: float) -> tuple[np.ndarray, dict]:
    """Parallel ("New York") compression: a hard-compressed copy (4:1, fast)
    is mixed under the song, `amount` 0-1 of its level. Quiet details
    (brushes, breaths, soft guitar, reverb tails) come up while loud hits
    keep the attack of the untouched signal: fuller and closer, not squashed."""
    stats = {"detail_lift_db": 0.0, "wet_avg_gr_db": 0.0}
    if amount <= 0:
        return x, stats
    found = _gain_reduction(x, sr, 4.0, 30, attack_ms=5.0, release_ms=120.0)
    if found is None:
        return x, stats
    gain_db, smooth, active = found
    makeup = 10 ** (float(smooth[active].mean()) / 20)  # the copy about as loud as the song
    wet = 10 ** (-gain_db / 20) * (amount * makeup)
    # how much more the quietest parts come up than the loudest (10%) ones
    lift = 20 * np.log10(1 + amount * makeup * 10 ** (-smooth[active] / 20))
    stats = {"detail_lift_db": round(float(lift.max() - np.percentile(lift, 10)), 2),
             "wet_avg_gr_db": round(float(smooth[active].mean()), 2)}
    return x * (1 + wet)[:, None], stats


def limiter_gain(envelope: np.ndarray, sr: int, ceiling_db: float,
                 lookahead_ms: float = 1.5, release_ms: float = 80.0) -> np.ndarray:
    """Gain per sample that keeps envelope * gain under the ceiling.

    need[n] is the gain sample n alone requires. Holding its minimum over the
    next 2L samples, then averaging twice over L samples, gives a smooth
    S-shaped attack that is never above need[n]: every value averaged into
    gain[n] held a window that contains n. Release (gain coming back up) is
    a one-pole curve on the held minimum, at a control rate of a few kHz.
    """
    ceiling = 10 ** (ceiling_db / 20)
    need = np.minimum(1.0, ceiling / np.maximum(envelope, 1e-12))
    if need.min() >= 1.0:
        return need
    L = max(1, int(round(lookahead_ms / 1000 * sr)))
    held = minimum_filter1d(need, 2 * L, origin=-L, mode="nearest")  # min over [n, n + 2L)
    step = max(1, min(L, sr // 3000))
    blocks = _blocks(held, step, np.min)
    coef = 1 - np.exp(-step / (release_ms / 1000 * sr))
    released = np.empty(len(blocks))
    g = 1.0
    for i, h in enumerate(blocks.tolist()):
        g = h if h < g else g + (h - g) * coef
        released[i] = g
    gain = np.repeat(released, step)[:len(need)]
    for _ in range(2):  # causal moving average over [n - L + 1, n]
        gain = uniform_filter1d(gain, L, origin=(L - 1) // 2, mode="nearest")
    return np.minimum(gain, 1.0)


def limit(x: np.ndarray, sr: int, ceiling_db: float = -1.0, gain: float = 1.0,
          envelope: np.ndarray | None = None, **kwargs) -> tuple[np.ndarray, dict]:
    """x * gain, true-peak limited to ceiling_db (dBTP). envelope is x's
    true_peak_envelope, when already known."""
    if envelope is None:
        envelope = true_peak_envelope(x)
    g = limiter_gain(envelope * gain, sr, ceiling_db, **kwargs)
    y = x * (gain * g)[:, None]
    # Gain changes can nudge a peak between samples a hair over: one more
    # pass on the result, then a last trim if anything is still above.
    tp = true_peak_envelope(y)
    top = db(float(tp.max()))
    if top > ceiling_db + 0.01:
        g2 = limiter_gain(tp, sr, ceiling_db - 0.05, **kwargs)
        y *= g2[:, None]
        g *= g2
        top = db(float(true_peak_envelope(y).max()))
        if top > ceiling_db:
            y *= 10 ** ((ceiling_db - top) / 20)
            top = ceiling_db
    reduction = -20 * np.log10(np.maximum(g, 1e-12))
    stats = {"max_gr_db": round(float(reduction.max()), 2),
             "limited_pct": round(100 * float(np.count_nonzero(reduction > 0.05)) / len(g), 1),
             "true_peak_db": round(top, 2)}
    return y, stats
