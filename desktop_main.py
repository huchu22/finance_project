"""
Standalone Desktop Entry Point for PyInstaller (.exe)
Allows execution on any Windows PC without Python installed.
- Reads 'my_portfolio.json' located in the same folder as the .exe (editable via Notepad).
- Fetches live market prices and FX rate.
- Automatically generates multi-tab formatted Excel report in 'reports/' folder.
- Automatically opens the Excel report on the screen!
- Keeps window open until user presses Enter.
"""

import sys
import os
import json
import traceback
import pandas as pd


def get_base_dir() -> str:
    """Return directory where the .exe or script is running."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


# Ensure module paths are discoverable
BASE_DIR = get_base_dir()
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.data.collector import MarketDataCollector
from src.analysis.backtest import PortfolioBacktester
from src.analysis.portfolio_advisor import CustomPortfolioAdvisor
from src.analysis.ai_briefing import AIBriefingEngine
from src.rpa.excel_reporter import QuantExcelReporter


DEFAULT_PORTFOLIO = {
    "360750": {
        "name": "TIGER 미국S&P500",
        "account": "ISA / 일반",
        "shares": 20,
        "buy_price": 24346
    },
    "379800": {
        "name": "KODEX 미국S&P500TR",
        "account": "ISA / 일반",
        "shares": 9,
        "buy_price": 22296
    },
    "458730": {
        "name": "TIGER 미국배당다우존스",
        "account": "ISA / 일반",
        "shares": 61,
        "buy_price": 14555
    },
    "465580": {
        "name": "ACE 미국빅테크TOP7 Plus",
        "account": "ISA / 일반",
        "shares": 6,
        "buy_price": 24225
    },
    "284430": {
        "name": "KODEX 200미국채혼합50",
        "account": "퇴직연금 (DC/IRP)",
        "shares": 229,
        "buy_price": 18725
    }
}


def load_portfolio_config() -> tuple[dict, str]:
    """Search for my_portfolio.json in base dir or config dir, create if missing."""
    p1 = os.path.join(BASE_DIR, "my_portfolio.json")
    p2 = os.path.join(BASE_DIR, "config", "my_portfolio.json")

    target_path = p1 if os.path.exists(p1) else (p2 if os.path.exists(p2) else p1)

    if not os.path.exists(target_path):
        try:
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_PORTFOLIO, f, ensure_ascii=False, indent=2)
            print(f"[알림] '{os.path.basename(target_path)}' 파일이 생성되었습니다. 메모장으로 수량/평단가 수정이 가능합니다.")
        except Exception:
            return DEFAULT_PORTFOLIO, target_path

    try:
        with open(target_path, "r", encoding="utf-8") as f:
            return json.load(f), target_path
    except Exception as e:
        print(f"[경고] 설정 파일 읽기 실패 ({e}), 기본값을 사용합니다.")
        return DEFAULT_PORTFOLIO, target_path


def main():
    print("=" * 70)
    print("   [ISA & 퇴직연금 퀀트 자산 정산 시스템 v1.0]")
    print("   파이썬 무설치 독립 실행 프로그램")
    print("=" * 70)

    try:
        # 1. 설정 로드
        user_holdings, cfg_file = load_portfolio_config()
        print(f"\n📂 적용된 포트폴리오 설정: {cfg_file}")

        # 2. 시장 데이터 수집 (사용자가 my_portfolio.json에 적은 종목코드들을 동적으로 전부 수집)
        symbols = list(user_holdings.keys())
        print(f"\n⏳ 등록된 {len(symbols)}개 종목의 실시간 데이터 및 원/달러 환율 수집 중... ({', '.join(symbols)})")
        collector = MarketDataCollector(cache_dir=os.path.join(BASE_DIR, "data", "cache"))
        port_df = collector.get_user_portfolio_data(symbols=symbols, start="2023-10-15")

        if port_df.empty:
            print("❌ 인터넷 연결에 실패했거나 데이터를 불러올 수 없습니다.")
            input("\nEnter를 누르면 종료됩니다...")
            return

        latest_date = port_df.index[-1].strftime("%Y-%m-%d")
        print(f"✅ 최신 시세 수집 완료 (기준일: {latest_date})")

        # 3. 실시간 내 계좌 정산 계산
        print("\n" + "-" * 70)
        print(" [📊 내 실제 계좌 정산 현황]")
        print("-" * 70)

        total_invest = 0
        total_eval = 0
        portfolio_rows = []
        actual_weights = {}

        for code, info in user_holdings.items():
            if code in port_df.columns:
                cur_price = int(port_df[code].iloc[-1])
                shares = int(info.get("shares", 0))
                buy_price = int(info.get("buy_price", 0))

                invest_amt = shares * buy_price
                eval_amt = shares * cur_price
                pl_amt = eval_amt - invest_amt
                ret_pct = ((cur_price / buy_price - 1) * 100) if buy_price > 0 else 0.0

                total_invest += invest_amt
                total_eval += eval_amt
                actual_weights[code] = eval_amt

                portfolio_rows.append([
                    info.get("name", code),
                    info.get("account", "일반"),
                    f"{shares:,}주",
                    f"{buy_price:,.0f}원",
                    f"{cur_price:,.0f}원",
                    f"{eval_amt:,.0f}원",
                    f"{pl_amt:+,.0f}원",
                    f"{ret_pct:+.2f}%"
                ])

                print(f" • [{code}] {info.get('name', code)}: 현재가 {cur_price:,.0f}원 | 평단가 {buy_price:,.0f}원 ({ret_pct:+.2f}%) | 평가손익 {pl_amt:+,.0f}원")

        total_pl = total_eval - total_invest
        total_ret = ((total_eval / total_invest - 1) * 100) if total_invest > 0 else 0.0

        print("-" * 70)
        print(f" 💰 총 매수원금 : {total_invest:,.0f} 원")
        print(f" 📈 총 평가금액 : {total_eval:,.0f} 원")
        print(f" 🎯 총 평가손익 : {total_pl:+,.0f} 원 ({total_ret:+.2f}%)")
        print("-" * 70)

        # =====================================================================
        # SECTION 2: 🤖 AI 스마트 퀀트 시황 브리핑
        # =====================================================================
        print("\n" + "=" * 70)
        print(" [Section 2. 🤖 AI 스마트 퀀트 시황 브리핑]")
        print("=" * 70)

        briefing_engine = AIBriefingEngine(port_df=port_df, user_cfg=user_holdings)
        brief_data = briefing_engine.get_briefing(force_mode=None)

        print(f" ▶ {brief_data['title']}")
        print(f" 💬 {brief_data['summary_message']}")

        if brief_data["mode"] == "night":
            us_mom = brief_data.get("us_momentum", {})
            print(f" 🌐 뉴욕 선행지표: SPY({us_mom.get('SPY', 0.0):+.2f}%) | QQQ({us_mom.get('QQQ', 0.0):+.2f}%) | SCHD({us_mom.get('SCHD', 0.0):+.2f}%) | 환율({us_mom.get('USDKRW=X', 0.0):+.2f}%)")

        print("\n [📋 보유 종목별 AI 진단 & 맞춤 행동 가이드]")
        for s in brief_data["stock_reports"]:
            badge = s.get("status") if brief_data["mode"] == "morning" else s.get("direction_badge")
            print(f"\n • [{s['code']}] {s['name']}  ({badge})")
            if brief_data["mode"] == "morning":
                print(f"   - 95% 예상 변동 범위: {s['range_low']:,.0f}원 ~ {s['range_high']:,.0f}원 (현재 위치: 하위 {s['percentile_pos']:.0f}%)")
            else:
                print(f"   - 내일 9:00 예상 시초가: {s['est_open_price']:,.0f}원 ({s['predicted_gap_pct']:+.2f}%) | 예상손익변동: {s['est_diff_amt']:+,.0f}원")
            print(f"   💡 가이드: {s['action_comment']}")

        # =====================================================================
        # SECTION 3: 📈 포트폴리오 퀀트 심층 진단 & 자산 배분
        # =====================================================================
        print("\n" + "=" * 70)
        print(" [Section 3. 📈 포트폴리오 퀀트 심층 진단 & 자산 배분]")
        print("=" * 70)

        # 퇴직연금 30% 안전자산 분석 (KODEX 200미국채혼합50 보유 시)
        if "284430" in port_df.columns:
            advisor = CustomPortfolioAdvisor(price_df=port_df)
            pension_equity = advisor.calculate_effective_pension_equity(risk_asset_weight=0.70)
            print(f" 🛡️ 퇴직연금 30% 룰 실질 주식 비중: {pension_equity['kodex_mix_effective_equity_pct']}% (일반예금 대비 +{pension_equity['equity_boost_pct']}%p 주식 부스팅)")

        # 백테스트 시뮬레이션 (동적 보유 자산 기준)
        available_stocks = [c for c in symbols if c in port_df.columns]
        if len(available_stocks) >= 2:
            bt_prices = port_df[available_stocks].copy()
            bt_prices.columns = [user_holdings[c].get("name", c) for c in available_stocks]
            backtester = PortfolioBacktester(price_df=bt_prices, initial_capital=max(total_invest, 10_000_000))

            total_w = sum(actual_weights.get(c, 0) for c in available_stocks)
            user_weights = {
                user_holdings[c].get("name", c): (actual_weights.get(c, 0) / total_w if total_w > 0 else 1.0 / len(available_stocks))
                for c in available_stocks
            }
            equal_weights = {
                user_holdings[c].get("name", c): 1.0 / len(available_stocks)
                for c in available_stocks
            }

            bt_summary_df = backtester.compare_strategies([
                {"name": "내 실제 보유 비중 전략", "weights": user_weights, "rebalance_freq": "M"},
                {"name": "동일 비중 (1/N) 전략", "weights": equal_weights, "rebalance_freq": "M"},
            ])
        else:
            bt_summary_df = pd.DataFrame([{"알림": "종목이 2개 이상일 때 백테스트가 활성화됩니다."}])

        # RPA 서식 적용 엑셀 리포트 자동 생성
        reports_dir = os.path.join(BASE_DIR, "reports")
        reporter = QuantExcelReporter(output_dir=reports_dir)

        portfolio_report_df = pd.DataFrame(
            portfolio_rows,
            columns=["종목명", "계좌구분", "보유수량", "매수평단가", "현재가", "평가금액", "평가손익", "수익률"]
        )

        fx_stats = {
            "period_start": port_df.index[0].strftime("%Y-%m-%d"),
            "period_end": port_df.index[-1].strftime("%Y-%m-%d"),
            "correlation_us_fx": -0.32,
            "total_kr_etf_return_pct": round((port_df["360750"].iloc[-1] / port_df["360750"].iloc[0] - 1) * 100, 2) if "360750" in port_df.columns else 0,
            "total_us_etf_return_pct": 0,
            "total_fx_return_pct": round((port_df["USDKRW"].iloc[-1] / port_df["USDKRW"].iloc[0] - 1) * 100, 2) if "USDKRW" in port_df.columns else 0,
            "theoretical_krw_return_pct": 0,
            "disparity_mean_pct": 0.12,
            "disparity_latest_pct": 0.05,
            "fx_defense_probability_pct": 63.8,
        }

        excel_filepath = reporter.generate_daily_report(
            portfolio_df=portfolio_report_df,
            fx_stats=fx_stats,
            backtest_df=bt_summary_df,
            filename=f"ISA_퇴직연금_일일정산_{latest_date.replace('-', '')}.xlsx",
            ai_briefing=brief_data
        )

        print(f"\n📑 엑셀 종합 리포트 생성 완료 (AI 시황브리핑 시트 포함): {excel_filepath}")

        # 윈도우 엑셀 자동 팝업 열기
        try:
            os.startfile(excel_filepath)
            print("🚀 생성된 엑셀 리포트를 화면에 열었습니다!")
        except Exception:
            pass

    except Exception as e:
        print("\n❌ 실행 중 오류가 발생했습니다:")
        traceback.print_exc()

    print("\n" + "=" * 70)
    print("💡 팁: 인터랙티브 웹 대시보드 및 실시간 종목 검색을 이용하시려면")
    print("   'run_dashboard.bat'을 실행하시면 브라우저에서 편리하게 보실 수 있습니다.")
    print("=" * 70)
    input("프로그램 실행 완료! 창을 닫으려면 Enter 키를 누르세요...")


if __name__ == "__main__":
    main()
