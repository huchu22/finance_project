"""
ISA Maturity Strategy Decision Simulator
Compares 3 major paths upon ISA maturity (e.g. 3-year term):
1. Option A: Transfer to Pension Savings / IRP (연금저축/IRP 이전 - 과세이연, 세액공제, 3.3~5.5% 저율과세)
2. Option B: Direct US Equity (미국 직투 SCHD/VOO - 연 250만원 공제, 양도세 22% 분류과세, 금투세/종소세 회피)
3. Option C: Domestic Taxable Account (국내 일반계좌 - 15.4% 배당소득세, 2천만원 초과 시 종합과세 위험)
"""

from typing import Dict, Any, List
import pandas as pd


class ISAMaturitySimulator:
    """Simulates post-ISA maturity wealth accumulation and taxation."""

    def __init__(
        self,
        maturity_amount: float = 30_000_000,  # e.g., 30M KRW accumulated in ISA after 3 years
        annual_growth_rate: float = 0.07,     # 7% capital appreciation
        annual_dividend_yield: float = 0.035, # 3.5% dividend yield
        investment_horizon_years: int = 10,
    ):
        self.maturity_amount = maturity_amount
        self.g = annual_growth_rate
        self.d = annual_dividend_yield
        self.years = investment_horizon_years

    def simulate_pension_transfer(self) -> Dict[str, Any]:
        """Option A: Pension Savings / IRP Transfer
        - Immediate Tax Credit: 10% of transfer amount (capped at 3M deduction = 495,000 KRW refund for 16.5% bracket)
        - Reinvest refund
        - 0% tax deducted annually (tax deferred)
        - Final withdrawal tax: 5.5% (age 55~69)
        """
        # Tax credit benefit: 10% of transfer amount up to 3,000,000 max deduction base
        deduction_base = min(self.maturity_amount * 0.10, 3_000_000)
        tax_refund = deduction_base * 0.165  # assuming under 55M salary (16.5%)

        current_val = self.maturity_amount + tax_refund
        history = []

        for yr in range(1, self.years + 1):
            growth = current_val * self.g
            dividend = current_val * self.d  # 100% reinvested without 15.4% withholding
            current_val += growth + dividend
            history.append({
                "Year": yr,
                "PreTaxValue": current_val,
                "NetAfterTaxLiquidation": current_val * (1 - 0.055),  # 5.5% pension income tax
                "CumulativeTax": current_val * 0.055,
            })

        return {
            "strategy": "연금저축/IRP 이전 (과세이연+세액공제)",
            "initial_value": self.maturity_amount + tax_refund,
            "tax_refund_received": tax_refund,
            "final_value": current_val,
            "net_liquidation_value": current_val * (1 - 0.055),
            "effective_tax_rate_pct": 5.5,
            "liquidity_note": "만 55세 이후 연금 수령 시 최대 절세 (중도 인출 시 기타소득세 16.5% 주의)",
            "history": pd.DataFrame(history),
        }

    def simulate_us_direct(self) -> Dict[str, Any]:
        """Option B: Direct US Stock Investment (SCHD / VOO)
        - Dividend tax: 15.4% withheld each year
        - Capital gain: 2.5M KRW deduction per year, 22% capital gains tax upon realization
        - Advantage: Capital gains are categorized (분류과세), not included in Financial Income Comprehensive Tax
        """
        current_val = self.maturity_amount
        cost_basis = self.maturity_amount
        total_dividend_tax = 0.0
        history = []

        for yr in range(1, self.years + 1):
            growth = current_val * self.g
            gross_div = current_val * self.d
            div_tax = gross_div * 0.154
            net_div = gross_div - div_tax
            total_dividend_tax += div_tax

            # Reinvest net dividend
            current_val += growth + net_div
            cost_basis += net_div

            # Capital gains tax estimation upon full liquidation
            capital_gain = max(0.0, current_val - cost_basis)
            taxable_gain = max(0.0, capital_gain - 2_500_000)
            cg_tax = taxable_gain * 0.22

            history.append({
                "Year": yr,
                "PreTaxValue": current_val,
                "NetAfterTaxLiquidation": current_val - cg_tax,
                "CumulativeTax": total_dividend_tax + cg_tax,
            })

        capital_gain = max(0.0, current_val - cost_basis)
        taxable_gain = max(0.0, capital_gain - 2_500_000)
        cg_tax = taxable_gain * 0.22

        return {
            "strategy": "미국 직투 전환 (양도세 22% 분류과세)",
            "initial_value": self.maturity_amount,
            "tax_refund_received": 0,
            "final_value": current_val,
            "net_liquidation_value": current_val - cg_tax,
            "effective_tax_rate_pct": round((total_dividend_tax + cg_tax) / (current_val - self.maturity_amount) * 100, 2),
            "liquidity_note": "언제든 자유롭게 인출 가능, 금융소득종합과세(2,000만원) 미합산 분리과세 강점",
            "history": pd.DataFrame(history),
        }

    def simulate_domestic_taxable(self) -> Dict[str, Any]:
        """Option C: Domestic General Taxable Account (국내 일반계좌)
        - Both Trading Gain and Dividends are treated as 배당소득 (15.4% withholding)
        - High risk of triggering 종합과세 if annual income > 20M KRW
        """
        current_val = self.maturity_amount
        cost_basis = self.maturity_amount
        total_tax = 0.0
        history = []

        for yr in range(1, self.years + 1):
            growth = current_val * self.g
            gross_div = current_val * self.d
            div_tax = gross_div * 0.154
            net_div = gross_div - div_tax
            total_tax += div_tax

            current_val += growth + net_div
            cost_basis += net_div

            trading_gain = max(0.0, current_val - cost_basis)
            trading_tax = trading_gain * 0.154

            history.append({
                "Year": yr,
                "PreTaxValue": current_val,
                "NetAfterTaxLiquidation": current_val - trading_tax,
                "CumulativeTax": total_tax + trading_tax,
            })

        trading_gain = max(0.0, current_val - cost_basis)
        trading_tax = trading_gain * 0.154

        return {
            "strategy": "국내 일반계좌 (배당소득세 15.4%)",
            "initial_value": self.maturity_amount,
            "tax_refund_received": 0,
            "final_value": current_val,
            "net_liquidation_value": current_val - trading_tax,
            "effective_tax_rate_pct": 15.4,
            "liquidity_note": "자유로운 입출금 가능하나, 2,000만원 초과 시 금융소득종합과세(최대 49.5%) 누진과세 노출",
            "history": pd.DataFrame(history),
        }

    def compare_all(self) -> pd.DataFrame:
        """Compare all 3 options in a neat summary table."""
        res_a = self.simulate_pension_transfer()
        res_b = self.simulate_us_direct()
        res_c = self.simulate_domestic_taxable()

        data = [
            {
                "전략": res_a["strategy"],
                f"{self.years}년 후 세전 자산": f"{res_a['final_value']:,.0f}원",
                "세후 실질 수령액": f"{res_a['net_liquidation_value']:,.0f}원",
                "세액공제 환급액": f"{res_a['tax_refund_received']:,.0f}원",
                "실효 세율 / 적용세": "5.5% (연금소득세)",
                "특징 및 유동성": res_a["liquidity_note"],
            },
            {
                "전략": res_b["strategy"],
                f"{self.years}년 후 세전 자산": f"{res_b['final_value']:,.0f}원",
                "세후 실질 수령액": f"{res_b['net_liquidation_value']:,.0f}원",
                "세액공제 환급액": "0원",
                "실효 세율 / 적용세": "22% (양도세) / 15.4% (배당)",
                "특징 및 유동성": res_b["liquidity_note"],
            },
            {
                "전략": res_c["strategy"],
                f"{self.years}년 후 세전 자산": f"{res_c['final_value']:,.0f}원",
                "세후 실질 수령액": f"{res_c['net_liquidation_value']:,.0f}원",
                "세액공제 환급액": "0원",
                "실효 세율 / 적용세": "15.4% (배당소득세)",
                "특징 및 유동성": res_c["liquidity_note"],
            },
        ]
        return pd.DataFrame(data)
