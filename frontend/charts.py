import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional


def _coerce_numerics(df: pd.DataFrame) -> pd.DataFrame:
    """Try to convert string columns to numeric where possible."""
    df = df.copy()
    for c in df.columns:
        if df[c].dtype == object:
            converted = pd.to_numeric(df[c], errors="coerce")
            if converted.notna().sum() == len(df):  # all values converted cleanly
                df[c] = converted
    return df


def _label_col(df: pd.DataFrame) -> Optional[str]:
    """Return the first string/categorical column — best candidate for x-axis labels."""
    for c in df.columns:
        if df[c].dtype == object:
            return c
    return None


def _date_col(df: pd.DataFrame) -> Optional[str]:
    """Return the first datetime column."""
    for c in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[c]):
            return c
        if df[c].dtype == object:
            try:
                parsed = pd.to_datetime(df[c], infer_datetime_format=True)
                if parsed.notna().all():
                    return c
            except Exception:
                pass
    return None


def _numeric_cols(df: pd.DataFrame, exclude: list[str]) -> list[str]:
    """Return all numeric columns not in the exclude list."""
    return [c for c in df.columns if c not in exclude and pd.api.types.is_numeric_dtype(df[c])]


def detect_chart_type(df: pd.DataFrame) -> str:
    df = _coerce_numerics(df)
    if len(df.columns) < 2 or df.empty:
        return "table"

    date = _date_col(df)
    if date:
        nums = _numeric_cols(df, exclude=[date])
        if nums:
            return "line"

    label = _label_col(df)
    if label:
        nums = _numeric_cols(df, exclude=[label])
        if nums:
            return "pie" if df[label].nunique() <= 8 and len(nums) == 1 else "bar"

    # All numeric — use first col as x
    nums = _numeric_cols(df, exclude=[])
    if len(nums) >= 2:
        return "bar"

    return "table"


def build_figure(df: pd.DataFrame, title: str = "", chart_type: str = "auto") -> Optional[go.Figure]:
    df = _coerce_numerics(df)

    if chart_type == "auto":
        chart_type = detect_chart_type(df)

    if chart_type == "table" or df.empty or len(df.columns) < 1:
        return None

    date = _date_col(df)
    label = _label_col(df)

    if chart_type == "line":
        x = date or label or df.columns[0]
        if x and df[x].dtype == object:
            try:
                df[x] = pd.to_datetime(df[x], infer_datetime_format=True)
            except Exception:
                pass
        y_cols = _numeric_cols(df, exclude=[x])
        if not y_cols:
            return None
        fig = px.line(df, x=x, y=y_cols, title=title, markers=True)
        fig.update_layout(legend_title="")

    elif chart_type == "bar":
        x = label or df.columns[0]
        y_cols = _numeric_cols(df, exclude=[x])
        if not y_cols:
            return None
        fig = px.bar(df, x=x, y=y_cols, title=title, barmode="group")
        fig.update_layout(xaxis_tickangle=-30, legend_title="")

    elif chart_type == "pie":
        x = label or df.columns[0]
        y_cols = _numeric_cols(df, exclude=[x])
        if not y_cols:
            return None
        fig = px.pie(df, names=x, values=y_cols[0], title=title)

    else:
        return None

    fig.update_layout(margin=dict(t=50, b=40))
    return fig
