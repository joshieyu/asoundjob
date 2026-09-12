import math

def curve(fx, fy, t0, t1, segs=64, eps=1e-4):
    """Cubic path through a parametric curve using numeric tangents."""
    pts, tans = [], []
    h = (t1 - t0) / segs
    for i in range(segs + 1):
        t = t0 + h * i
        pts.append((fx(t), fy(t)))
        dx = (fx(t + eps) - fx(t - eps)) / (2 * eps) * h
        dy = (fy(t + eps) - fy(t - eps)) / (2 * eps) * h
        tans.append((dx, dy))
    d = f"M{pts[0][0]:.2f} {pts[0][1]:.2f}"
    for i in range(len(pts) - 1):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        (a, b), (c, e) = tans[i], tans[i + 1]
        d += (f"C{x0+a/3:.2f} {y0+b/3:.2f} {x1-c/3:.2f} {y1-e/3:.2f} {x1:.2f} {y1:.2f}")
    return d

def sinc(u):
    if abs(u) < 1e-9: return 1.0
    return math.sin(u) / u

def dirichlet(u, n):
    s = math.sin(u / 2)
    if abs(s) < 1e-9: return 2 * n + 1
    return math.sin((n + 0.5) * u) / s

def sinc_h(x0, width, ybase, height, lobes=3.5, fn=None):
    """sinc running left-to-right; peak at centre, apex height = `height`."""
    fn = fn or sinc
    U = lobes * math.pi
    peak = fn(0.0)
    return curve(lambda t: x0 + width * (t + U) / (2 * U),
                 lambda t: ybase - height * fn(t) / peak,
                 -U, U, segs=int(24 * lobes))

def sinc_left(x0, width, ybase, height, lobes=3.5, fn=None):
    """Left half only — oscillations rising into the peak."""
    fn = fn or sinc
    U = lobes * math.pi
    peak = fn(0.0)
    return curve(lambda t: x0 + width * (t + U) / U,
                 lambda t: ybase - height * fn(t) / peak,
                 -U, 0.0, segs=int(24 * lobes))


# --- ASJ wordmark, as shipped -------------------------------------------------
# The A's side lobes dip DIP below the baseline, so the true vertical extent is
# peak .. baseline + DIP*peak. Align the S to that, not to the baseline, or it
# sits high; and centre that whole span, not the baseline, or the mark rides low.
DIP = 0.2172


def layout(peak=100, canvas_h=170):
    span = peak * (1 + DIP)
    top = (canvas_h - span) / 2
    return top, top + peak, span          # top, baseline, span


def A_sinc(x0, width, baseline, peak, lobes=1.5):
    import math
    U = lobes * math.pi
    return curve(lambda t: x0 + width * (t + U) / (2 * U),
                 lambda t: baseline - peak * sinc(t), -U, U, segs=54)


def J_sinc(x0, width, baseline, peak, left=2.5, past=0.30):
    """The A's left half, same orientation. left>=2.3 clears the trough so the
    terminal hooks back UP; at 1.5 it stops dead at the bottom of the lobe."""
    import math
    t0, t1 = -left * math.pi, past * math.pi
    return curve(lambda t: x0 + width * (t - t0) / (t1 - t0),
                 lambda t: baseline - peak * sinc(t), t0, t1, segs=64)


def S_sym(top, span, xcen, amp, flare=0.45):
    """One period extended symmetrically at both ends; span must match the A's
    full extent (peak .. lobe bottom), not just peak .. baseline."""
    import math
    t0, t1 = -flare, 2 * math.pi + flare
    return curve(lambda t: xcen + amp * math.sin(t + math.pi),
                 lambda t: top + span * (t - t0) / (t1 - t0), t0, t1, segs=64)
