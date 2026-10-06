"""Restrained dashboard styling, with native accessible Streamlit controls."""
from html import escape
import streamlit as st


def apply_styles():
    st.markdown('''<style>
    :root {--ink:#e3edf7;--muted:#899eb6;--line:#22334a;--accent:#36d7e5;}
    .stApp {background:#080d16;color:var(--ink);}
    .block-container {max-width:1450px;padding:1.4rem 1.6rem 2rem;}
    [data-testid="stSidebar"] {background:#0d1523;border-right:1px solid var(--line);min-width:245px;}
    [data-testid="stHeader"] {background:#080d16;}
    [data-testid="stSidebar"] .block-container {padding:2rem 1.2rem;}
    h1,h2,h3 {letter-spacing:-.035em;color:var(--ink);}
    h1 {font-size:2rem!important;font-weight:650!important;}
    h3 {font-size:1.1rem!important;}
    [data-testid="stVerticalBlock"] {gap:.8rem;}
    [data-testid="stVerticalBlockBorderWrapper"]>div {background:#101a2a;border-radius:12px;}
    [data-testid="stMetric"] {background:#101a2a;border:1px solid var(--line);padding:18px 20px;border-radius:12px;}
    [data-testid="stMetricLabel"] {color:var(--muted);font-size:13px;}
    [data-testid="stMetricValue"] {font-size:29px;letter-spacing:-.04em;}
    [data-testid="stBaseButton-primary"] {background:#134653;border-color:#2f99a8;color:#b0f5fa;}
    [data-testid="stBaseButton-primary"]:hover {background:#1b5866;border-color:#36d7e5;}
    [data-testid="stImage"] img {border-radius:9px;}
    .brand {display:flex;align-items:center;gap:11px;margin:0 0 32px;}
    .brandmark {background:#134653;color:#36d7e5;width:38px;height:40px;border-radius:12px 12px 17px 17px;
      display:grid;place-items:center;font-weight:700;font-size:17px;}
    .brandname {font-size:20px;font-weight:700;letter-spacing:-.7px;}
    .brandnote {font-size:10px;color:#849198;letter-spacing:1.5px;}
    .eyebrow {font-size:11px;letter-spacing:1.5px;color:#829096;font-weight:600;text-transform:uppercase;}
    .pagehead {display:flex;justify-content:space-between;align-items:center;margin:4px 0 16px;gap:12px;}
    .pagehead h1 {margin:8px 0 2px;padding:0;}
    .pagehead p {color:#738089;font-size:14px;margin:5px 0 0;}
    .pill {font-size:11px;font-weight:600;padding:7px 11px;border:1px solid #225366;
      border-radius:6px;white-space:nowrap;background:#113041;color:#36d7e5;}
    .dot {display:inline-block;width:6px;height:6px;border-radius:50%;background:currentColor;margin-right:6px;}
    .stats {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:6px 0 14px;}
    .stat {border:1px solid var(--line);background:#101a2a;border-radius:11px;padding:17px 19px;}
    .stat label {display:block;font-size:12px;color:#7c8990;margin-bottom:9px;}
    .stat strong {display:block;font-size:25px;font-weight:600;letter-spacing:-.7px;}
    .stat small {color:#7c8990;font-size:11px;}
    .feed-title {display:flex;justify-content:space-between;font-size:13px;font-weight:600;margin-bottom:12px;}
    .feed-title span {font-size:11px;color:#819099;font-weight:400;}
    .camera-empty {height:340px;background:#edf1f2;border:1px dashed #cad3d6;border-radius:8px;
      display:flex;flex-direction:column;align-items:center;justify-content:center;color:#6b7e88;}
    .camera-empty b {font-size:18px;color:#41525b;margin:18px 0 8px;}
    .camera-empty p {font-size:12px;margin:0;}
    .crosshair {width:52px;height:39px;border:2px solid #9caeb6;border-radius:8px;position:relative;}
    .crosshair:after {content:'';position:absolute;left:16px;top:9px;width:16px;height:16px;border:2px solid #9caeb6;border-radius:50%;}
    .score {font-size:66px;letter-spacing:-4px;font-weight:600;line-height:1.15;margin:14px 0 2px;}
    .score small {font-size:17px;color:#a0aab0;letter-spacing:0;}
    .riskbar {height:7px;background:#edf0f1;border-radius:10px;overflow:hidden;margin:16px 0 12px;}
    .riskbar i {height:100%;display:block;border-radius:10px;}
    .indicator {display:flex;justify-content:space-between;gap:10px;padding:10px 0;border-bottom:1px solid #edf0f1;font-size:12px;color:#738089;}
    .indicator b {color:#b4dbed;font-weight:550;text-align:right;}
    .safety-note {color:#839097;font-size:11px;line-height:1.6;margin:18px 0 10px;}
    .notice {border:1px solid #6d5231;background:#292016;padding:14px 17px;border-radius:9px;margin-bottom:12px;color:#f6b64c;}
    .notice strong {display:block;font-size:15px;margin-bottom:4px;}
    .notice span {font-size:12px;}
    .critical {border:1px solid #804548;background:#331c24;color:#fa726e;}
    .event {display:grid;grid-template-columns:75px 1fr auto;gap:16px;padding:12px 0;border-bottom:1px solid #22334a;align-items:center;font-size:12px;}
    .event time {color:#89969c;font-variant-numeric:tabular-nums;}
    .event b {font-weight:550;color:#b4dbed;}
    .event p {margin:3px 0 0;font-size:11px;color:#839097;}
    .event em {font-style:normal;color:#89969c;font-size:11px;}
    @media(max-width:800px) {.block-container{padding:1.3rem 1rem;}.stats{grid-template-columns:repeat(2,1fr);}.pagehead{align-items:flex-start;}.score{font-size:50px;}.camera-empty{height:240px;}}
    </style>''', unsafe_allow_html=True)


def heading(title, subtitle, badge="LOCAL WORKSPACE"):
    st.markdown(f'<div class="pagehead"><div><div class="eyebrow">DRIVER SAFETY / WORKSPACE</div><h1>{escape(title)}</h1><p>{escape(subtitle)}</p></div><div class="pill"><i class="dot"></i>{escape(badge)}</div></div>', unsafe_allow_html=True)


def cards(items):
    content = "".join(f'<div class="stat"><label>{escape(label)}</label><strong>{escape(str(value))}</strong><small>{escape(note)}</small></div>' for label, value, note in items)
    st.markdown(f'<div class="stats">{content}</div>', unsafe_allow_html=True)


def notice(title, message, critical=False):
    st.markdown(f'<div class="notice {"critical" if critical else ""}"><strong>{escape(title)}</strong><span>{escape(message)}</span></div>', unsafe_allow_html=True)


def timeline(events):
    if not events:
        st.caption("Chưa có sự kiện được ghi nhận.")
        return
    from datetime import datetime
    lines = []
    for event in reversed(events):
        try:
            when = datetime.fromisoformat(event["timestamp"]).astimezone().strftime("%H:%M:%S")
        except (ValueError, TypeError):
            when = "—"
        lines.append(f'<div class="event"><time>{when}</time><div><b>{escape(event["event_type"])}</b><p>{escape(event["description"] or "")}</p></div><em>{event["risk_score"]:.0f}/100</em></div>')
    st.markdown("".join(lines), unsafe_allow_html=True)
