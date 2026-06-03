# -*- coding: utf-8 -*-
"""Excel export helper."""
import io

import pandas as pd


def to_excel_bytes(df, sheet_name="Report"):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xl:
        df.to_excel(xl, index=False, sheet_name=sheet_name[:31])
        ws = xl.sheets[sheet_name[:31]]
        for i, col in enumerate(df.columns, start=1):
            # pandas 3.0 keeps missing values as NA after astype(str), so an
            # all-null column yields NaN here; fall back to a sane default.
            max_len = df[col].astype(str).str.len().max()
            if pd.isna(max_len):
                max_len = 10
            content_width = int(max_len) + 2
            header_width = len(str(col)) + 2
            width = max(12, min(40, max(content_width, header_width)))
            ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = width
    buf.seek(0)
    return buf.getvalue()
