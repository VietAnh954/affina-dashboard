"""
================================================================================
 BUILD DASHBOARD DATA — Chạy hàng ngày 10:00 VN qua GitHub Actions
================================================================================

Mục tiêu:
    1. Tải dữ liệu nguồn từ Google Drive (Sheet Cấp đơn + 2 Excel)
    2. Làm sạch + chuẩn hóa (logic từ 3 notebook gốc)
    3. Push 3 bảng nguồn lên Supabase (qd1, ds_nhan_su_affina, union_all_data_cap_don)
    4. Chạy DuckDB queries CORE + NEO + TSA (logic từ File 3 gốc — full 3 năm)
    5. Combine → df_master (bao gồm subtotal rows)
    6. Push df_master lên bảng MỚI dashboard_master_data
    7. Cập nhật bảng dashboard_meta (last_update, row_count, ...)

Environment variables (GitHub Secrets hoặc .env local):
    - SUPABASE_DB_URI
    - GOOGLE_CLIENT_ID
    - GOOGLE_CLIENT_SECRET
    - GOOGLE_REFRESH_TOKEN

Author: Senior Data Engineer for VietAnh @ Affina
================================================================================
"""

import io
import os
import re
import sys
import time
import unicodedata
import warnings
from datetime import datetime, timezone, timedelta

import duckdb
import pandas as pd
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from sqlalchemy import create_engine, text

# ==================== .env cho local dev ====================
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # trên GitHub Actions không cần dotenv

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)


# ============================================================================
# 1. CONFIG
# ============================================================================
SHEET_FILE_ID = "1qc_QhrvpoLLp6w9RkGBEkm8qBO49GJE8oMlwkCdJOsk"  # Google Sheet Cấp đơn

DSNS_FILE_NAME  = "DSNS CTV sale Affina NEW - HR NHẬP.xlsx"
QUYDOI_FILE_NAME = "26_02_04_sửa ngày_quy_doi_all.xlsx"

# Time range cho dashboard: full 3 năm (giống File 1 & File 3 gốc)
START_YEAR = 2024
END_YEAR   = 2026

# Env
SUPABASE_DB_URI      = os.environ.get("SUPABASE_DB_URI")
GOOGLE_CLIENT_ID     = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
GOOGLE_REFRESH_TOKEN = os.environ.get("GOOGLE_REFRESH_TOKEN")

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]

# ANSI logging (không dùng emoji để tránh lỗi encoding Windows)
def log(msg: str) -> None:
    ts = datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def _validate_env() -> None:
    missing = [k for k, v in {
        "SUPABASE_DB_URI":      SUPABASE_DB_URI,
        "GOOGLE_CLIENT_ID":     GOOGLE_CLIENT_ID,
        "GOOGLE_CLIENT_SECRET": GOOGLE_CLIENT_SECRET,
        "GOOGLE_REFRESH_TOKEN": GOOGLE_REFRESH_TOKEN,
    }.items() if not v]
    if missing:
        log(f"[ERROR] Thiếu env: {missing}")
        sys.exit(1)


# ============================================================================
# 2. GOOGLE DRIVE HELPERS (OAuth Refresh Token — không dùng Service Account)
# ============================================================================
def get_drive_service():
    creds = Credentials(
        token=None,
        refresh_token=GOOGLE_REFRESH_TOKEN,
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
    )
    creds.refresh(Request())
    return build("drive", "v3", credentials=creds)


def find_file_in_drive(drive_service, file_name: str, parent_folder_name: str | None = None):
    """Tìm file theo tên, ưu tiên trong folder cụ thể, fallback tìm toàn Drive."""
    query = f"name = '{file_name}' and trashed = false"
    if parent_folder_name:
        folder_res = drive_service.files().list(
            q=f"name = '{parent_folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false",
            fields="files(id, name)",
        ).execute()
        folders = folder_res.get("files", [])
        if folders:
            query += f" and '{folders[0]['id']}' in parents"

    res = drive_service.files().list(q=query, fields="files(id, name)", pageSize=10).execute()
    files = res.get("files", [])
    if not files and parent_folder_name:
        # fallback: tìm toàn Drive
        log(f"  Không thấy '{file_name}' trong folder '{parent_folder_name}', tìm toàn Drive...")
        return find_file_in_drive(drive_service, file_name, None)
    return files[0]["id"] if files else None


def download_binary(drive_service, file_id: str) -> bytes:
    request = drive_service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return fh.getvalue()


