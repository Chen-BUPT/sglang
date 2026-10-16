# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to SGLang project

"""Two-level directory layout for HiCache file pages.

One directory of millions of ``.bin`` pages fills an ext4 htree (ENOSPC while
the disk is not full, then EUCLEAN / dx_probe after a bad index block). Pages
are stored at ``<root>/<aa>/<bb>/<stem>.bin`` (65536 buckets). Readers try that
path first and fall back to a flat ``<root>/<stem>.bin`` left by older builds.
"""

from __future__ import annotations

import hashlib
import os
from typing import Iterator, Optional


def _bucket(stem: str) -> tuple[str, str]:
    digest = hashlib.md5(stem.encode("utf-8")).hexdigest()
    return digest[:2], digest[2:4]


def sharded_bin_path(root: str, stem: str) -> str:
    aa, bb = _bucket(stem)
    return os.path.join(root, aa, bb, f"{stem}.bin")


def flat_bin_path(root: str, stem: str) -> str:
    return os.path.join(root, f"{stem}.bin")


def existing_bin_path(root: str, stem: str) -> Optional[str]:
    """Sharded path if present, otherwise a legacy flat file, otherwise None."""
    sharded = sharded_bin_path(root, stem)
    if os.path.isfile(sharded):
        return sharded
    flat = flat_bin_path(root, stem)
    if os.path.isfile(flat):
        return flat
    return None


def iter_stored_bins(root: str) -> Iterator[tuple[str, str]]:
    """Yield ``(stem, path)`` for flat pages and ``aa/bb`` shards under ``root``."""
    try:
        names = os.listdir(root)
    except FileNotFoundError:
        return
    for name in names:
        path = os.path.join(root, name)
        if name.endswith(".bin") and os.path.isfile(path):
            yield name[:-4], path
            continue
        if len(name) != 2 or not os.path.isdir(path):
            continue
        try:
            mids = os.listdir(path)
        except OSError:
            continue
        for mid in mids:
            if len(mid) != 2:
                continue
            mid_path = os.path.join(path, mid)
            if not os.path.isdir(mid_path):
                continue
            try:
                files = os.listdir(mid_path)
            except OSError:
                continue
            for fn in files:
                if not fn.endswith(".bin"):
                    continue
                fp = os.path.join(mid_path, fn)
                if os.path.isfile(fp):
                    yield fn[:-4], fp
