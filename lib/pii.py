"""
lib/pii.py — PII masking based on user role

PII levels:
  full   — no masking (admin)
  masked — partial masking: names visible, CCCD/SĐT/email masked
  none   — PII columns dropped entirely (sale)
"""
from __future__ import annotations

import pandas as pd

PII_COLS_DROP = [
    "Tên NĐBH", "Ngày sinh NĐBH", "Giới tính NNBH", "CCCD NĐBH",
    "Tên NMBH", "Ngày sinh NMBH", "CCCD NMBH", "Quan hệ",
    "SĐT NMBH", "Email NMBH", "Địa chỉ NMBH",
]


def _mask_id(val: str) -> str:
    s = str(val).strip()
    if not s or s in ("nan", "None", ""):
        return ""
    if len(s) > 4:
        return "*" * (len(s) - 4) + s[-4:]
    return "****"


def _mask_phone(val: str) -> str:
    s = str(val).strip()
    if not s or s in ("nan", "None", ""):
        return ""
    digits = "".join(c for c in s if c.isdigit())
    if len(digits) > 3:
        return "*" * (len(digits) - 3) + digits[-3:]
    return "***"


def _mask_email(val: str) -> str:
    s = str(val).strip()
    if not s or s in ("nan", "None", "") or "@" not in s:
        return ""
    local, domain = s.rsplit("@", 1)
    if len(local) > 2:
        return local[:2] + "***@" + domain
    return "***@" + domain


def _mask_address(val: str) -> str:
    s = str(val).strip()
    if not s or s in ("nan", "None", ""):
        return ""
    parts = s.split(",")
    if len(parts) > 1:
        return "***," + ",".join(parts[-2:])
    if len(s) > 10:
        return "***" + s[-10:]
    return "***"


_MASK_MAP = {
    "CCCD NĐBH": _mask_id,
    "CCCD NMBH": _mask_id,
    "SĐT NMBH": _mask_phone,
    "SĐT sale": _mask_phone,
    "Email NMBH": _mask_email,
    "Địa chỉ NMBH": _mask_address,
}


def strip_pii(df: pd.DataFrame, level: str = "none") -> pd.DataFrame:
    if level == "full":
        return df

    df = df.copy()

    if level == "none":
        cols_to_drop = [c for c in PII_COLS_DROP if c in df.columns]
        if cols_to_drop:
            df = df.drop(columns=cols_to_drop)
        return df

    # level == "masked"
    for col, mask_fn in _MASK_MAP.items():
        if col in df.columns:
            df[col] = df[col].apply(mask_fn)

    return df
