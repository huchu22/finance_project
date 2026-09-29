"""
Portfolio Rebalancing Backtester
- Simulates asset allocation strategies (e.g. TIGER 미국배당다우존스 70% + KODEX 200미국채혼합 30% vs 50:50)
- Supports Periodic Rebalancing (Monthly, Quarterly, Annually, Buy & Hold)
- Calculates CAGR, MDD, Sharpe Ratio, Volatility, and Drawdown series
"""

from typing import Dict, List, Any, Optional
import numpy as np
import pandas as pd


class PortfolioBacktester:
    """Backtesting engine for multi-asset portfolio with custom rebalancing."""

    def __init__(self, price_df: pd.DataFrame, initial_capital: float = 20_000_000, risk_free_rate: float = 0.035):
        """
        :param price_df: DataFrame with asset daily close prices (columns as asset identifiers).
        :param initial_capital: Initial investment amount in KRW (default 20M KRW for ISA 1st year).
        :param risk_free_rate: Annual risk-free rate (e.g., 3.5% = 0.035).
        """
        self.prices = price_df.dropna().copy()
        self.initial_capital = initial_capital
        self.rf = risk_free_rate

    def run_strategy(
        self,
        weights: Dict[str, float],
        rebalance_freq: Optional[str] = "M",
        name: str = "Strategy"
    ) -> Dict[str, Any]:
        """Run backtest for given weights and rebalancing frequency ('M', 'Q', 'Y', None for Buy&Hold)."""
        assets = list(weights.keys())
        missing = [a for a in assets if a not in self.prices.columns]
        if missing:
            raise ValueError(f"Assets {missing} not found in price data columns: {list(self.prices.columns)}")

        # Normalize weights if sum != 1.0
        total_w = sum(weights.values())
        norm_weights = {k: v / total_w for k, v in weights.items()}

        sub_prices = self.prices[assets]
        dates = sub_prices.index

        # Rebalancing dates determination
        rebal_flags = pd.Series(False, index=dates)
        rebal_flags.iloc[0] = True

        if rebalance_freq == "M":
            month_ends = dates.to_series().groupby(pd.Grouper(freq="ME")).tail(1)
            rebal_flags.loc[month_ends] = True
        elif rebalance_freq == "Q":
            quarter_ends = dates.to_series().groupby(pd.Grouper(freq="QE")).tail(1)
            rebal_flags.loc[quarter_ends] = True
        elif rebalance_freq == "Y":
            year_ends = dates.to_series().groupby(pd.Grouper(freq="YE")).tail(1)
            rebal_flags.loc[year_ends] = True

        # Simulation
        portfolio_value = pd.Series(index=dates, dtype=float)
        holdings = {a: 0.0 for a in assets}

        curr_cash = self.initial_capital

        for i, dt in enumerate(dates):
            current_prices = sub_prices.loc[dt]

            # Rebalancing trigger
            if rebal_flags.loc[dt]:
                if i > 0:
                    curr_cash = sum(holdings[a] * current_prices[a] for a in assets)
                for a in assets:
                    allocated_cash = curr_cash * norm_weights[a]
                    holdings[a] = allocated_cash / current_prices[a]

            # Calculate total valuation
            total_val = sum(holdings[a] * current_prices[a] for a in assets)
            portfolio_value.loc[dt] = total_val

        # Daily returns
        daily_ret = portfolio_value.pct_change().dropna()

        # Cumulative Return
        cum_ret = (portfolio_value.iloc[-1] / portfolio_value.iloc[0] - 1) * 100

        # Total Days & CAGR
        days = (dates[-1] - dates[0]).days
        years = max(days / 365.25, 0.01)
        cagr = ((portfolio_value.iloc[-1] / portfolio_value.iloc[0]) ** (1.0 / years) - 1) * 100

        # Maximum Drawdown (MDD)
        rolling_max = portfolio_value.cummax()
        drawdown = (portfolio_value - rolling_max) / rolling_max
        mdd = drawdown.min() * 100

        # Annualized Volatility
        ann_vol = daily_ret.std() * np.sqrt(252) * 100

        # Sharpe Ratio
        excess_daily_ret = daily_ret - (self.rf / 252)
        sharpe = (excess_daily_ret.mean() / daily_ret.std()) * np.sqrt(252) if daily_ret.std() > 0 else 0

        return {
            "name": name,
            "weights": norm_weights,
            "rebalance_freq": rebalance_freq or "Buy & Hold",
            "initial_capital": self.initial_capital,
            "final_value": portfolio_value.iloc[-1],
            "total_return_pct": round(cum_ret, 2),
            "cagr_pct": round(cagr, 2),
            "mdd_pct": round(mdd, 2),
            "volatility_pct": round(ann_vol, 2),
            "sharpe_ratio": round(sharpe, 2),
            "series": portfolio_value,
            "drawdown_series": drawdown * 100,
        }

    def compare_strategies(self, strategies_config: List[Dict[str, Any]]) -> pd.DataFrame:
        """Compare multiple strategies and return a summary dataframe."""
        results = []
        for cfg in strategies_config:
            res = self.run_strategy(
                weights=cfg["weights"],
                rebalance_freq=cfg.get("rebalance_freq", "M"),
                name=cfg.get("name", "Strategy")
            )
            results.append({
                "전략명": res["name"],
                "비중": str(res["weights"]),
                "리밸런싱 주기": res["rebalance_freq"],
                "최종 평가액(원)": f"{res['final_value']:,.0f}",
                "누적 수익률(%)": f"{res['total_return_pct']:+.2f}%",
                "CAGR(연복리)": f"{res['cagr_pct']:.2f}%",
                "MDD(최대낙폭)": f"{res['mdd_pct']:.2f}%",
                "변동성(연간)": f"{res['volatility_pct']:.2f}%",
                "샤프지수": f"{res['sharpe_ratio']:.2f}",
            })
        return pd.DataFrame(results)
