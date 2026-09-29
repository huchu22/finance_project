"""
Portfolio Advisor Module Tailored to User's Specific 5 ETF Holdings:
1. TIGER 미국S&P500 (360750)
2. KODEX 미국S&P500TR (379800)
3. TIGER 미국배당다우존스 (448330)
4. ACE 미국빅테크TOP7 Plus (465580)
5. KODEX 200미국채혼합50 (284430) [퇴직연금 안전자산]
"""

from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd


class CustomPortfolioAdvisor:
    """Provides targeted quant insights for user's specific ETF mix."""

    def __init__(self, price_df: pd.DataFrame):
        """price_df columns expected:
        '360750', '379800', '448330', '465580', '284430', and optionally 'USDKRW'
        """
        self.prices = price_df.dropna().copy()
        self.returns = self.prices.pct_change().dropna()

    def compare_sp500_twins(self) -> Dict[str, Any]:
        """Deep comparison between TIGER 미국S&P500 (360750) vs KODEX 미국S&P500TR (379800).
        Evaluates tracking correlation, cumulative returns, and dividend strategy differences.
        """
        if "360750" not in self.prices.columns or "379800" not in self.prices.columns:
            return {}

        tiger_p = self.prices["360750"]
        kodex_p = self.prices["379800"]

        corr = self.returns["360750"].corr(self.returns["379800"])
        tiger_cum = (tiger_p.iloc[-1] / tiger_p.iloc[0] - 1) * 100
        kodex_cum = (kodex_p.iloc[-1] / kodex_p.iloc[0] - 1) * 100

        # Daily tracking difference
        diff_series = (self.returns["379800"] - self.returns["360750"]) * 100

        return {
            "correlation": round(corr, 4),
            "tiger_cum_return_pct": round(tiger_cum, 2),
            "kodex_cum_return_pct": round(kodex_cum, 2),
            "performance_gap_pct": round(kodex_cum - tiger_cum, 2),
            "daily_diff_std": round(diff_series.std(), 4),
            "insight": (
                "두 종목은 동일 지수를 추종하는 99.9% 복제 종목입니다. "
                "TIGER(360750)는 '현금 배당 분배형(PR)'으로 분기별 배당금을 직접 인출/재투자하기에 적합하며, "
                "KODEX(379800)는 '배당 자동재투자형(TR)'으로 배당세 과세이연 및 자동 복리 효과를 노리는 장기 적립식에 최적화되어 있습니다. "
                "포트폴리오가 분산되어 보이지만 실제로는 동일 종목이므로, 현금 배당 선호 여부에 따라 하나로 단일화하는 것이 관리상 효율적입니다."
            )
        }

    def calculate_effective_pension_equity(self, risk_asset_weight: float = 0.70) -> Dict[str, Any]:
        """Calculates effective equity exposure in Retirement Pension (DC/IRP).
        Rule: Risk assets <= 70%, Safe assets >= 30%.
        KODEX 200미국채혼합50 (284430) has ~40% KOSPI 200 equity and ~60% US 10Y Treasury.
        """
        safe_asset_weight = 1.0 - risk_asset_weight

        # Pure cash/deposit safe asset
        pure_cash_equity = risk_asset_weight * 100

        # KODEX 200미국채혼합50 safe asset (contains 40% equity)
        kodex_equity_inside = 0.40
        boosted_equity = (risk_asset_weight + (safe_asset_weight * kodex_equity_inside)) * 100
        bond_exposure = (safe_asset_weight * (1.0 - kodex_equity_inside)) * 100

        return {
            "risk_asset_weight_pct": round(risk_asset_weight * 100, 1),
            "safe_asset_weight_pct": round(safe_asset_weight * 100, 1),
            "pure_safe_equity_exposure_pct": round(pure_cash_equity, 1),
            "kodex_mix_effective_equity_pct": round(boosted_equity, 1),
            "equity_boost_pct": round(boosted_equity - pure_cash_equity, 1),
            "effective_bond_exposure_pct": round(bond_exposure, 1),
            "insight": (
                f"퇴직연금 의무 안전자산 30%를 단순 예금/채권 대신 'KODEX 200미국채혼합50'으로 채우면, "
                f"계좌 전체의 실질 주식 노출도가 기존 {pure_cash_equity:.0f}%에서 **{boosted_equity:.1f}%**로 "
                f"+{boosted_equity - pure_cash_equity:.1f}%p 증가합니다. "
                f"이는 법정 안전자산 규제를 100% 준수하면서도 20~30년 장기 복리 수익률을 극대화하는 가장 강력한 연금 운용 전략입니다."
            )
        }

    def analyze_tech_concentration(self, weights: Dict[str, float]) -> Dict[str, Any]:
        """Estimates total Magnificent 7 / BigTech concentration across holdings."""
        # Approximate Tech/Mag7 ratios in each ETF
        tech_ratios = {
            "360750": 0.32,  # S&P 500: ~32% Mag7/Tech
            "379800": 0.32,  # S&P 500: ~32% Mag7/Tech
            "458730": 0.08,  # 배당다우: Financials, Healthcare, Industrials (BigTech ~8%)
            "465580": 0.95,  # ACE 빅테크TOP7: 95% Mag7
            "284430": 0.08,  # 채권혼합: KOSPI200 삼전/하이닉스 + 미국채
        }

        total_weight = sum(weights.values())
        norm_weights = {k: v / total_weight for k, v in weights.items() if total_weight > 0}

        overall_tech = sum(norm_weights.get(k, 0.0) * tech_ratios.get(k, 0.20) for k in norm_weights) * 100
        overall_dividend_defensive = norm_weights.get("458730", 0.0) * 100 + norm_weights.get("284430", 0.0) * 60

        return {
            "total_tech_exposure_pct": round(overall_tech, 1),
            "defensive_weight_pct": round(overall_dividend_defensive, 1),
            "is_tech_overweight": overall_tech > 50.0,
            "diagnosis": (
                f"포트폴리오의 실질 빅테크/성장주 비중은 약 **{overall_tech:.1f}%**입니다. "
                + ("(빅테크 초집중 상태: 강세장에서 높은 수익률을 내지만, 금리 급등이나 기술주 조정 시 변동성이 큽니다.)"
                   if overall_tech > 50.0 else
                   "(적절한 분산: S&P500의 시장 평균과 배당다우존스의 방어력이 균형을 이루고 있습니다.)")
            )
        }

    def get_correlation_matrix(self) -> pd.DataFrame:
        """Returns correlation matrix with user-friendly Korean ETF names."""
        name_map = {
            "360750": "TIGER S&P500",
            "379800": "KODEX S&P500TR",
            "458730": "TIGER 배당다우",
            "465580": "ACE 빅테크TOP7",
            "284430": "KODEX 200미국채",
            "USDKRW": "원/달러 환율"
        }
        df_corr = self.returns.corr()
        df_corr.index = [name_map.get(c, c) for c in df_corr.index]
        df_corr.columns = [name_map.get(c, c) for c in df_corr.columns]
        return df_corr.round(3)
