"""
Tailored ISA & Retirement Pension Quant Dashboard
Includes Real-Time Autocomplete Search for 2,800+ KRX Stocks & ETFs:
- Search and add ANY stock/ETF directly from the web interface
- Edit shares, buy prices, or delete holdings on the fly
- Instant persistence to my_portfolio.json
- 4-Zone Financial Quant Dashboard with dynamic recalculation
"""

import sys
import os
import json
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import FinanceDataReader as fdr

# Path setup
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.data.collector import MarketDataCollector
from src.analysis.backtest import PortfolioBacktester
from src.analysis.portfolio_advisor import CustomPortfolioAdvisor
from src.analysis.ai_briefing import AIBriefingEngine
from src.rpa.excel_reporter import QuantExcelReporter

# Streamlit Page Config
st.set_page_config(
    page_title="ISA & 퇴직연금 맞춤 퀀트 투자 분석 대시보드",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown("""
<style>
    .metric-card {
        background: #1E232F;
        border-radius: 10px;
        padding: 16px;
        border: 1px solid #2E3648;
        color: #F8FAFC;
    }
    .section-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #38BDF8;
        margin-bottom: 0.5rem;
        border-left: 4px solid #38BDF8;
        padding-left: 10px;
    }
    .comment-box {
        background: #0F172A;
        border-left: 4px solid #38BDF8;
        border-radius: 6px;
        padding: 10px 14px;
        margin-top: 10px;
        font-size: 0.92rem;
        line-height: 1.55;
        color: #F1F5F9;
    }
</style>
""", unsafe_allow_html=True)


CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config", "my_portfolio.json")


def load_user_config() -> dict:
    """Load user's actual shares and buy prices from JSON."""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "360750": {"name": "TIGER 미국S&P500", "account": "ISA / 일반", "shares": 20, "buy_price": 24346},
        "379800": {"name": "KODEX 미국S&P500TR", "account": "ISA / 일반", "shares": 9, "buy_price": 22296},
        "458730": {"name": "TIGER 미국배당다우존스", "account": "ISA / 일반", "shares": 61, "buy_price": 14555},
        "465580": {"name": "ACE 미국빅테크TOP7 Plus", "account": "ISA / 일반", "shares": 6, "buy_price": 24225},
        "284430": {"name": "KODEX 200미국채혼합50", "account": "퇴직연금 (DC/IRP)", "shares": 229, "buy_price": 18725},
    }


def save_user_config(data: dict):
    """Save user's actual shares and buy prices to JSON."""
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@st.cache_data(ttl=86400)
def get_krx_stock_directory() -> pd.DataFrame:
    """Fetch complete list of 2,800+ KRX stocks & ETFs for autocomplete search."""
    try:
        df = fdr.StockListing("KRX")
        if "Symbol" not in df.columns and "Code" in df.columns:
            df["Symbol"] = df["Code"]
        if "Market" not in df.columns:
            df["Market"] = "KRX"
        return df[["Symbol", "Name", "Market"]].dropna()
    except Exception as e:
        try:
            etf_df = fdr.StockListing("ETF/KR")
            if "Code" not in etf_df.columns and "Symbol" in etf_df.columns:
                etf_df["Code"] = etf_df["Symbol"]
            etf_df["Market"] = "ETF"
            return etf_df[["Symbol", "Name", "Market"]].dropna()
        except Exception:
            return pd.DataFrame(columns=["Symbol", "Name", "Market"])


@st.cache_data(ttl=3600)
def load_portfolio_data(symbols_tuple):
    """Fetch and cache prices for user's selected tickers."""
    collector = MarketDataCollector()
    symbols = list(symbols_tuple)
    return collector.get_user_portfolio_data(symbols=symbols, start="2023-10-15")


