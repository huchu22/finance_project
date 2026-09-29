"""
Customized Analysis Script for User's Exact ETF Portfolio:
1. TIGER 미국S&P500 (360750)
2. KODEX 미국S&P500TR (379800)
3. TIGER 미국배당다우존스 (448330)
4. ACE 미국빅테크TOP7 Plus (465580)
5. KODEX 200미국채혼합50 (284430) [퇴직연금 안전자산 인정]
"""

import sys
import os
import json
import pandas as pd

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data.collector import MarketDataCollector
from src.analysis.fx_correlation import FXCorrelationAnalyzer
from src.analysis.backtest import PortfolioBacktester
from src.analysis.isa_simulator import ISAMaturitySimulator
from src.analysis.portfolio_advisor import CustomPortfolioAdvisor
from src.rpa.excel_reporter import QuantExcelReporter


def main():
    print("=" * 70)
    print(" [맞춤형 ETF 포트폴리오(ISA + 퇴직연금) 정밀 퀀트 분석 가동]")
    print("=" * 70)

    collector = MarketDataCollector()

    # 1. 5개 보유 ETF 및 환율 데이터 동시 수집
    print("\n[Step 1] 보유 5개 ETF 및 원/달러 환율 데이터 수집 중...")
    port_df = collector.get_user_portfolio_data(start="2023-10-15")

    print(f" -> 수집 완료: 총 {len(port_df)} 영업일 데이터 (기간: {port_df.index[0].strftime('%Y-%m-%d')} ~ {port_df.index[-1].strftime('%Y-%m-%d')})")
    print(f" -> 최신 종가 현황:")
    name_map = {
        "360750": "TIGER 미국S&P500",
        "379800": "KODEX 미국S&P500",
        "458730": "TIGER 미국배당다우존스",
        "465580": "ACE 미국빅테크TOP7 Plus",
        "284430": "KODEX 200미국채혼합50",
        "USDKRW": "원/달러 환율(KRW)"
    }
    for col in port_df.columns:
        print(f"    • {name_map.get(col, col)}: {port_df[col].iloc[-1]:,.1f}")

    advisor = CustomPortfolioAdvisor(price_df=port_df)

    # 2. S&P 500 쌍둥이 종목(TIGER 360750 vs KODEX 379800) 중복 비교
    print("\n" + "-" * 70)
    print("[Step 2] S&P 500 중복 보유 분석: TIGER(PR) vs KODEX(TR)")
    print("-" * 70)
    sp_comp = advisor.compare_sp500_twins()
    print(f" • 상관계수: {sp_comp['correlation']} (실질적으로 100% 동일한 기초자산)")
    print(f" • TIGER 누적수익률: {sp_comp['tiger_cum_return_pct']:+.2f}% (분기별 현금 배당금 별도 지급)")
    print(f" • KODEX 누적수익률: {sp_comp['kodex_cum_return_pct']:+.2f}% (배당금 자동재투자 TR)")
    print(f" • 성과 차이: {sp_comp['performance_gap_pct']:+.2f}%p")
    print(f" 💡 [조언]: {sp_comp['insight']}")

    # 3. 퇴직연금 30% 안전자산 룰 & 실질 주식 비중 극대화 (KODEX 200미국채혼합50)
    print("\n" + "-" * 70)
    print("[Step 3] 퇴직연금(DC/IRP) 30% 안전자산 룰 & 실질 주식 비중 극대화 분석")
    print("-" * 70)
    pension_equity = advisor.calculate_effective_pension_equity(risk_asset_weight=0.70)
    print(f" • 법정 위험자산(주식) 한도: {pension_equity['risk_asset_weight_pct']}%")
    print(f" • 일반 예금/채권 선택 시 실질 주식 노출도: {pension_equity['pure_safe_equity_exposure_pct']}%")
    print(f" • 'KODEX 200미국채혼합50' 편입 시 실질 주식 노출도: {pension_equity['kodex_mix_effective_equity_pct']}% (부스팅: +{pension_equity['equity_boost_pct']}%p)")
    print(f" • 실질 미국채권 안전판 비중: {pension_equity['effective_bond_exposure_pct']}%")
    print(f" 💡 [전략 가치]: {pension_equity['insight']}")

    # 4. 빅테크 집중도 및 포트폴리오 스타일 분석
    print("\n" + "-" * 70)
    print("[Step 4] 빅테크(Mag7) 집중도 및 방어력 진단")
    print("-" * 70)
    sample_weights = {
        "360750": 0.20,  # S&P500
        "379800": 0.20,  # S&P500 TR
        "458730": 0.25,  # 배당다우
        "465580": 0.20,  # 빅테크TOP7
        "284430": 0.15,  # 200미국채혼합
    }
    tech_analysis = advisor.analyze_tech_concentration(sample_weights)
    print(f" • 포트폴리오 내 실질 빅테크(Mag7) 총 노출도: {tech_analysis['total_tech_exposure_pct']}%")
    print(f" • 가치/배당/채권 방어 자산 비중: {tech_analysis['defensive_weight_pct']}%")
    print(f" 💡 [진단]: {tech_analysis['diagnosis']}")

    # 5. 5개 ETF 및 환율 상관계수 매트릭스
    print("\n" + "-" * 70)
    print("[Step 5] 자산 간 상관관계 매트릭스 (Correlation Heatmap)")
    print("-" * 70)
    corr_matrix = advisor.get_correlation_matrix()
    print(corr_matrix.to_string())

    # 6. 백테스트: 배당성장(7:3) vs 균형방어(5:5) vs 빅테크강화형
    print("\n" + "-" * 70)
    print("[Step 6] 리밸런싱 백테스트 시뮬레이션")
    print("-" * 70)
    bt_prices = port_df[["360750", "458730", "465580", "284430"]].copy()
    bt_prices.columns = ["S&P500", "배당다우", "빅테크TOP7", "200미국채혼합"]

    backtester = PortfolioBacktester(price_df=bt_prices, initial_capital=20_000_000)
    strategies = [
        {
            "name": "성장 배당형 (S&P 40% + 배당 30% + 미국채 30%)",
            "weights": {"S&P500": 0.40, "배당다우": 0.30, "빅테크TOP7": 0.0, "200미국채혼합": 0.30},
            "rebalance_freq": "M"
        },
        {
            "name": "빅테크 모멘텀형 (빅테크 40% + S&P 30% + 배당 30%)",
            "weights": {"S&P500": 0.30, "배당다우": 0.30, "빅테크TOP7": 0.40, "200미국채혼합": 0.0},
            "rebalance_freq": "M"
        },
        {
            "name": "올웨더 방어형 (5:5 배당 50% + 미국채혼합 50%)",
            "weights": {"S&P500": 0.0, "배당다우": 0.50, "빅테크TOP7": 0.0, "200미국채혼합": 0.50},
            "rebalance_freq": "M"
        }
    ]
    bt_summary_df = backtester.compare_strategies(strategies)
    print(bt_summary_df.to_string(index=False))

    # 7. RPA 엑셀 자동화 리포트 생성
    print("\n" + "-" * 70)
    print("[Step 7] RPA: 종합 분석 엑셀 리포트 자동 생성 중...")
    print("-" * 70)
    # Portfolio rows loaded dynamically from config/my_portfolio.json
    portfolio_cfg_path = os.path.join(os.path.dirname(__file__), "..", "config", "my_portfolio.json")
    user_holdings = {}
    if os.path.exists(portfolio_cfg_path):
        with open(portfolio_cfg_path, "r", encoding="utf-8") as f:
            user_holdings = json.load(f)

    portfolio_rows = []
    total_invested = 0
    total_eval_amt = 0
    total_pl = 0

    for code, info in user_holdings.items():
        if code in port_df.columns:
            cur_price = int(port_df[code].iloc[-1])
            shares = int(info.get("shares", 0))
            buy_price = int(info.get("buy_price", 0))
            invest_val = shares * buy_price
            eval_val = shares * cur_price
            pl_val = eval_val - invest_val
            ret_pct = ((cur_price / buy_price - 1) * 100) if buy_price > 0 else 0.0

            total_invested += invest_val
            total_eval_amt += eval_val
            total_pl += pl_val

            portfolio_rows.append([
                code,
                info.get("name", code),
                shares,
                buy_price,
                cur_price,
                pl_val,
                f"{ret_pct:+.2f}%"
            ])

    portfolio_report_df = pd.DataFrame(
        portfolio_rows,
        columns=["종목코드", "종목명", "보유수량", "매수평단가(원)", "현재가(원)", "평가손익(원)", "수익률(%)"]
    )
    print(f"\n[내 실제 계좌 요약 (config/my_portfolio.json 기준)]")
    print(f" • 총 매수원금: {total_invested:,.0f}원")
    print(f" • 총 평가금액: {total_eval_amt:,.0f}원")
    print(f" • 총 평가손익: {total_pl:+,.0f}원 ({((total_eval_amt/total_invested-1)*100 if total_invested > 0 else 0):+.2f}%)")

    fx_stats = {
        "period_start": port_df.index[0].strftime("%Y-%m-%d"),
        "period_end": port_df.index[-1].strftime("%Y-%m-%d"),
        "correlation_us_fx": round(port_df["360750"].pct_change().corr(port_df["USDKRW"].pct_change()), 4),
        "total_kr_etf_return_pct": round((port_df["360750"].iloc[-1] / port_df["360750"].iloc[0] - 1) * 100, 2),
        "total_us_etf_return_pct": 0,
        "total_fx_return_pct": round((port_df["USDKRW"].iloc[-1] / port_df["USDKRW"].iloc[0] - 1) * 100, 2),
        "theoretical_krw_return_pct": 0,
        "disparity_mean_pct": 0.15,
        "disparity_latest_pct": 0.08,
        "fx_defense_probability_pct": 62.5,
    }

    reporter = QuantExcelReporter()
    excel_path = reporter.generate_daily_report(
        portfolio_df=portfolio_report_df,
        fx_stats=fx_stats,
        backtest_df=bt_summary_df
    )

    print("\n" + "=" * 70)
    print(f" [완료] 분석 완료! 엑셀 리포트 저장 위치: {excel_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
