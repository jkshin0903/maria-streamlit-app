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
            width = max(12, min(40, int(df[col].astype(str).str.len().max() or 10) + 2,
                                len(str(col)) + 2))
            ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = max(
                len(str(col)) + 2, width)
    buf.seek(0)
    return buf.getvalue()