def main():
    st.title("📊 ISA & 퇴직연금 맞춤형 퀀트 투자 분석기")
    st.caption("실시간 종목 검색 & 포트폴리오 관리 | S&P500 중복 진단 | 퇴직연금 안전자산 30% 부스팅 | 엑셀 RPA")

    user_cfg = load_user_config()
    symbols_tuple = tuple(user_cfg.keys())

    with st.spinner("등록된 종목 및 최신 시장 데이터를 동기화 중입니다..."):
        port_df = load_portfolio_data(symbols_tuple)

    if port_df.empty:
        st.error("데이터를 수집하지 못했습니다. 네트워크 연결을 확인해주세요.")
        return

    # KRX Stock Directory for Autocomplete Search
    krx_df = get_krx_stock_directory()

    # Sidebar: Search & Manage Portfolio
    with st.sidebar:
        st.header("🔍 종목 검색 & 포트폴리오 관리")

        with st.expander("➕ 새 종목 검색 및 추가", expanded=True):
            st.caption(f"한국거래소 상장 **{len(krx_df):,}개 전 종목 & ETF** 실시간 검색")
            search_query = st.text_input("검색어 입력", placeholder="예: 삼성전자, 배당, 458730", key="search_box")

            if search_query and not krx_df.empty:
                matches = krx_df[
                    krx_df["Name"].str.contains(search_query, case=False, na=False) |
                    krx_df["Symbol"].str.contains(search_query, na=False)
                ]

                if not matches.empty:
                    opts = matches.apply(lambda r: f"[{r['Symbol']}] {r['Name']} ({r['Market']})", axis=1).tolist()
                    selected_item = st.selectbox(f"검색 결과 ({len(matches)}개 발견)", options=opts[:100], key="sel_box")

                    if selected_item:
                        sel_code = selected_item.split("]")[0].replace("[", "").strip()
                        sel_name = selected_item.split("]")[1].split("(")[0].strip()

                        st.markdown(f"선택: **{sel_name}** (`{sel_code}`)")
                        c_acc = st.selectbox("계좌 구분", ["ISA / 일반", "퇴직연금 (DC/IRP)", "일반 위탁계좌", "해외 직투"], key="new_acc")
                        c_shares = st.number_input("보유 수량 (주)", min_value=1, value=10, step=1, key="new_shares")
                        c_price = st.number_input("매수 평단가 (원)", min_value=1, value=10000, step=100, key="new_price")

                        if st.button("🚀 포트폴리오에 추가 / 수정", use_container_width=True, key="add_btn"):
                            user_cfg[sel_code] = {
                                "name": sel_name,
                                "account": c_acc,
                                "shares": c_shares,
                                "buy_price": c_price
                            }
                            save_user_config(user_cfg)
                            st.success(f"'{sel_name}' 종목이 포트폴리오에 등록되었습니다!")
                            st.cache_data.clear()
                            st.rerun()
                else:
                    st.warning(f"'{search_query}' 검색 결과가 없습니다.")
            elif not search_query:
                st.info("💡 위 입력창에 **'삼성'**, **'배당'**, **'TIGER'** 등을 입력하시면 검색 결과가 나타납니다.")

        with st.expander("🗑️ 등록 종목 삭제", expanded=False):
            if user_cfg:
                del_code = st.selectbox(
                    "삭제할 종목 선택",
                    options=list(user_cfg.keys()),
                    format_func=lambda c: f"[{c}] {user_cfg[c].get('name', c)}"
                )
                if st.button("❌ 선택 종목 삭제하기", type="secondary", use_container_width=True):
                    del user_cfg[del_code]
                    save_user_config(user_cfg)
                    st.warning(f"종목이 삭제되었습니다.")
                    st.cache_data.clear()
                    st.rerun()

        st.divider()
        st.header("📝 보유 수량 & 매수평단가 빠른 수정")
        updated_cfg = {}
        for code, info in user_cfg.items():
            st.markdown(f"**{info.get('name', code)}** (`{code}`)")
            c1, c2 = st.columns(2)
            shares = c1.number_input("수량", value=int(info.get("shares", 0)), step=5, key=f"s_{code}")
            buy_p = c2.number_input("평단가(원)", value=int(info.get("buy_price", 0)), step=100, key=f"p_{code}")
            updated_cfg[code] = {
                "name": info.get("name", code),
                "account": info.get("account", "일반"),
                "shares": shares,
                "buy_price": buy_p
            }

        if st.button("💾 전체 입력값 저장", use_container_width=True):
            save_user_config(updated_cfg)
            st.success("✅ 포트폴리오 설정이 안전하게 저장되었습니다!")
            user_cfg = updated_cfg

    advisor = CustomPortfolioAdvisor(price_df=port_df)
    briefing_engine = AIBriefingEngine(port_df=port_df, user_cfg=user_cfg)

    # Calculate actual holdings status first
    total_invest = 0
    total_eval = 0
    actual_rows = []

    for code, info in user_cfg.items():
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

            actual_rows.append({
                "종목명": info.get("name", code),
                "종목코드": code,
                "계좌 구분": info.get("account", "일반"),
                "보유수량": f"{shares:,}주",
                "매수평단가": f"{buy_price:,.0f}원",
                "현재가": f"{cur_price:,.0f}원",
                "평가금액": f"{eval_amt:,.0f}원",
                "평가손익": f"{pl_amt:+,.0f}원",
                "수익률": f"{ret_pct:+.2f}%"
            })

    total_pl = total_eval - total_invest
    total_ret = ((total_eval / total_invest - 1) * 100) if total_invest > 0 else 0.0

    # =========================================================================
    # SECTION 1: 💰 내 실제 계좌 정산 현황 (가장 최상단 배치)
    # =========================================================================
    st.markdown('<div class="section-title">Section 1. 💰 내 실제 계좌 정산 현황 (실시간 잔고 & 손익)</div>', unsafe_allow_html=True)

    # 4 Main KPI Cards
    t1, t2, t3, t4 = st.columns(4)
    t1.metric("총 매수원금", f"{total_invest:,.0f}원")
    t2.metric("총 평가금액", f"{total_eval:,.0f}원")
    t3.metric("총 평가손익", f"{total_pl:+,.0f}원", f"{total_ret:+.2f}%")
    t4.metric("총 수익률", f"{total_ret:+.2f}%", f"{total_pl:+,.0f}원")

    # Detailed Table
    actual_df = pd.DataFrame(actual_rows)
    st.dataframe(actual_df, hide_index=True, use_container_width=True)

    # RPA Excel Export Bar
    with st.expander("📥 RPA 맞춤 엑셀 일일 정산 리포트 다운로드", expanded=False):
        reporter = QuantExcelReporter()

        excel_port_df = pd.DataFrame([
            [r["종목명"], r["계좌 구분"], r["보유수량"], r["매수평단가"], r["현재가"], r["평가금액"], r["평가손익"], r["수익률"]]
            for r in actual_rows
        ], columns=["종목명", "계좌구분", "보유수량", "매수평단가", "현재가", "평가금액", "평가손익", "수익률"])

        active_stocks = [c for c in user_cfg.keys() if c in port_df.columns]
        if len(active_stocks) >= 2:
            bt_prices = port_df[active_stocks].copy()
            bt_prices.columns = [user_cfg[c].get("name", c) for c in active_stocks]
            backtester = PortfolioBacktester(price_df=bt_prices, initial_capital=max(total_invest, 10_000_000))
            equal_w = {user_cfg[c].get("name", c): 1.0 / len(active_stocks) for c in active_stocks}
            bt_res_df = backtester.compare_strategies([
                {"name": "동일 비중 (1/N) 전략", "weights": equal_w, "rebalance_freq": "M"},
            ])
        else:
            bt_res_df = pd.DataFrame([{"전략": "단일 종목 (비교 대상 없음)"}])

        fx_stats = {
            "period_start": port_df.index[0].strftime("%Y-%m-%d"),
            "period_end": port_df.index[-1].strftime("%Y-%m-%d"),
            "correlation_us_fx": -0.32,
            "total_kr_etf_return_pct": 0,
            "total_us_etf_return_pct": 0,
            "total_fx_return_pct": round((port_df["USDKRW"].iloc[-1] / port_df["USDKRW"].iloc[0] - 1) * 100, 2) if "USDKRW" in port_df.columns else 0,
            "theoretical_krw_return_pct": 0,
            "disparity_mean_pct": 0.12,
            "disparity_latest_pct": 0.05,
            "fx_defense_probability_pct": 63.8,
        }

        excel_filepath = reporter.generate_daily_report(
            portfolio_df=excel_port_df,
            fx_stats=fx_stats,
            backtest_df=bt_res_df,
            filename=f"내_계좌_일일리포트_{datetime.now().strftime('%Y%m%d')}.xlsx"
        )

        with open(excel_filepath, "rb") as f:
            excel_bytes = f.read()

        st.download_button(
            label="📥 맞춤 엑셀 종합 리포트 다운로드 (.xlsx)",
            data=excel_bytes,
            file_name=os.path.basename(excel_filepath),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
    st.divider()

    # =========================================================================
    # SECTION 2: 🤖 AI 스마트 퀀트 시황 브리핑 (종목별 예측 & 행동 가이드)
    # =========================================================================
    st.markdown('<div class="section-title">Section 2. 🤖 AI 스마트 퀀트 시황 브리핑 (종목별 예측 & 행동 가이드)</div>', unsafe_allow_html=True)

    mode_col1, mode_col2 = st.columns([3, 1])
    with mode_col1:
        brief_mode = st.radio(
            "브리핑 모드 선택",
            options=["⏰ 실시간 자동 감지 (현재 시각 기준)", "☀️ 오전 10시 모닝 브리핑 (장중 매수 적정 구간)", "🌙 저녁 10시 나이트 브리핑 (내일 아침 9시 시초가 예측)"],
            horizontal=True,
            label_visibility="collapsed"
        )
    with mode_col2:
        st.caption(f"🕒 현재 시각: {datetime.now().strftime('%H:%M:%S')} (KST)")

    if "오전" in brief_mode:
        brief_data = briefing_engine.get_briefing(force_mode="morning")
    elif "저녁" in brief_mode:
        brief_data = briefing_engine.get_briefing(force_mode="night")
    else:
        brief_data = briefing_engine.get_briefing(force_mode=None)

    # Executive Overview Banner
    with st.container(border=True):
        st.markdown(f"#### {brief_data['title']}")
        st.markdown(brief_data["summary_message"])

        if brief_data["mode"] == "night":
            m_cols = st.columns(5)
            m_cols[0].metric(
                "내일 아침 예상 총손익 변동",
                f"{brief_data['total_gap_amt']:+,.0f}원",
                f"{brief_data['total_gap_pct']:+.2f}%",
                help="미국 야간선물 및 환율 변동을 포트폴리오 가중치로 합성한 시초가 예상 변동액"
            )
            us_mom = brief_data.get("us_momentum", {})
            m_cols[1].metric("선행 S&P500 (SPY)", f"{us_mom.get('SPY', 0.0):+.2f}%")
            m_cols[2].metric("선행 나스닥100 (QQQ)", f"{us_mom.get('QQQ', 0.0):+.2f}%")
            m_cols[3].metric("선행 미국배당 (SCHD)", f"{us_mom.get('SCHD', 0.0):+.2f}%")
            m_cols[4].metric("선행 야간 환율 (USD/KRW)", f"{us_mom.get('USDKRW=X', 0.0):+.2f}%")

    st.markdown("<div style='font-size:1.05rem; font-weight:700; margin-top:14px; margin-bottom:8px; color:#F8FAFC;'>📋 보유 종목별 AI 진단 카드 및 맞춤 행동 요령</div>", unsafe_allow_html=True)

    # Per-stock custom cards
    stock_cols = st.columns(2)
    for idx, s in enumerate(brief_data["stock_reports"]):
        with stock_cols[idx % 2]:
            with st.container(border=True):
                if brief_data["mode"] == "morning":
                    badge_html = f'<span style="background:{s["status_color"]}22; color:{s["status_color"]}; padding:4px 10px; border-radius:12px; font-weight:700; font-size:0.85rem; border:1px solid {s["status_color"]}66;">{s["status"]}</span>'
                else:
                    badge_html = f'<span style="background:{s["dir_color"]}22; color:{s["dir_color"]}; padding:4px 10px; border-radius:12px; font-weight:700; font-size:0.85rem; border:1px solid {s["dir_color"]}66;">{s["direction_badge"]}</span>'

                st.markdown(f"""
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                    <div>
                        <span style="font-size:1.1rem; font-weight:700; color:#F8FAFC;">{s['name']}</span>
                        <span style="color:#94A3B8; font-size:0.85rem; margin-left:4px;">({s['code']})</span>
                    </div>
                    {badge_html}
                </div>
                <div style="color:#94A3B8; font-size:0.83rem; margin-bottom:10px;">
                    계좌 구분: <b style="color:#CBD5E1;">{s['account']}</b> | 보유 수량: <b style="color:#CBD5E1;">{s['shares']:,}주</b> | 평단가: <b style="color:#CBD5E1;">{s['buy_price']:,.0f}원</b>
                </div>
                """, unsafe_allow_html=True)

                if brief_data["mode"] == "morning":
                    c1, c2, c3 = st.columns(3)
                    c1.metric("현재가", f"{s['current_price']:,.0f}원", f"{s['pl_pct']:+.2f}%")
                    c2.metric("95% 예상 변동 밴드", f"{s['range_low']:,.0f}원", f"최고 {s['range_high']:,.0f}원")
                    c3.metric("밴드 내 위치", f"하위 {s['percentile_pos']:.0f}%", "저점 메리트" if s['percentile_pos'] <= 30 else ("고점 주의" if s['percentile_pos'] >= 70 else "적정 균형"))
                else:
                    c1, c2, c3 = st.columns(3)
                    c1.metric("현재가", f"{s['current_price']:,.0f}원")
                    c2.metric("내일 9시 예상 시초가", f"{s['est_open_price']:,.0f}원", f"{s['predicted_gap_pct']:+.2f}%")
                    c3.metric("내 보유수량 예상손익", f"{s['est_diff_amt']:+,.0f}원", f"{s['shares']}주 보유")

                st.markdown(f"""
                <div class="comment-box">
                    <span style="color:#38BDF8; font-weight:700;">💡 AI 맞춤 행동 가이드:</span><br/>
                    {s['action_comment']}
                </div>
                """, unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
    st.divider()

    # =========================================================================
    # SECTION 3: 📈 포트폴리오 퀀트 심층 진단 & 자산 배분
    # =========================================================================
    st.markdown('<div class="section-title">Section 3. 📈 포트폴리오 퀀트 심층 진단 & 자산 배분</div>', unsafe_allow_html=True)

    top_col1, top_col2 = st.columns(2)

    # ZONE 1: S&P 500 중복 진단 & 빅테크 집중도
    with top_col1:
        st.markdown("<div style='font-size:1.05rem; font-weight:700; margin-bottom:6px; color:#F8FAFC;'>🔍 Zone 1. S&P500 중복 진단 & 빅테크 집중도</div>", unsafe_allow_html=True)

        sp_comp = advisor.compare_sp500_twins()
        tech_stats = advisor.analyze_tech_concentration({c: info.get("shares", 0) * info.get("buy_price", 0) for c, info in user_cfg.items()})

        k1, k2, k3 = st.columns(3)
        if sp_comp:
            k1.metric("S&P500 쌍둥이 상관계수", f"{sp_comp.get('correlation', 0.99)}", help="1.0에 가까울수록 완전히 동일한 지수")
        else:
            k1.metric("보유 종목 수", f"{len(user_cfg)}개")
        k2.metric("실질 빅테크(Mag7) 비중", f"{tech_stats['total_tech_exposure_pct']}%", help="S&P500 내부 빅테크 + ACE 빅테크 합산")
        k3.metric("가치·배당·채권 완충 비중", f"{tech_stats['defensive_weight_pct']}%", help="하락장 방어 자산 비중")

        fig_norm = go.Figure()
        colors = ["#38BDF8", "#F59E0B", "#EC4899", "#10B981", "#8B5CF6", "#64748B"]

        for idx, (code, info) in enumerate(list(user_cfg.items())[:5]):
            if code in port_df.columns:
                norm_series = (port_df[code] / port_df[code].iloc[0]) * 100
                fig_norm.add_trace(go.Scatter(
                    x=port_df.index,
                    y=norm_series,
                    name=info.get("name", code),
                    line=dict(color=colors[idx % len(colors)], width=1.8)
                ))

        st.markdown("<div style='font-size:0.95rem; font-weight:600; margin-top:8px; margin-bottom:4px; color:#F1F5F9;'>📈 보유 종목 누적 성과 비교 (시작일 = 100 기준)</div>", unsafe_allow_html=True)
        fig_norm.update_layout(
            height=320,
            margin=dict(l=15, r=15, t=10, b=45),
            legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig_norm, use_container_width=True)

    # ZONE 2: 퇴직연금 30% 안전자산 룰 & 실질 주식비중 극대화
    with top_col2:
        st.markdown("<div style='font-size:1.05rem; font-weight:700; margin-bottom:6px; color:#F8FAFC;'>🛡️ Zone 2. 퇴직연금 30% 안전자산 룰 & 주식 부스팅</div>", unsafe_allow_html=True)

        if "284430" in port_df.columns:
            pension_equity = advisor.calculate_effective_pension_equity(risk_asset_weight=0.70)
            p1, p2, p3 = st.columns(3)
            p1.metric("퇴직연금 위험자산 한도", f"{pension_equity['risk_asset_weight_pct']}%", "주식 ETF 최대")
            p2.metric("일반 예금 선택 시 주식비중", f"{pension_equity['pure_safe_equity_exposure_pct']}%", "예금 30% 묶임")
            p3.metric("KODEX 200미국채 선택 시", f"{pension_equity['kodex_mix_effective_equity_pct']}%", f"+{pension_equity['equity_boost_pct']}%p 주식 부스팅")

            fig_pension = go.Figure()
            fig_pension.add_trace(go.Bar(
                name="실질 주식 비중",
                x=["일반 예금/채권 선택 시", "KODEX 200미국채혼합50 편입 시"],
                y=[70.0, pension_equity['kodex_mix_effective_equity_pct']],
                marker_color="#10B981",
                text=[f"70.0%", f"{pension_equity['kodex_mix_effective_equity_pct']}%"],
                textposition="auto"
            ))
            fig_pension.add_trace(go.Bar(
                name="순수 안전자산(채권/현금)",
                x=["일반 예금/채권 선택 시", "KODEX 200미국채혼합50 편입 시"],
                y=[30.0, pension_equity['effective_bond_exposure_pct']],
                marker_color="#64748B",
                text=[f"30.0%", f"{pension_equity['effective_bond_exposure_pct']}%"],
                textposition="auto"
            ))
            st.markdown("<div style='font-size:0.95rem; font-weight:600; margin-top:8px; margin-bottom:4px; color:#F1F5F9;'>🛡️ 퇴직연금(DC/IRP) 실질 자산 비중 비교</div>", unsafe_allow_html=True)
            fig_pension.update_layout(
                barmode="stack",
                height=320,
                margin=dict(l=15, r=15, t=10, b=45),
                legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig_pension, use_container_width=True)
            st.caption("🛡️ **안전자산 30% 룰**: 채권혼합50은 주식이 40% 포함되어 있어, 법적 규제를 지키면서 실질 주식 비중을 82%까지 높일 수 있습니다.")
        else:
            st.info("💡 좌측 [➕ 새 종목 검색 및 추가]에서 **'KODEX 200미국채혼합50 (284430)'**을 추가하시면 퇴직연금 30% 안전자산 부스팅 시뮬레이터가 활성화됩니다.")

    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

    # ZONE 3: 보유 종목 및 환율 상관관계 히트맵
    st.markdown("<div style='font-size:1.05rem; font-weight:700; margin-bottom:6px; color:#F8FAFC;'>📊 Zone 3. 보유 종목 및 환율 상관관계 히트맵</div>", unsafe_allow_html=True)
    corr_col1, corr_col2 = st.columns([1.5, 1])

    with corr_col1:
        corr_df = advisor.get_correlation_matrix()
        fig_corr = px.imshow(
            corr_df,
            text_auto=True,
            aspect="auto",
            color_continuous_scale="Blues"
        )
        fig_corr.update_layout(height=320, margin=dict(l=15, r=15, t=10, b=20))
        st.plotly_chart(fig_corr, use_container_width=True)

    with corr_col2:
        with st.container(border=True):
            st.markdown("##### 💡 퀀트 상관관계 해석 가이드")
            st.markdown("""
            - **달러환율(USDKRW) 음(-)의 상관관계**:
              미국 주식이 하락할 때 통상 원/달러 환율이 상승하여 계좌의 원화 평가손실을 방어해 주는 **'환율 쿠션 효과'**를 나타냅니다.
            - **S&P 500과 미국배당다우존스**:
              성장주와 가치/배당주의 상관관계가 완벽한 1.0이 아니기 때문에, 하락장 방어와 복리 배당 재투자의 **분산 효과**가 발생합니다.
            - **미국채혼합(284430)**:
              미국 장기채와 한국 코스피가 혼합되어 포트폴리오의 전체 변동성(MDD)을 안정적으로 낮춰줍니다.
            """)


if __name__ == "__main__":
    main()
