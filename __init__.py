import numpy as np
import json


def xy_to_rphi(x, y):
    # NOTE: Axes rotated by 90 CCW by intent, so tat 0 is top.
    return np.hypot(x, y), np.arctan2(-x, y)


def rphi_to_xy(r, phi):
    return r * -np.sin(phi), r * np.cos(phi)


def scan_to_xy(scan, thresh=None, laserFoV=np.radians(225)):
    s = np.array(scan, copy=True)
    if thresh is not None:
        s[s > thresh] = np.nan
    angles = np.linspace(-laserFoV/2, laserFoV/2, len(scan))
    return rphi_to_xy(s, angles)


def load_scan(fname):
    data = np.genfromtxt(fname, delimiter=",")
    seqs, scans = data[:,0].astype(np.uint32), data[:,1:-1]
    return seqs, scans


def load_dets(name):
    def _doload(fname):
        seqs, dets = [], []
        with open(fname) as f:
            for line in f:
                seq, tail = line.split(',', 1)
                seqs.append(int(seq))
                dets.append(json.loads(tail))
        return seqs, dets

    s1, wcs = _doload(name + ".wc")
    s2, was = _doload(name + ".wa")

    assert all(a == b for a, b in zip(s1, s2)), "Uhhhh?"
    return s1, wcs, was


def precrec_unvoted(preds, gts, radius, pred_rphi=False, gt_rphi=False):
    """
    The "unvoted" precision/recall, meaning that multiple predictions for the same ground-truth are NOT penalized.

    - `preds` an iterable (scans) of iterables (per scan) containing predicted x/y or r/phi pairs.
    - `gts` an iterable (scans) of iterables (per scan) containing ground-truth x/y or r/phi pairs.
    - `radius` the cutoff-radius for "correct", in meters.
    - `pred_rphi` whether `preds` is r/phi (True) or x/y (False).
    - `gt_rphi` whether `gts` is r/phi (True) or x/y (False).

    Returns a pair of numbers: (precision, recall)
    """
    npred, npred_hit, ngt, ngt_hit = 0, 0, 0, 0
    for ps, gts in zip(preds, gts):
        # Distance between each ground-truth and predictions
        assoc = np.zeros((len(gts), len(ps)))

        for ip, p in enumerate(ps):
            for igt, gt in enumerate(gts):
                px, py = rphi_to_xy(*p) if pred_rphi else p
                gx, gy = rphi_to_xy(*gt) if pred_rphi else gt
                assoc[igt, ip] = np.hypot(px-gx, py-gy)

        # Now cutting it off at `radius`, we can get all we need.
        assoc = assoc < radius
        npred += len(ps)
        npred_hit += np.count_nonzero(np.sum(assoc, axis=0))
        ngt += len(gts)
        ngt_hit += np.count_nonzero(np.sum(assoc, axis=1))

    return (
        npred_hit/npred if npred > 0 else np.nan,
          ngt_hit/ngt   if   ngt > 0 else np.nan
    )