def download_sheet_as_xlsx(drive_service, file_id: str) -> bytes:
    request = drive_service.files().export_media(
        fileId=file_id,
        mimeType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return fh.getvalue()


# ============================================================================
# 3. DATA CLEANING FUNCTIONS (copy y nguyên từ notebook gốc)
# ============================================================================
def standardize_date_format(date_value):
    if pd.isna(date_value):
        return None
    date_str = str(date_value).strip()
    if date_str in ["None", "nan", "", "NaT"]:
        return None
    try:
        match = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", date_str)
        if match:
            year, p1, p2 = match.groups()
            if int(p1) > 12 and int(p2) <= 12:
                try:
                    return pd.to_datetime(f"{year}-{p2.zfill(2)}-{p1.zfill(2)}",
                                          format="%Y-%m-%d").strftime("%Y-%m-%d")
                except Exception:
                    return date_str
            return date_str[:10]
        if "/" in date_str:
            parts = date_str.split("/")
            if len(parts) == 3:
                p1, p2, p3 = [p.strip() for p in parts]
                if len(p3) >= 3 or (p3.isdigit() and int(p3) > 31):
                    m, d, y = p1, p2, p3
                elif len(p1) >= 3 or (p1.isdigit() and int(p1) > 31):
                    y, m, d = p1, p2, p3
                else:
                    m, d, y = p1, p2, p3
                y = (f"20{y}" if len(y) == 2 and int(y) <= 30 else
                     f"19{y}" if len(y) == 2 else
                     f"20{y[1:]}" if len(y) == 3 else
                     f"202{y}" if len(y) == 1 else y)
                try:
                    return pd.to_datetime(f"{y.zfill(4)}-{m.zfill(2)}-{d.zfill(2)}",
                                          format="%Y-%m-%d").strftime("%Y-%m-%d")
                except Exception:
                    try:
                        return pd.to_datetime(f"{y.zfill(4)}-{d.zfill(2)}-{m.zfill(2)}",
                                              format="%Y-%m-%d").strftime("%Y-%m-%d")
                    except Exception:
                        return date_str
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            parsed = pd.to_datetime(date_str, dayfirst=False, errors="coerce")
            if pd.notna(parsed) and parsed.year > 1900:
                return parsed.strftime("%Y-%m-%d")
    except Exception:
        return date_str
    return date_str


def clean_currency_column(series):
    series_str = series.astype(str).str.replace(r"[^\d,\.]", "", regex=True).str.strip()
    mask_vn = series_str.str.contains(r"\.") & series_str.str.contains(",")
    series_str[mask_vn] = series_str[mask_vn].str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    mask_comma_only = (~series_str.str.contains(r"\.")) & series_str.str.contains(",")
    series_str[mask_comma_only] = series_str[mask_comma_only].str.replace(",", ".", regex=False)
    mask_multi_dot = series_str.str.count(r"\.") > 1
    if mask_multi_dot.any():
        def fix_multi_dot(x):
            if not isinstance(x, str):
                return x
            parts = x.split(".")
            return ("".join(parts[:-1]) + "." + parts[-1]
                    if len(parts[-1]) <= 2 and all(p.isdigit() for p in parts[:-1])
                    else x.replace(".", ""))
        series_str[mask_multi_dot] = series_str[mask_multi_dot].apply(fix_multi_dot)
    mask_single_dot = series_str.str.count(r"\.") == 1
    series_str[mask_single_dot] = series_str[mask_single_dot].apply(
        lambda x: x if isinstance(x, str) and len(x.split(".")[1]) <= 2
        else x.replace(".", "") if isinstance(x, str) else x
    )
    num = pd.to_numeric(series_str, errors="coerce")
    return num.apply(lambda x: x * 1000 if pd.notna(x) and x < 1000 else x).round(0).astype("Int64")


def clean_whitespace(df):
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = (df[col].astype(str)
                       .str.replace(r"[\n\r\t]+", "", regex=True)
                       .str.replace(r"\s{2,}", " ", regex=True)
                       .str.strip())
    return df


def clean_contract(value):
    if pd.isna(value):
        return value
    return re.sub(r"\s+", " ",
                  re.sub(r"[⁄/]", "/",
                         re.sub(r"[–—−-]", "-",
                                unicodedata.normalize("NFC", str(value))))).strip()


def convert_channel(val):
    val_str = str(val).strip()
    if val_str in ["Core Agency", "core Agency", "Standard"]:
        return "Core Agency"
    if val_str in ["CTV_TSA (TSA 2)", "CTV_TSA (TSA2)"]:
        return "CTV_TSA (TSA 2)"
    if val_str in ["Elite", "H.O", "Neo", "TSA"]:
        return val_str
    return "Core Agency"


# ============================================================================
# 4. LOAD & CLEAN 3 NGUỒN DATA
# ============================================================================
def load_all_sources(drive_service):
    log("[Step 2] Đang tải data từ Google Drive...")

    # 4.1 Google Sheet Cấp đơn
    log(f"  - Tải Google Sheet ID {SHEET_FILE_ID[:15]}... (Cấp đơn)")
    sheet_bytes = download_sheet_as_xlsx(drive_service, SHEET_FILE_ID)

    # 4.2 DSNS
    dsns_id = find_file_in_drive(drive_service, DSNS_FILE_NAME, "Data")
    if not dsns_id:
        dsns_id = find_file_in_drive(drive_service, DSNS_FILE_NAME, "Nhân sự sales")
    if not dsns_id:
        raise FileNotFoundError(f"Không tìm thấy file '{DSNS_FILE_NAME}' trên Google Drive")
    log(f"  - Tải DSNS (id={dsns_id[:10]}...)")
    dsns_bytes = download_binary(drive_service, dsns_id)

    # 4.3 Quy đổi
    qd_id = find_file_in_drive(drive_service, QUYDOI_FILE_NAME, "Data")
    if not qd_id:
        raise FileNotFoundError(f"Không tìm thấy file '{QUYDOI_FILE_NAME}' trên Google Drive")
    log(f"  - Tải Quy đổi (id={qd_id[:10]}...)")
    qd_bytes = download_binary(drive_service, qd_id)

    log("  [OK] Đã tải xong 3 nguồn data")
    return io.BytesIO(sheet_bytes), io.BytesIO(dsns_bytes), io.BytesIO(qd_bytes)


def clean_data(sheet_io, dsns_io, qd_io):
    """Trả về (df_ns, qd1, df_union) — logic giữ nguyên từ File 3 gốc."""
    log("[Step 3] Đang làm sạch data...")

    # 4.1 Quy đổi
    qd1 = pd.read_excel(qd_io, sheet_name="Updating")

    # 4.2 Nhân sự
    df_ns = pd.read_excel(dsns_io, dtype=str, sheet_name="DSNS AGENCY 2025").dropna(subset=["Họ tên"])
    df_ns = clean_whitespace(df_ns)
    df_ns["Channel"] = df_ns["Channal"].apply(convert_channel)
    for c in ["Thời gian bắt đầu", "Ngày hiệu lực chức danh", "Ngày Sinh"]:
        if c in df_ns.columns:
            df_ns[c] = df_ns[c].apply(standardize_date_format)
    df_ns["Điện thoại"] = df_ns["Điện thoại"].apply(
        lambda x: str(x).lstrip("0") if pd.notna(x) and str(x) != "nan" else x)
    df_ns["Người giới thiệu"] = df_ns["Người giới thiệu"].apply(
        lambda x: str(x).lstrip("0") if pd.notna(x) and str(x) != "nan" else x)

    # 4.3 Cấp đơn — 7 sheet (giữ nguyên logic từ notebook)
    # BHSK
    df_BHSK = pd.read_excel(sheet_io, sheet_name="Sức khỏe", header=None, skiprows=5)
    bhsk_cols = [
        "Ngày update", "STT", "Tên Người được BH", "Ngày Sinh", "Giới tính", "Email",
        "Số hộ chiếu", "CMND", "ĐỊA CHỈ", "Tên", "Quan hệ", "Ngày sinh người mua Bảo hiểm",
        "Số CMND_CCCD NMBH", "Số điện thoại NMBH", "Địa chỉ NMBH", "Email NMBH",
        "Chương trình bảo hiểm", "Ngoại trú", "Nha khoa", "Thai sản", "Topup",
        "Phí bảo hiểm", "Giảm phí_refund", "Giảm phí_deduct", "Tổng giảm phí",
        "Số tiền thanh toán", "Ngày thanh toán", "Ngày bắt đầu", "Ngày kết thúc",
        "Số Giấy Chứng Nhận", "Số hợp đồng", "Thông tin xuất hoá đơn",
        "Phí điều chỉnh ( Nếu có)", "Giảm phí ( Nếu có)", "Nguyên nhân (Nếu có)",
        "Lead ID (nếu có)", "Phone trên lead", "Code sale", "Phone Khách hàng",
        "Tên liên hệ", "Người giới thiệu", "Hình thức thanh toán", "Note",
        "Đối tác nhà bảo hiểm", "Sản phẩm", "Channel", "Mã hợp đồng Affina",
        "Đã gửi mail cho khách", "Nộp claim", "Ủy quyền bồi thường (Nếu có)"
    ]
    df_BHSK.columns = (bhsk_cols[:len(df_BHSK.columns)] +
                       [f"C_{i}" for i in range(len(df_BHSK.columns) - len(bhsk_cols))]
                       if len(df_BHSK.columns) > len(bhsk_cols)
                       else bhsk_cols[:len(df_BHSK.columns)])
    df_BHSK["Loại bảo hiểm"] = "BHSK"
    df_BHSK = df_BHSK.rename(columns={
        "Tên": "Tên NMBH",
        "Giới tính": "Giới tính NNBH",
        "Ngày sinh người mua Bảo hiểm": "Ngày sinh NMBH",
        "Ngày Sinh": "Ngày Sinh NNBH",
        "Chương trình bảo hiểm": "Gói bảo hiểm",
        "CMND": "CCCD",
    })
    keep_bhsk = [
        "STT", "Ngày thanh toán", "Code sale", "Sản phẩm", "Quan hệ", "Gói bảo hiểm",
        "Ngoại trú", "Nha khoa", "Thai sản", "Topup", "Đối tác nhà bảo hiểm",
        "Số CMND_CCCD NMBH", "Số tiền thanh toán", "Channel", "Tên Người được BH",
        "Số hộ chiếu", "CCCD", "Ngày Sinh NNBH", "Giới tính NNBH", "Địa chỉ NMBH",
        "Phone Khách hàng", "Email", "Ngày bắt đầu", "Ngày kết thúc", "Loại bảo hiểm",
        "Số hợp đồng", "Tên NMBH", "Ngày sinh NMBH", "Địa chỉ"
    ]
    df_BHSK = df_BHSK[[c for c in keep_bhsk if c in df_BHSK.columns]]

    # BHXM
    sheet_io.seek(0)
    df_BHXM = pd.read_excel(sheet_io, sheet_name="Thông tin cấp Bảo hiểm xe máy",
                            header=None, skiprows=2).dropna(subset=[0])
    df_BHXM.columns = [
        "Ngày update", "STT", "BIỂN SỐ XE", "SỐ KHUNG", "SỐ MÁY", "TÊN KHÁCH HÀNG",
        "PHÍ BẢO HIỂM TNDS BẮT BUỘC", "PHÍ BẢO HIỂM TAI NẠN NNTX", "SỐ NĂM",
        "TỔNG PHÍ BẢO HIỂM", "NGÀY CẤP ĐƠN", "NGÀY BẮT ĐẦU", "NGÀY KẾT THÚC",
        "LOẠI XE", "NHÃN HIỆU XE", "SỐ ĐIẸN THOẠI", "Email", "Chương trình",
        "Code sale", "Hình thức thanh toán", "Đối tác nhà bảo hiểm", "Sản phẩm",
        "Channel", "Số hợp đồng", "Note"
    ][:len(df_BHXM.columns)]
    keep_bhxm = [
        "Ngày update", "Code sale", "Chương trình", "Đối tác nhà bảo hiểm",
        "TỔNG PHÍ BẢO HIỂM", "Channel", "TÊN KHÁCH HÀNG", "NGÀY BẮT ĐẦU",
        "NGÀY KẾT THÚC", "Số hợp đồng", "BIỂN SỐ XE"
    ]
    df_BHXM_done = df_BHXM[[c for c in keep_bhxm if c in df_BHXM.columns]].copy()
    if not df_BHXM_done.empty:
        df_BHXM_done.columns = [
            "Ngày thanh toán", "Code sale", "Sản phẩm", "Đối tác nhà bảo hiểm",
            "Số tiền thanh toán", "Channel", "Tên Người được BH", "Ngày bắt đầu",
            "Ngày kết thúc", "Số hợp đồng", "Biển số xe"
        ]
        df_BHXM_done["Loại bảo hiểm"] = "BHXM"

    # BHYT
    sheet_io.seek(0)
    df_BHYT = pd.read_excel(sheet_io, sheet_name="BHYTBHXH", skiprows=1,
                            dtype={"Số tiền thanh toán": str})
    col_c, new_c = {}, []
    for c in df_BHYT.columns:
        b = c.split(".")[0]
        if b not in col_c:
            col_c[b] = 0
            new_c.append(b)
        else:
            col_c[b] += 1
            mapping = {
                "Ngày sinh": "Ngày sinh NMBH",
                "CCCD": "CCCD NMBH",
                "Địa chỉ": "Địa chỉ NMBH",
                "SĐT": "SĐT NMBH",
                "Email": "Email NMBH",
                "Sản phẩm": "Sản phẩm 2",
            }
            new_c.append(mapping.get(b, f"{b}_{col_c[b]}") if col_c[b] == 1 else f"{b}_{col_c[b]}")
    df_BHYT.columns = new_c
    df_BHYT["Loại bảo hiểm"] = "BHYT/BHXH"
    df_BHYT = df_BHYT.rename(columns={
        "Họ tên NĐBH": "Tên Người được BH",
        "Họ tên BMBH": "Tên NMBH",
        "Ngày sinh": "Ngày Sinh NNBH",
        "Code sales": "Code sale",
        "Đối tác NBH": "Đối tác nhà bảo hiểm",
        "Mã tờ khai": "Số hợp đồng",
        "Phí Bảo hiểm": "Số tiền thanh toán",
        "Ngày duyệt": "Ngày thanh toán",
        "Ngày thanh toán": "Ngày thanh toán (real)",
        "Giới tính": "Giới tính NNBH",
    })
    keep_bhyt = [
        "STT", "Ngày thanh toán", "Code sale", "Sản phẩm", "Đối tác nhà bảo hiểm",
        "Số tiền thanh toán", "Channel", "Tên Người được BH", "Ngày Sinh NNBH",
        "Giới tính NNBH", "CCCD", "Địa chỉ", "SĐT", "Email", "Phone Khách hàng",
        "Ngày bắt đầu", "Ngày kết thúc", "Loại bảo hiểm", "Số hợp đồng", "Tên NMBH",
        "Ngày sinh NMBH", "CCCD NMBH", "Địa chỉ NMBH", "SĐT NMBH", "Email NMBH",
        "Mã BHYT", "Mã BHXH", "Trạng thái", "Ngày thanh toán (real)", "Ngày hoàn phí",
        "Phương án thù lao", "Phí Bảo hiểm", "Thời hạn BH", "Số GCN", "Tên liên hệ",
        "Hình thức thanh toán"
    ]
    df_BHYT_done = df_BHYT[[c for c in keep_bhyt if c in df_BHYT.columns]]
    if "Phí Bảo hiểm" in df_BHYT_done.columns:
        df_BHYT_done.loc[:, "Số tiền thanh toán"] = df_BHYT_done["Phí Bảo hiểm"]

    # BHOTO
    sheet_io.seek(0)
    df_BHOTO = pd.read_excel(sheet_io, sheet_name="Bao hiem oto", dtype={"Số tiền": str})
    df_BHOTO_done = df_BHOTO[[
        "Ngày thanh toán", "Code sale", "Chương trình", "Đối tác nhà bảo hiểm",
        "Số tiền", "Channel", "Tên khách hàng", "Số GCN", "Biển số",
        "Ngày bắt đầu hiệu lực", "Ngày kết thúc hiệu lực"
    ]].copy()
    df_BHOTO_done.columns = [
        "Ngày thanh toán", "Code sale", "Sản phẩm", "Đối tác nhà bảo hiểm",
        "Số tiền thanh toán", "Channel", "Tên Người được BH", "Số hợp đồng",
        "Biển số xe", "Ngày bắt đầu", "Ngày kết thúc"
    ]
    df_BHOTO_done["Loại bảo hiểm"] = "BHOTO"

    # BHDL
    sheet_io.seek(0)
    df_BHDL = pd.read_excel(sheet_io, sheet_name="Du lịch",
                            dtype={"Phí bảo hiểm": str}).rename(
        columns={"Họ Và Tên": "Tên Người được BH"})
    df_BHDL_done = df_BHDL[[
        "Ngày thanh toán", "Tên sale", "Sản phẩm", "Đối tác nhà BH",
        "Phí bảo hiểm", "Channel", "Tên Người được BH", "Số hợp đồng"
    ]].copy()
    df_BHDL_done.columns = [
        "Ngày thanh toán", "Code sale", "Sản phẩm", "Đối tác nhà bảo hiểm",
        "Số tiền thanh toán", "Channel", "Tên Người được BH", "Số hợp đồng"
    ]
    df_BHDL_done["Loại bảo hiểm"] = "BHDL"

    # TNSP (TNDS)
    sheet_io.seek(0)
    df_TNSP = pd.read_excel(sheet_io, sheet_name="Trách nhiệm sản phẩm",
                            dtype={"Phí Bảo hiểm": str}).rename(columns={
        "Nhà Bảo hiểm": "Đối tác nhà bảo hiểm",
        "Phí Bảo hiểm": "Số tiền thanh toán",
    })
    df_TNSP_done = df_TNSP[[
        "Ngày thanh toán", "Code sale", "Sản phẩm", "Đối tác nhà bảo hiểm",
        "Số tiền thanh toán", "Channel"
    ]].copy()
    df_TNSP_done["Loại bảo hiểm"] = "TNDS"

    # BHRR
    sheet_io.seek(0)
    df_BHRR = pd.read_excel(sheet_io, sheet_name="Bảo hiểm rủi ro",
                            dtype={"Số tiền thanh toán": str}).rename(columns={
        "Tên khách hàng": "Tên Người được BH",
        "Mã hợp đồng": "Số hợp đồng",
    })
    df_BHRR_done = df_BHRR[[
        "Ngày thanh toán", "Code sale", "Sản phẩm", "Đối tác nhà bảo hiểm",
        "Số tiền thanh toán", "Channel", "Tên Người được BH", "Số hợp đồng",
        "Ngày bắt đầu", "Ngày kết thúc"
    ]].copy()
    df_BHRR_done["Loại bảo hiểm"] = "BHRR"

    # Gộp
    df_union = pd.concat([
        df_BHSK, df_BHOTO_done, df_BHXM_done, df_BHDL_done,
        df_TNSP_done, df_BHRR_done, df_BHYT_done
    ], axis=0, ignore_index=True)
    df_union["Số hợp đồng"] = df_union["Số hợp đồng"].apply(clean_contract)
    for col in ["Ngày thanh toán", "Ngày bắt đầu", "Ngày kết thúc",
                "Ngày Sinh NNBH", "Ngày sinh NMBH"]:
        if col in df_union.columns:
            df_union[col] = df_union[col].apply(standardize_date_format)
    df_union["Số tiền thanh toán"] = clean_currency_column(df_union["Số tiền thanh toán"])
    df_union = clean_whitespace(df_union)

    log(f"  [OK] df_ns={len(df_ns)} | qd1={len(qd1)} | df_union={len(df_union)}")
    return df_ns, qd1, df_union


# ============================================================================
# 5. PUSH 3 BẢNG NGUỒN LÊN SUPABASE
# ============================================================================
def push_sources_to_supabase(engine, df_ns, qd1, df_union):
    log("[Step 4] Đang push 3 bảng nguồn lên Supabase...")
    try:
        qd1.to_sql("qd1", con=engine, if_exists="replace", index=False)
        log("  [OK] qd1")
        df_ns.to_sql("ds_nhan_su_affina", con=engine, if_exists="replace", index=False)
        log("  [OK] ds_nhan_su_affina")
        df_union.to_sql("union_all_data_cap_don", con=engine, if_exists="replace", index=False)
        log("  [OK] union_all_data_cap_don")
    except Exception as e:
        log(f"  [WARN] Push Supabase lỗi (không blocking): {e}")


# ============================================================================
# 6. DUCKDB QUERIES — CORE + NEO + TSA (copy nguyên từ File 3 gốc)
# ============================================================================
def run_duckdb_queries(df_ns, qd1, df_union):
    log("[Step 5] Đang chạy DuckDB queries CORE / NEO / TSA...")
    con = duckdb.connect()
    con.register("df_ns", df_ns)
    con.register("qd1", qd1)
    con.register("df_union", df_union)

    core_sql = f"""
    WITH t1 AS (
        SELECT dnsa.*,
               TRY_CAST(uadcd."Ngày thanh toán" AS DATE) AS "Ngày thanh toán",
               uadcd."Code sale", uadcd."Sản phẩm", uadcd."Đối tác nhà bảo hiểm",
               uadcd."Số tiền thanh toán",
               UPPER(uadcd."Channel") AS "Channel Sales",
               uadcd."Loại bảo hiểm", uadcd."Tên Người được BH",
               TRY_CAST(uadcd."Ngày bắt đầu" AS DATE) AS "Ngày bắt đầu",
               TRY_CAST(uadcd."Ngày kết thúc" AS DATE) AS "Ngày kết thúc",
               uadcd."Số hợp đồng",
               uadcd."Số CMND_CCCD NMBH" AS "CCCD NMBH",
               uadcd."Phone Khách hàng", uadcd."Email NMBH", uadcd."Địa chỉ NMBH",
               uadcd."Tên NMBH", uadcd."Quan hệ",
               TRY_CAST(uadcd."Ngày Sinh NNBH" AS DATE) AS "Ngày Sinh NNBH",
               TRY_CAST(uadcd."Ngày sinh NMBH" AS DATE) AS "Ngày sinh NMBH",
               uadcd."CCCD", uadcd."Ngoại trú", uadcd."Giới tính NNBH",
               uadcd."Nha khoa", uadcd."Thai sản", uadcd."Topup"
        FROM df_ns dnsa
        JOIN df_union uadcd
          ON TRIM(LEADING '0' FROM dnsa."Điện thoại") = TRIM(LEADING '0' FROM uadcd."Code sale")
             OR UPPER(dnsa."Họ tên") = UPPER(uadcd."Code sale")
        WHERE "Chức danh" != 'TSA'
    ),
    detail AS (
        SELECT "Code", "Họ tên", "Họ tên" AS "Họ tên sale", "Code" AS "SĐT sale",
               "Chức danh", "Channel", "Ngày thanh toán", "Sản phẩm",
               "Đối tác nhà bảo hiểm", "Đối tác nhà bảo hiểm" AS "Nhà BH",
               CAST("Số tiền thanh toán" AS DOUBLE) AS "Số tiền thanh toán",
               CAST("Số tiền thanh toán" AS DOUBLE) AS "Phí BH (VNĐ)",
               "QUẢN LÝ CẤP 1 (BDM)", "QUẢN LÝ CẤP 2 (BDD)", "Quản lý Cấp 3 (BDH)",
               "Channel Sales", "Ngày bắt đầu",
               "Tên Người được BH" AS "Tên NĐBH", "Loại bảo hiểm", "Số hợp đồng",
               "CCCD NMBH", "CMND/CCCD", "Ngày kết thúc",
               "Phone Khách hàng" AS "SĐT NMBH", "Email NMBH", "Địa chỉ NMBH",
               "Tên NMBH", "Quan hệ",
               "Ngày Sinh NNBH" AS "Ngày sinh NĐBH", "Ngày sinh NMBH",
               "CCCD" AS "CCCD NĐBH", "Ngoại trú", "Nha khoa",
               "Giới tính NNBH", "Thai sản", "Topup"
        FROM t1
    ),
    final_result AS (
        SELECT d.*, dsqd.rate_bonus, dsqd."Affina_rate_bonus",
               ROUND("Số tiền thanh toán" / (CAST(dsqd."Thuế" AS DOUBLE) + 1), 0) AS "Doanh thu trước thuế",
               exchange_core,
               "RMM_OR" AS "SM_OR_rate", "RMD_OR" AS "SD_OR_rate",
               "BDM_bonus" AS "BDM_rate", "BDD_bonus" AS "BDD_rate",
               "Chi Agency_rate", "Chi QL_rate", "Budget hết tháng 06/2026",
               CASE WHEN "Channel" = 'CTV_TSA (TSA 2)' THEN dsqd."teamlead_tsa"
                    ELSE 0 END AS "Teamlead_rate"
        FROM detail d
        LEFT JOIN qd1 dsqd
          ON TRIM(UPPER(dsqd.provider)) = TRIM(UPPER(d."Đối tác nhà bảo hiểm"))
         AND TRIM(UPPER(dsqd.product))  = TRIM(UPPER(d."Sản phẩm"))
         AND d."Ngày thanh toán" BETWEEN TRY_CAST(dsqd."Effective_Date" AS DATE)
                                     AND TRY_CAST(dsqd."Valid_to" AS DATE)
    )
    SELECT *,
        CASE
            WHEN ("Ngày thanh toán" BETWEEN DATE '2025-07-18' AND DATE '2025-08-31')
                 AND ("Sản phẩm" LIKE '%B-One_new%' OR "Sản phẩm" LIKE '%B-One_Renew%')
                THEN 0.03 * "Doanh thu trước thuế"
            WHEN ("Ngày thanh toán" BETWEEN DATE '2025-08-15' AND DATE '2025-09-10')
                 AND "Loại bảo hiểm" = 'BHXM'
                 AND ("Đối tác nhà bảo hiểm" LIKE '%BSH%' OR "Đối tác nhà bảo hiểm" LIKE '%PVI%')
                THEN 0.15 * "Doanh thu trước thuế"
            WHEN ("Ngày thanh toán" BETWEEN DATE '2025-07-13' AND DATE '2025-07-17')
                 AND exchange_core * "Doanh thu trước thuế" >= 2000000
                 AND exchange_core * "Doanh thu trước thuế" < 3000000
                 AND "Channel" = 'Core Agency' THEN 50000
            WHEN ("Ngày thanh toán" BETWEEN DATE '2025-07-13' AND DATE '2025-07-17')
                 AND exchange_core * "Doanh thu trước thuế" >= 3000000
                 AND exchange_core * "Doanh thu trước thuế" < 5000000
                 AND "Channel" = 'Core Agency' THEN 100000
            WHEN ("Ngày thanh toán" BETWEEN DATE '2025-07-13' AND DATE '2025-07-17')
                 AND exchange_core * "Doanh thu trước thuế" >= 5000000
                 AND "Channel" = 'Core Agency' THEN 200000
            ELSE 0
        END AS "Incentive OVE",
        0 AS "SM_OR", 0 AS "SD_OR", 0 AS "SM_IO", 0 AS "SD_IO",
        0 AS "Chi Agency", 0 AS "Chi QL", 0 AS "Budget Neo T6",
        CASE WHEN "Channel" = 'Core Agency'
             THEN ROUND(CAST("BDM_rate" AS DOUBLE) * "Doanh thu trước thuế", 0)
             ELSE 0 END AS "BDM_bonus",
        CASE WHEN "Channel" = 'Core Agency'
             THEN ROUND(CAST("BDD_rate" AS DOUBLE) * "Doanh thu trước thuế", 0)
             ELSE 0 END AS "BDD_bonus",
        ("Doanh thu trước thuế" * CAST(rate_bonus AS DOUBLE)) AS "EST_Bonus",
        ("Doanh thu trước thuế" * CAST("Affina_rate_bonus" AS DOUBLE)) AS "Affina_Revenue",
        COALESCE("Doanh thu trước thuế" * CAST("Teamlead_rate" AS DOUBLE), 0) AS "Thưởng Teamlead"
    FROM final_result
    WHERE extract(year from "Ngày thanh toán") BETWEEN {START_YEAR} AND {END_YEAR}
      AND UPPER("Channel") NOT IN ('NEO', 'H.O', 'TSA', 'RENEW', 'DIGITAL')
    ORDER BY "Ngày thanh toán"
    """

    neo_sql = f"""
    WITH t1 AS (
        SELECT dnsa.*,
               TRY_CAST(uadcd."Ngày thanh toán" AS DATE) AS "Ngày thanh toán",
               uadcd."Code sale", uadcd."Sản phẩm", uadcd."Đối tác nhà bảo hiểm",
               uadcd."Số tiền thanh toán",
               UPPER(uadcd."Channel") AS "Channel Sales",
               uadcd."Loại bảo hiểm", uadcd."Tên Người được BH",
               TRY_CAST(uadcd."Ngày bắt đầu" AS DATE) AS "Ngày bắt đầu",
               TRY_CAST(uadcd."Ngày kết thúc" AS DATE) AS "Ngày kết thúc",
               uadcd."Số hợp đồng",
               uadcd."Số CMND_CCCD NMBH" AS "CCCD NMBH",
               uadcd."Phone Khách hàng", uadcd."Email NMBH", uadcd."Địa chỉ NMBH",
               uadcd."Tên NMBH", uadcd."Quan hệ",
               TRY_CAST(uadcd."Ngày Sinh NNBH" AS DATE) AS "Ngày Sinh NNBH",
               TRY_CAST(uadcd."Ngày sinh NMBH" AS DATE) AS "Ngày sinh NMBH",
               uadcd."CCCD", uadcd."Ngoại trú", uadcd."Giới tính NNBH",
               uadcd."Nha khoa", uadcd."Thai sản", uadcd."Topup"
        FROM df_ns dnsa
        JOIN df_union uadcd
          ON TRIM(LEADING '0' FROM dnsa."Điện thoại") = TRIM(LEADING '0' FROM uadcd."Code sale")
             OR UPPER(dnsa."Họ tên") = UPPER(uadcd."Code sale")
        WHERE "Chức danh" != 'TSA'
    ),
    detail AS (
        SELECT "Code", "Họ tên", "Họ tên" AS "Họ tên sale", "Code" AS "SĐT sale",
               "Chức danh", "Channel", "Ngày thanh toán", "Sản phẩm",
               "Đối tác nhà bảo hiểm", "Đối tác nhà bảo hiểm" AS "Nhà BH",
               CAST("Số tiền thanh toán" AS DOUBLE) AS "Số tiền thanh toán",
               CAST("Số tiền thanh toán" AS DOUBLE) AS "Phí BH (VNĐ)",
               "QUẢN LÝ CẤP 1 (BDM)", "QUẢN LÝ CẤP 2 (BDD)", "Quản lý Cấp 3 (BDH)",
               "Channel Sales", "Ngày bắt đầu",
               "Tên Người được BH" AS "Tên NĐBH", "Loại bảo hiểm", "Số hợp đồng",
               "CCCD NMBH", "CMND/CCCD", "Ngày kết thúc",
               "Phone Khách hàng" AS "SĐT NMBH", "Email NMBH", "Địa chỉ NMBH",
               "Tên NMBH", "Quan hệ",
               "Ngày Sinh NNBH" AS "Ngày sinh NĐBH", "Ngày sinh NMBH",
               "CCCD" AS "CCCD NĐBH", "Ngoại trú", "Nha khoa",
               "Giới tính NNBH", "Thai sản", "Topup"
        FROM t1
    ),
    final_result AS (
        SELECT d.*, dsqd.rate_bonus, dsqd."Affina_rate_bonus",
               ROUND("Số tiền thanh toán" / (CAST(dsqd."Thuế" AS DOUBLE) + 1), 0) AS "Doanh thu trước thuế",
               exchange_core,
               "RMM_OR" AS "SM_OR_rate", "RMD_OR" AS "SD_OR_rate",
               "BDM_bonus" AS "BDM_rate", "BDD_bonus" AS "BDD_rate",
               "Chi Agency_rate", "Chi QL_rate", "Budget hết tháng 06/2026",
               0 AS "Teamlead_rate",
               CASE WHEN extract(month from d."Ngày thanh toán") BETWEEN 2 AND 6
                         AND dsqd."sp_contest_neo" = 1
                    THEN dsqd."RMM_IO" ELSE 0 END AS "SM_IO_rate",
               CASE WHEN extract(month from d."Ngày thanh toán") BETWEEN 2 AND 6
                         AND dsqd."sp_contest_neo" = 1
                    THEN dsqd."RMD_IO" ELSE 0 END AS "SD_IO_rate"
        FROM detail d
        LEFT JOIN qd1 dsqd
          ON TRIM(UPPER(dsqd.provider)) = TRIM(UPPER(d."Đối tác nhà bảo hiểm"))
         AND TRIM(UPPER(dsqd.product))  = TRIM(UPPER(d."Sản phẩm"))
         AND d."Ngày thanh toán" BETWEEN TRY_CAST(dsqd."Effective_Date" AS DATE)
                                     AND TRY_CAST(dsqd."Valid_to" AS DATE)
    )
    SELECT *,
        0 AS "Incentive OVE",
        ROUND(CAST("SM_OR_rate" AS DOUBLE) * "Doanh thu trước thuế", 0) AS "SM_OR",
        ROUND(CAST("SD_OR_rate" AS DOUBLE) * "Doanh thu trước thuế", 0) AS "SD_OR",
        ROUND(CAST("SM_IO_rate" AS DOUBLE) * "Doanh thu trước thuế", 0) AS "SM_IO",
        ROUND(CAST("SD_IO_rate" AS DOUBLE) * "Doanh thu trước thuế", 0) AS "SD_IO",
        ROUND(CAST("Chi Agency_rate" AS DOUBLE) * "Doanh thu trước thuế", 0) AS "Chi Agency",
        ROUND(CAST("Chi QL_rate"     AS DOUBLE) * "Doanh thu trước thuế", 0) AS "Chi QL",
        ROUND(CAST("Budget hết tháng 06/2026" AS DOUBLE) * "Doanh thu trước thuế", 0) AS "Budget Neo T6",
        0 AS "BDM_bonus", 0 AS "BDD_bonus",
        ("Doanh thu trước thuế" * CAST(rate_bonus AS DOUBLE)) AS "EST_Bonus",
        ("Doanh thu trước thuế" * CAST("Affina_rate_bonus" AS DOUBLE)) AS "Affina_Revenue",
        0 AS "Thưởng Teamlead"
    FROM final_result
    WHERE extract(year from "Ngày thanh toán") BETWEEN {START_YEAR} AND {END_YEAR}
      AND UPPER("Channel") = 'NEO'
    ORDER BY "Ngày thanh toán"
    """

    tsa_sql = f"""
    WITH all_data AS (
        SELECT uadcd.*
        FROM df_union uadcd
        WHERE extract(year from TRY_CAST("Ngày thanh toán" AS DATE)) BETWEEN {START_YEAR} AND {END_YEAR}
          AND UPPER("Channel") IN ('TSA', 'RENEW', 'DIGITAL', 'H.O')
    ),
    joined_data AS (
        SELECT a."Ngày thanh toán", a."Code sale", a."Channel", a."Sản phẩm",
               a."Đối tác nhà bảo hiểm", a."Đối tác nhà bảo hiểm" AS "Nhà BH",
               a."Loại bảo hiểm",
               CAST(a."Số tiền thanh toán" AS DOUBLE) AS "Số tiền thanh toán",
               CAST(a."Số tiền thanh toán" AS DOUBLE) AS "Phí BH (VNĐ)",
               a."Số hợp đồng",
               TRY_CAST(a."Ngày kết thúc" AS DATE) AS "Ngày kết thúc",
               a."Phone Khách hàng" AS "SĐT NMBH", a."Email NMBH", a."Địa chỉ NMBH",
               a."Tên NMBH", a."Quan hệ",
               TRY_CAST(a."Ngày Sinh NNBH" AS DATE) AS "Ngày sinh NĐBH",
               TRY_CAST(a."Ngày sinh NMBH" AS DATE) AS "Ngày sinh NMBH",
               a."CCCD" AS "CCCD NĐBH",
               a."Số CMND_CCCD NMBH" AS "CCCD NMBH",
               a."Ngoại trú", a."Giới tính NNBH", a."Nha khoa", a."Thai sản", a."Topup",
               a."Tên Người được BH" AS "Tên NĐBH",
               TRY_CAST(a."Ngày bắt đầu" AS DATE) AS "Ngày bắt đầu",
               a."Code sale" AS "SĐT sale",
               qd."Affina_rate_bonus",
               ROUND(CAST(a."Số tiền thanh toán" AS DOUBLE) / (CAST(qd."Thuế" AS DOUBLE) + 1), 0) AS "Doanh thu trước thuế",
               CASE WHEN UPPER(a."Channel") = 'RENEW' THEN 0.03
                    WHEN UPPER(a."Channel") = 'H.O'   THEN CAST(qd."rate_bonus" AS DOUBLE)
                    ELSE CAST(qd."bonus_tsa" AS DOUBLE) END AS "bonus_rate",
               CASE WHEN UPPER(a."Channel") != 'RENEW' THEN CAST(qd."reward_Hue" AS DOUBLE)
                    ELSE 0.015 END AS "Teamlead_rate",
               ROUND(CAST(a."Số tiền thanh toán" AS DOUBLE) / (CAST(qd."Thuế" AS DOUBLE) + 1), 0)
                    * CAST(qd."Affina_rate_bonus" AS DOUBLE) AS "Affina_Revenue"
        FROM all_data a
        LEFT JOIN qd1 qd
          ON UPPER(TRIM(qd.provider)) = UPPER(TRIM(a."Đối tác nhà bảo hiểm"))
         AND UPPER(TRIM(qd.product))  = UPPER(TRIM(a."Sản phẩm"))
         AND TRY_CAST(a."Ngày thanh toán" AS DATE)
             BETWEEN TRY_CAST(qd."Effective_Date" AS DATE)
                 AND TRY_CAST(qd."Valid_to" AS DATE)
    )
    SELECT "Ngày thanh toán", "Code sale", "Channel", "Sản phẩm",
           "Đối tác nhà bảo hiểm", "Nhà BH", "Loại bảo hiểm",
           "Số tiền thanh toán", "Phí BH (VNĐ)", "Doanh thu trước thuế",
           "Số hợp đồng", "Ngày kết thúc", "SĐT NMBH", "Email NMBH", "Địa chỉ NMBH",
           "Tên NMBH", "Quan hệ", "Ngày sinh NĐBH", "Ngày sinh NMBH",
           "CCCD NĐBH", "CCCD NMBH", "Ngoại trú", "Giới tính NNBH",
           "Nha khoa", "Thai sản", "Topup", "Tên NĐBH", "Ngày bắt đầu",
           "SĐT sale", "bonus_rate", "Teamlead_rate", "Affina_rate_bonus", "Affina_Revenue",
           CASE
               WHEN (TRY_CAST("Ngày thanh toán" AS DATE) BETWEEN DATE '2025-07-18' AND DATE '2025-08-31')
                    AND ("Sản phẩm" LIKE '%B-One_new%' OR "Sản phẩm" LIKE '%B-One_Renew%')
                   THEN 0.03 * "Doanh thu trước thuế"
               WHEN (TRY_CAST("Ngày thanh toán" AS DATE) BETWEEN DATE '2025-08-15' AND DATE '2025-09-10')
                    AND "Loại bảo hiểm" = 'BHXM'
                    AND ("Đối tác nhà bảo hiểm" LIKE '%BSH%' OR "Đối tác nhà bảo hiểm" LIKE '%PVI%')
                   THEN 0.15 * "Doanh thu trước thuế"
               ELSE 0
           END AS "Incentive OVE",
           ("Doanh thu trước thuế" * CAST("bonus_rate" AS DOUBLE)) AS "EST_Bonus",
           ("Doanh thu trước thuế" * CAST("Teamlead_rate" AS DOUBLE)) AS "Thưởng Teamlead"
    FROM joined_data
    ORDER BY "Ngày thanh toán"
    """

    df_core = con.execute(core_sql).df()
    log(f"  [OK] CORE: {len(df_core)} dòng")
    df_neo = con.execute(neo_sql).df()
    log(f"  [OK] NEO:  {len(df_neo)} dòng")
    df_tsa = con.execute(tsa_sql).df()
    log(f"  [OK] TSA:  {len(df_tsa)} dòng")

    con.close()
    return df_core, df_neo, df_tsa


# ============================================================================
# 7. COMBINE — Không subtotal row (dashboard tự tính, không cần subtotal)
# ============================================================================
def combine_master(df_core, df_neo, df_tsa):
    log("[Step 6] Combine 3 nguồn thành df_master...")
    df_core = df_core.copy(); df_core["Source"] = "Core"
    df_neo  = df_neo.copy();  df_neo["Source"]  = "Neo"
    df_tsa  = df_tsa.copy();  df_tsa["Source"]  = "TSA"

    # Union bằng concat (sort=False giữ nguyên thứ tự cột, thiếu cột → NaN)
    df_master = pd.concat([df_core, df_neo, df_tsa], ignore_index=True, sort=False)

    # KHÔNG thêm subtotal — dashboard tự SUM khi filter. Subtotal chỉ hữu ích cho Excel.

    # Chuẩn hóa cột NGÀY về datetime (Supabase sẽ hiểu là DATE / TIMESTAMP)
    for col in ["Ngày thanh toán", "Ngày bắt đầu", "Ngày kết thúc",
                "Ngày sinh NĐBH", "Ngày sinh NMBH"]:
        if col in df_master.columns:
            df_master[col] = pd.to_datetime(df_master[col], errors="coerce")

    # Numeric cols → float
    numeric_cols = [
        "Số tiền thanh toán", "Phí BH (VNĐ)", "Doanh thu trước thuế",
        "EST_Bonus", "Affina_Revenue", "Thưởng Teamlead", "Incentive OVE",
        "SM_OR", "SD_OR", "SM_IO", "SD_IO", "BDM_bonus", "BDD_bonus",
        "Chi Agency", "Chi QL", "Budget Neo T6",
        "rate_bonus", "Affina_rate_bonus", "exchange_core", "bonus_rate", "Teamlead_rate"
    ]
    for col in numeric_cols:
        if col in df_master.columns:
            df_master[col] = pd.to_numeric(df_master[col], errors="coerce")

    df_master["_ingested_at"] = pd.Timestamp.now(tz="UTC")

    log(f"  [OK] df_master: {len(df_master)} dòng, {len(df_master.columns)} cột")
    return df_master


# ============================================================================
# 8. PUSH DASHBOARD_MASTER_DATA + META LÊN SUPABASE
# ============================================================================
def push_dashboard_data(engine, df_master, df_core, df_neo, df_tsa, duration_sec):
    log("[Step 7] Đang push dashboard_master_data lên Supabase...")

    # Sanitize column names: Supabase/Postgres không thích khoảng trắng nhiều/ký tự đặc biệt
    # nhưng vẫn giữ được nếu dùng quoted identifier. to_sql sẽ auto-quote.
    # -> giữ nguyên tên cột tiếng Việt cho dashboard dễ hiểu.

    # Ghi đè full (replace) — vì dashboard cần snapshot mới hoàn toàn
    df_master.to_sql(
        "dashboard_master_data",
        con=engine,
        if_exists="replace",
        index=False,
        chunksize=1000,
        method="multi",
    )
    log(f"  [OK] Đã push {len(df_master)} dòng vào dashboard_master_data")

    # Meta
    log("[Step 8] Cập nhật dashboard_meta...")
    date_min = df_master["Ngày thanh toán"].min() if "Ngày thanh toán" in df_master.columns else None
    date_max = df_master["Ngày thanh toán"].max() if "Ngày thanh toán" in df_master.columns else None

    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dashboard_meta (
                id           SERIAL PRIMARY KEY,
                updated_at   TIMESTAMPTZ DEFAULT NOW(),
                row_count    INTEGER,
                core_count   INTEGER,
                neo_count    INTEGER,
                tsa_count    INTEGER,
                date_min     DATE,
                date_max     DATE,
                duration_sec NUMERIC,
                status       TEXT,
                error_msg    TEXT
            );
        """))
        conn.execute(text("""
            INSERT INTO dashboard_meta
                (row_count, core_count, neo_count, tsa_count,
                 date_min, date_max, duration_sec, status, error_msg)
            VALUES
                (:rc, :cc, :nc, :tc, :dmin, :dmax, :dur, 'success', NULL)
        """), {
            "rc": len(df_master),
            "cc": len(df_core),
            "nc": len(df_neo),
            "tc": len(df_tsa),
            "dmin": date_min.date() if pd.notna(date_min) else None,
            "dmax": date_max.date() if pd.notna(date_max) else None,
            "dur": duration_sec,
        })
    log("  [OK] dashboard_meta updated")


# ============================================================================
# 9. MAIN
# ============================================================================
def main():
    t_start = time.time()
    log("=" * 70)
    log("BUILD DASHBOARD DATA — START")
    log("=" * 70)

    _validate_env()

    drive_service = get_drive_service()
    log("[Step 1] Đã auth Google Drive (OAuth Refresh Token)")

    sheet_io, dsns_io, qd_io = load_all_sources(drive_service)
    df_ns, qd1, df_union = clean_data(sheet_io, dsns_io, qd_io)

    engine = create_engine(SUPABASE_DB_URI, pool_pre_ping=True)

    push_sources_to_supabase(engine, df_ns, qd1, df_union)

    df_core, df_neo, df_tsa = run_duckdb_queries(df_ns, qd1, df_union)
    df_master = combine_master(df_core, df_neo, df_tsa)

    duration = round(time.time() - t_start, 2)
    push_dashboard_data(engine, df_master, df_core, df_neo, df_tsa, duration)

    log("=" * 70)
    log(f"BUILD DASHBOARD DATA — DONE in {duration}s")
    log(f"  Rows: {len(df_master):,}")
    log(f"  Core={len(df_core):,} | Neo={len(df_neo):,} | TSA={len(df_tsa):,}")
    log("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Log lỗi lên dashboard_meta (nếu có thể) rồi exit non-zero
        log(f"[FATAL] {type(e).__name__}: {e}")
        if SUPABASE_DB_URI:
            try:
                engine = create_engine(SUPABASE_DB_URI, pool_pre_ping=True)
                with engine.begin() as conn:
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS dashboard_meta (
                            id           SERIAL PRIMARY KEY,
                            updated_at   TIMESTAMPTZ DEFAULT NOW(),
                            row_count    INTEGER,
                            core_count   INTEGER,
                            neo_count    INTEGER,
                            tsa_count    INTEGER,
                            date_min     DATE,
                            date_max     DATE,
                            duration_sec NUMERIC,
                            status       TEXT,
                            error_msg    TEXT
                        );
                    """))
                    conn.execute(text("""
                        INSERT INTO dashboard_meta (status, error_msg)
                        VALUES ('error', :msg)
                    """), {"msg": f"{type(e).__name__}: {str(e)[:500]}"})
            except Exception as inner:
                log(f"[WARN] Không thể ghi log lỗi vào Supabase: {inner}")
        raise
