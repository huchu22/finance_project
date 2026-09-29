"""
FX & Underlying Asset Correlation and Disparity Analyzer
- Analyzes return decomposition: Domestic ETF Return = Asset Return + FX Effect + Interaction
- Calculates correlation between US Asset and USD/KRW (Dollar Hedge Defense Effect)
- Computes tracking disparity between Korean ETF and Theoretical Value (US Price * FX)
"""

from typing import Dict, Any
import numpy as np
import pandas as pd


class FXCorrelationAnalyzer:
    """Analyzes currency effects, correlation, and tracking disparity for domestic-listed foreign ETFs."""

    def __init__(self, df: pd.DataFrame, kr_col: str, us_col: str, fx_col: str = "USDKRW"):
        self.df = df.copy()
        self.kr_col = kr_col
        self.us_col = us_col
        self.fx_col = fx_col
        self._calculate_returns()

    def _calculate_returns(self):
        """Calculate daily returns and normalized base 100 prices."""
        self.df["ret_kr"] = self.df[self.kr_col].pct_change()
        self.df["ret_us"] = self.df[self.us_col].pct_change()
        self.df["ret_fx"] = self.df[self.fx_col].pct_change()

        # Cumulative normalized price starting from 100
        self.df["norm_kr"] = (self.df[self.kr_col] / self.df[self.kr_col].iloc[0]) * 100
        self.df["norm_us"] = (self.df[self.us_col] / self.df[self.us_col].iloc[0]) * 100
        self.df["norm_fx"] = (self.df[self.fx_col] / self.df[self.fx_col].iloc[0]) * 100

        # Theoretical normalized: US price converted to KRW
        theo = self.df[self.us_col] * self.df[self.fx_col]
        self.df["norm_theo"] = (theo / theo.iloc[0]) * 100

        # Disparity rate (%) = (Actual Korean ETF / Theoretical KRW - 1) * 100
        self.df["disparity_pct"] = ((self.df["norm_kr"] / self.df["norm_theo"]) - 1) * 100

    def get_summary_statistics(self) -> Dict[str, Any]:
        """Compute key correlation metrics and return decomposition."""
        valid_df = self.df.dropna()

        # 1. Overall Correlation
        corr_matrix = valid_df[["ret_kr", "ret_us", "ret_fx"]].corr()
        corr_us_fx = corr_matrix.loc["ret_us", "ret_fx"]

        # 2. Downside Defense: FX movement when US stock drops
        down_days = valid_df[valid_df["ret_us"] < 0]
        avg_down_us = down_days["ret_us"].mean() * 100 if len(down_days) > 0 else 0
        fx_offset_on_down = down_days["ret_fx"].mean() * 100 if len(down_days) > 0 else 0
        defense_rate = (
            down_days[down_days["ret_fx"] > 0].shape[0] / len(down_days) * 100
            if len(down_days) > 0 else 0
        )

        # 3. Cumulative Return Decomposition
        total_kr_return = (self.df[self.kr_col].iloc[-1] / self.df[self.kr_col].iloc[0] - 1) * 100
        total_us_return = (self.df[self.us_col].iloc[-1] / self.df[self.us_col].iloc[0] - 1) * 100
        total_fx_return = (self.df[self.fx_col].iloc[-1] / self.df[self.fx_col].iloc[0] - 1) * 100

        # Interaction effect: (1 + R_us) * (1 + R_fx) - 1
        compounded_theo_return = (
            (1 + total_us_return / 100) * (1 + total_fx_return / 100) - 1
        ) * 100

        return {
            "period_start": self.df.index[0].strftime("%Y-%m-%d"),
            "period_end": self.df.index[-1].strftime("%Y-%m-%d"),
            "total_days": len(self.df),
            "correlation_us_fx": round(corr_us_fx, 4),
            "total_kr_etf_return_pct": round(total_kr_return, 2),
            "total_us_etf_return_pct": round(total_us_return, 2),
            "total_fx_return_pct": round(total_fx_return, 2),
            "theoretical_krw_return_pct": round(compounded_theo_return, 2),
            "disparity_mean_pct": round(self.df["disparity_pct"].mean(), 2),
            "disparity_latest_pct": round(self.df["disparity_pct"].iloc[-1], 2),
            "down_days_count": len(down_days),
            "avg_us_drop_on_down_days": round(avg_down_us, 2),
            "avg_fx_change_on_down_days": round(fx_offset_on_down, 2),
            "fx_defense_probability_pct": round(defense_rate, 2),
        }

    def get_processed_dataframe(self) -> pd.DataFrame:
        """Return the calculated dataframe for plotting or reporting."""
        return self.df
