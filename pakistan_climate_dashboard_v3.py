"""
Pakistan Climate Dashboard v2
Features: Forecast, PDF Export, Drought Index, Urdu Support, Email Alerts
Run: streamlit run pakistan_climate_dashboard_v2.py
Install: pip install streamlit plotly pandas requests fpdf2 smtplib
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import requests
import smtplib
import io
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from fpdf import FPDF

# -----------------------------------------------------------
# Page config
# -----------------------------------------------------------
st.set_page_config(
    page_title="Pakistan Climate Dashboard",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .metric-card { background:#f8f9fa; border-radius:10px; padding:15px; text-align:center; border:1px solid #e9ecef; }
    .alert-box   { background:#fff3cd; border:1px solid #ffc107; border-radius:8px; padding:12px; margin:8px 0; }
    .drought-low    { color:#1D9E75; font-weight:600; }
    .drought-mod    { color:#BA7517; font-weight:600; }
    .drought-severe { color:#D85A30; font-weight:600; }
    .drought-extreme{ color:#A32D2D; font-weight:600; }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------
# Language strings (English / Urdu)
# -----------------------------------------------------------
LANG = {
    "en": {
        "title":        "Pakistan Climate Dashboard",
        "variable":     "Climate variable",
        "cities":       "Cities",
        "date_from":    "From",
        "date_to":      "To",
        "language":     "Language",
        "map":          "City map",
        "trend":        "Monthly trend",
        "compare":      "City comparison",
        "heatmap":      "Seasonal heatmap",
        "province":     "Province summary",
        "table":        "Monthly data table",
        "forecast":     "7-day forecast",
        "drought":      "Drought index",
        "alerts":       "Temperature alerts",
        "pdf_export":   "Export PDF report",
        "download_csv": "Download data as CSV",
        "alert_thresh": "Alert threshold (°C)",
        "alert_email":  "Your email",
        "smtp_host":    "SMTP host (e.g. smtp.gmail.com)",
        "smtp_pass":    "Email password / app password",
        "send_alert":   "Send alert email",
        "alert_sent":   "Alert email sent!",
        "alert_fail":   "Failed to send email",
        "no_alert":     "No cities exceed the threshold.",
        "drought_info": "Drought index is calculated from rainfall deficit vs long-term average.",
        "caption":      "Data: Open-Meteo API · Dashboard by Pakistan Climate Analytics",
        "gen_pdf":      "Generate & download PDF",
        "pdf_ready":    "PDF ready — click below to download",
        "vars": {
            "Temperature (°C)": "temperature_2m_mean",
            "Rainfall (mm)":    "precipitation_sum",
            "Wind Speed (km/h)":"wind_speed_10m_max",
            "Humidity (%)":     "relative_humidity_2m_mean",
        }
    },
    "ur": {
        "title":        "پاکستان موسمیاتی ڈیش بورڈ",
        "variable":     "موسمیاتی متغیر",
        "cities":       "شہر",
        "date_from":    "شروع",
        "date_to":      "آخر",
        "language":     "زبان",
        "map":          "شہر کا نقشہ",
        "trend":        "ماہانہ رجحان",
        "compare":      "شہروں کا موازنہ",
        "heatmap":      "موسمی ہیٹ میپ",
        "province":     "صوبہ خلاصہ",
        "table":        "ماہانہ ڈیٹا ٹیبل",
        "forecast":     "7 دن کی پیشگوئی",
        "drought":      "خشک سالی انڈیکس",
        "alerts":       "درجہ حرارت الرٹس",
        "pdf_export":   "PDF رپورٹ برآمد کریں",
        "download_csv": "CSV ڈاؤن لوڈ کریں",
        "alert_thresh": "الرٹ حد (°C)",
        "alert_email":  "آپ کا ای میل",
        "smtp_host":    "SMTP ہوسٹ",
        "smtp_pass":    "ای میل پاس ورڈ",
        "send_alert":   "الرٹ ای میل بھیجیں",
        "alert_sent":   "الرٹ ای میل بھیج دی گئی!",
        "alert_fail":   "ای میل بھیجنے میں ناکامی",
        "no_alert":     "کوئی شہر حد سے تجاوز نہیں کرتا۔",
        "drought_info": "خشک سالی انڈیکس بارش کی کمی سے حساب کیا جاتا ہے۔",
        "caption":      "ڈیٹا: Open-Meteo API · پاکستان کلائمیٹ اینالیٹکس",
        "gen_pdf":      "PDF بنائیں اور ڈاؤن لوڈ کریں",
        "pdf_ready":    "PDF تیار ہے — نیچے کلک کریں",
        "vars": {
            "درجہ حرارت (°C)":  "temperature_2m_mean",
            "بارش (mm)":        "precipitation_sum",
            "ہوا کی رفتار (km/h)": "wind_speed_10m_max",
            "نمی (%)":          "relative_humidity_2m_mean",
        }
    }
}

# -----------------------------------------------------------
# City & province config
# -----------------------------------------------------------
CITIES = {
    "Karachi":    {"lat": 24.86, "lon": 67.01, "province": "Sindh"},
    "Lahore":     {"lat": 31.55, "lon": 74.35, "province": "Punjab"},
    "Islamabad":  {"lat": 33.72, "lon": 73.06, "province": "Punjab"},
    "Peshawar":   {"lat": 34.01, "lon": 71.57, "province": "KPK"},
    "Quetta":     {"lat": 30.19, "lon": 66.99, "province": "Balochistan"},
    "Multan":     {"lat": 30.19, "lon": 71.47, "province": "Punjab"},
    "Faisalabad": {"lat": 31.42, "lon": 73.09, "province": "Punjab"},
    "Hyderabad":  {"lat": 25.37, "lon": 68.37, "province": "Sindh"},
    "Gwadar":     {"lat": 25.12, "lon": 62.32, "province": "Balochistan"},
    "Sukkur":     {"lat": 27.70, "lon": 68.85, "province": "Sindh"},
}

PROVINCE_COLORS = {
    "Punjab":      "#378ADD",
    "Sindh":       "#D85A30",
    "KPK":         "#1D9E75",
    "Balochistan": "#BA7517",
}

DROUGHT_NORMAL_RAIN = {
    "Karachi": 200, "Lahore": 500, "Islamabad": 900, "Peshawar": 400,
    "Quetta": 250,  "Multan": 160, "Faisalabad": 300, "Hyderabad": 160,
    "Gwadar": 100,  "Sukkur": 120,
}

# -----------------------------------------------------------
# Data fetching
# -----------------------------------------------------------
@st.cache_data(ttl=3600)
def fetch_climate_data(lat, lon, start_date, end_date):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat, "longitude": lon,
        "daily": ["temperature_2m_mean","precipitation_sum",
                  "wind_speed_10m_max","relative_humidity_2m_mean"],
        "start_date": start_date, "end_date": end_date,
        "timezone": "Asia/Karachi",
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        df = pd.DataFrame(data["daily"])
        df["date"] = pd.to_datetime(df["time"])
        df.drop(columns=["time"], inplace=True)
        return df
    except:
        return None

@st.cache_data(ttl=1800)
def fetch_forecast(lat, lon):
    """Fetch 7-day forecast from Open-Meteo."""
    url = "https://api.open-meteo.com/v1/forecast"
    today = datetime.now().strftime("%Y-%m-%d")
    end   = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    params = {
        "latitude": lat, "longitude": lon,
        "daily": ["temperature_2m_max","temperature_2m_min",
                  "precipitation_sum","wind_speed_10m_max",
                  "weathercode"],
        "start_date": today, "end_date": end,
        "timezone": "Asia/Karachi",
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        df = pd.DataFrame(data["daily"])
        df["date"] = pd.to_datetime(df["time"])
        df.drop(columns=["time"], inplace=True)
        return df
    except:
        return None

@st.cache_data(ttl=3600)
def get_all_cities_data(start_date, end_date, city_list):
    import numpy as np
    frames = []
    for city in city_list:
        info = CITIES[city]
        df = fetch_climate_data(info["lat"], info["lon"], start_date, end_date)
        if df is not None:
            df["city"] = city
            df["province"] = info["province"]
            df["lat"] = info["lat"]
            df["lon"] = info["lon"]
            frames.append(df)
    if frames:
        return pd.concat(frames, ignore_index=True)
    return generate_sample_data(city_list)

def generate_sample_data(city_list):
    import numpy as np
    sample = {
        "Karachi":    [27,12,13,69], "Lahore":    [24,31,9,50],
        "Islamabad":  [20,53,8,55],  "Peshawar":  [24,28,10,47],
        "Quetta":     [16,20,11,38], "Multan":    [27,11,9,40],
        "Faisalabad": [24,19,8,47],  "Hyderabad": [27,8,12,64],
        "Gwadar":     [28,5,14,72],  "Sukkur":    [30,9,10,42],
    }
    rows = []
    dates = pd.date_range("2024-01-01","2024-12-31",freq="D")
    for city in city_list:
        vals = sample.get(city, [25,20,10,50])
        for d in dates:
            rows.append({
                "date": d, "city": city,
                "province": CITIES[city]["province"],
                "lat": CITIES[city]["lat"], "lon": CITIES[city]["lon"],
                "temperature_2m_mean":       vals[0] + np.random.normal(0,2),
                "precipitation_sum":         max(0,vals[1]/30+np.random.normal(0,1)),
                "wind_speed_10m_max":        vals[2] + np.random.normal(0,1),
                "relative_humidity_2m_mean": vals[3] + np.random.normal(0,3),
            })
    return pd.DataFrame(rows)

def weather_icon(code):
    """Map WMO weather code to emoji."""
    if code <= 1:   return "☀️"
    if code <= 3:   return "⛅"
    if code <= 49:  return "🌫️"
    if code <= 67:  return "🌧️"
    if code <= 77:  return "❄️"
    if code <= 82:  return "🌦️"
    return "⛈️"

# -----------------------------------------------------------
# Drought index
# -----------------------------------------------------------
def calculate_drought_index(df, city):
    """
    Simple Rainfall Anomaly Index (RAI):
    RAI = (actual - normal) / normal * 100
    """
    actual = df[df["city"] == city]["precipitation_sum"].sum()
    normal = DROUGHT_NORMAL_RAIN.get(city, 300)
    rai = (actual - normal) / normal * 100
    if rai >= -10:   return rai, "Normal", "drought-low"
    if rai >= -25:   return rai, "Moderate drought", "drought-mod"
    if rai >= -50:   return rai, "Severe drought", "drought-severe"
    return rai, "Extreme drought", "drought-extreme"

# -----------------------------------------------------------
# PDF export
# -----------------------------------------------------------
def generate_pdf(df, selected_var, selected_var_label, city_avg, lang):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, "Pakistan Climate Dashboard Report", ln=True, align="C")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  Variable: {selected_var_label}", ln=True, align="C")
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, "City Averages", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_fill_color(240, 240, 240)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(70, 8, "City", border=1, fill=True)
    pdf.cell(50, 8, "Province", border=1, fill=True)
    pdf.cell(60, 8, selected_var_label, border=1, fill=True, ln=True)
    pdf.set_font("Helvetica", "", 11)

    for city, val in city_avg.items():
        pdf.cell(70, 8, city, border=1)
        pdf.cell(50, 8, CITIES[city]["province"], border=1)
        pdf.cell(60, 8, f"{val:.1f}", border=1, ln=True)

    pdf.ln(8)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, "Drought Index", ln=True)
    pdf.set_font("Helvetica", "", 11)
    for city in city_avg.keys():
        rai, status, _ = calculate_drought_index(df, city)
        pdf.cell(0, 7, f"{city}: {status}  (RAI: {rai:.1f}%)", ln=True)

    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(0, 6, "Data source: Open-Meteo API (open-meteo.com)  |  Pakistan Climate Analytics", ln=True, align="C")

    return bytes(pdf.output())

# -----------------------------------------------------------
# Email alert
# -----------------------------------------------------------
def send_alert_email(smtp_host, smtp_port, sender, password, recipient, alerts):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Pakistan Climate Dashboard — Temperature Alert"
    msg["From"]    = sender
    msg["To"]      = recipient
    body = "Temperature Alert Report\n\n"
    for line in alerts:
        body += f"• {line}\n"
    body += f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    msg.attach(MIMEText(body, "plain"))
    try:
        with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
            server.login(sender, password)
            server.sendmail(sender, recipient, msg.as_string())
        return True
    except Exception as e:
        return str(e)

# -----------------------------------------------------------
# SIDEBAR
# -----------------------------------------------------------
lang_choice = st.sidebar.selectbox("🌐 Language / زبان", ["English", "اردو"])
L = LANG["ur"] if lang_choice == "اردو" else LANG["en"]
var_labels = list(L["vars"].keys())

st.sidebar.title(L["title"])
st.sidebar.markdown("---")

selected_var_label = st.sidebar.selectbox(L["variable"], var_labels)
selected_var = L["vars"][selected_var_label]

selected_cities = st.sidebar.multiselect(
    L["cities"], list(CITIES.keys()), default=list(CITIES.keys())[:6]
)
if not selected_cities:
    selected_cities = ["Lahore", "Karachi", "Islamabad"]

col1s, col2s = st.sidebar.columns(2)
start_date = col1s.date_input(L["date_from"], datetime(2024, 1, 1))
end_date   = col2s.date_input(L["date_to"],   datetime(2024, 12, 31))

st.sidebar.markdown("---")
st.sidebar.markdown("**Open-Meteo** · Free API · No key needed")

# -----------------------------------------------------------
# Load data
# -----------------------------------------------------------
with st.spinner("Fetching data from Open-Meteo..."):
    df_all = get_all_cities_data(str(start_date), str(end_date), selected_cities)

df = df_all[df_all["city"].isin(selected_cities)].copy()
df["month"]     = df["date"].dt.strftime("%b")
df["month_num"] = df["date"].dt.month
monthly   = df.groupby(["city","month_num","month"])[selected_var].mean().reset_index()
city_avg  = df.groupby("city")[selected_var].mean()

# -----------------------------------------------------------
# TITLE
# -----------------------------------------------------------
st.title(f"🌍 {L['title']}")
st.caption(f"{selected_var_label} · {start_date} → {end_date}")

# Metric cards
cols = st.columns(min(len(selected_cities), 5))
for i, city in enumerate(selected_cities[:5]):
    with cols[i]:
        val = city_avg.get(city, 0)
        st.metric(city, f"{val:.1f}", delta=CITIES[city]["province"])

st.markdown("---")

# -----------------------------------------------------------
# ROW 1: Map + Trend
# -----------------------------------------------------------
c1, c2 = st.columns([1,1])

with c1:
    st.subheader(L["map"])
    map_data = df.groupby(["city","lat","lon","province"])[selected_var].mean().reset_index()
    map_data.columns = ["city","lat","lon","province","value"]
    fig_map = px.scatter_mapbox(
        map_data, lat="lat", lon="lon", size="value",
        color="province", color_discrete_map=PROVINCE_COLORS,
        hover_name="city", hover_data={"value":":.1f","lat":False,"lon":False},
        size_max=30, zoom=4.5, mapbox_style="carto-positron",
        center={"lat":30.5,"lon":69.5},
    )
    fig_map.update_layout(margin=dict(l=0,r=0,t=0,b=0), height=340)
    st.plotly_chart(fig_map, width="stretch")

with c2:
    st.subheader(L["trend"])
    fig_trend = px.line(
        monthly, x="month_num", y=selected_var, color="city",
        labels={"month_num":"Month", selected_var: selected_var_label},
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig_trend.update_xaxes(
        tickvals=list(range(1,13)),
        ticktext=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    )
    fig_trend.update_layout(height=340, margin=dict(l=0,r=0,t=10,b=0),
                             legend=dict(orientation="h",yanchor="bottom",y=1.02))
    st.plotly_chart(fig_trend, width="stretch")

# -----------------------------------------------------------
# ROW 2: Compare + Heatmap
# -----------------------------------------------------------
c3, c4 = st.columns([1,1])

with c3:
    st.subheader(L["compare"])
    comp = df.groupby(["city","province"])[selected_var].mean().reset_index().sort_values(selected_var)
    fig_bar = px.bar(comp, x=selected_var, y="city", orientation="h",
                     color="province", color_discrete_map=PROVINCE_COLORS,
                     labels={selected_var: selected_var_label, "city":""})
    fig_bar.update_layout(height=300, margin=dict(l=0,r=0,t=10,b=0), showlegend=False)
    st.plotly_chart(fig_bar, width="stretch")

with c4:
    st.subheader(L["heatmap"])
    heat = monthly.pivot(index="city", columns="month_num", values=selected_var)
    heat.columns = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    scale = "RdYlBu_r" if "temp" in selected_var.lower() else "Blues"
    fig_heat = px.imshow(heat, aspect="auto", color_continuous_scale=scale,
                         labels=dict(x="Month",y="City",color=selected_var_label))
    fig_heat.update_layout(height=300, margin=dict(l=0,r=0,t=10,b=0))
    st.plotly_chart(fig_heat, width="stretch")

st.markdown("---")

# -----------------------------------------------------------
# FEATURE 1: 7-Day Forecast
# -----------------------------------------------------------
st.subheader(f"📅 {L['forecast']}")
forecast_city = st.selectbox("Select city for forecast", selected_cities, key="fc_city")
fc = fetch_forecast(CITIES[forecast_city]["lat"], CITIES[forecast_city]["lon"])

if fc is not None:
    fc_cols = st.columns(min(len(fc), 7))
    for i, row in fc.head(7).iterrows():
        with fc_cols[i]:
            icon = weather_icon(int(row.get("weathercode", 0)))
            date_str = pd.to_datetime(row["date"]).strftime("%a\n%d %b")
            st.markdown(f"""
            <div style='text-align:center;padding:10px;background:#f8f9fa;
                        border-radius:10px;border:1px solid #e9ecef;'>
                <div style='font-size:11px;color:#666;white-space:pre'>{date_str}</div>
                <div style='font-size:24px;margin:4px 0'>{icon}</div>
                <div style='font-size:14px;font-weight:600;color:#D85A30'>
                    {row['temperature_2m_max']:.0f}°</div>
                <div style='font-size:12px;color:#378ADD'>
                    {row['temperature_2m_min']:.0f}°</div>
                <div style='font-size:11px;color:#666'>
                    💧{row['precipitation_sum']:.1f}mm</div>
                <div style='font-size:11px;color:#666'>
                    💨{row['wind_speed_10m_max']:.0f}km/h</div>
            </div>""", unsafe_allow_html=True)
else:
    st.info("Forecast data temporarily unavailable. Check your internet connection.")

st.markdown("---")

# -----------------------------------------------------------
# FEATURE 2: Drought Index
# -----------------------------------------------------------
st.subheader(f"🌵 {L['drought']}")
st.caption(L["drought_info"])

drought_cols = st.columns(min(len(selected_cities), 4))
for i, city in enumerate(selected_cities):
    with drought_cols[i % 4]:
        rai, status, css_class = calculate_drought_index(df, city)
        color_map = {
            "drought-low":     "#1D9E75",
            "drought-mod":     "#BA7517",
            "drought-severe":  "#D85A30",
            "drought-extreme": "#A32D2D",
        }
        bg_map = {
            "drought-low":     "#E1F5EE",
            "drought-mod":     "#FAEEDA",
            "drought-severe":  "#FAECE7",
            "drought-extreme": "#FCEBEB",
        }
        color = color_map[css_class]
        bg    = bg_map[css_class]
        gauge = min(max((rai + 100) / 200 * 100, 0), 100)
        st.markdown(f"""
        <div style='background:{bg};border-radius:10px;padding:12px;margin:4px 0;
                    border-left:4px solid {color}'>
            <div style='font-weight:600;font-size:14px'>{city}</div>
            <div style='color:{color};font-size:13px;margin:4px 0'>{status}</div>
            <div style='font-size:12px;color:#555'>RAI: {rai:.1f}%</div>
            <div style='background:#ddd;border-radius:4px;height:6px;margin-top:6px'>
                <div style='background:{color};width:{gauge:.0f}%;height:6px;border-radius:4px'></div>
            </div>
        </div>""", unsafe_allow_html=True)

st.markdown("---")

# -----------------------------------------------------------
# FEATURE 3: Temperature Alerts
# -----------------------------------------------------------
st.subheader(f"🚨 {L['alerts']}")
alert_col1, alert_col2 = st.columns([1, 2])

with alert_col1:
    threshold = st.slider(L["alert_thresh"], min_value=30, max_value=50, value=40)

with alert_col2:
    temp_avgs = df.groupby("city")["temperature_2m_mean"].mean()
    alerts = [
        f"{city}: avg {val:.1f}°C (exceeds {threshold}°C)"
        for city, val in temp_avgs.items() if val >= threshold
    ]
    if alerts:
        for a in alerts:
            st.markdown(f"""
            <div class='alert-box'>⚠️ {a}</div>
            """, unsafe_allow_html=True)
    else:
        st.success(L["no_alert"])

with st.expander("📧 Email alert settings"):
    ea1, ea2 = st.columns(2)
    alert_email = ea1.text_input(L["alert_email"], placeholder="you@example.com")
    smtp_host   = ea2.text_input(L["smtp_host"],   value="smtp.gmail.com")
    ea3, ea4    = st.columns(2)
    smtp_sender = ea3.text_input("Sender email", placeholder="sender@gmail.com")
    smtp_pass   = ea4.text_input(L["smtp_pass"],   type="password")

    if st.button(L["send_alert"]):
        if alerts and alert_email and smtp_pass:
            result = send_alert_email(
                smtp_host, 465, smtp_sender, smtp_pass, alert_email, alerts
            )
            if result is True:
                st.success(L["alert_sent"])
            else:
                st.error(f"{L['alert_fail']}: {result}")
        elif not alerts:
            st.info(L["no_alert"])
        else:
            st.warning("Please fill in email and password fields.")

st.markdown("---")

# -----------------------------------------------------------
# FEATURE 4: PDF Export
# -----------------------------------------------------------
st.subheader(f"📄 {L['pdf_export']}")
pdf_col1, pdf_col2 = st.columns([1,2])

with pdf_col1:
    if st.button(L["gen_pdf"]):
        with st.spinner("Generating PDF..."):
            pdf_bytes = generate_pdf(df, selected_var, selected_var_label, city_avg.to_dict(), L)
            st.session_state["pdf_bytes"] = pdf_bytes
            st.success(L["pdf_ready"])

with pdf_col2:
    if "pdf_bytes" in st.session_state:
        st.download_button(
            label="⬇️ Download PDF report",
            data=st.session_state["pdf_bytes"],
            file_name=f"pakistan_climate_report_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
        )

st.markdown("---")

# -----------------------------------------------------------
# Province summary + Data table
# -----------------------------------------------------------
c5, c6 = st.columns([1,2])

with c5:
    st.subheader(L["province"])
    prov = df.groupby("province")[selected_var].mean().reset_index()
    fig_prov = px.pie(prov, names="province", values=selected_var,
                      color="province", color_discrete_map=PROVINCE_COLORS, hole=0.4)
    fig_prov.update_layout(height=280, margin=dict(l=0,r=0,t=10,b=0))
    st.plotly_chart(fig_prov, width="stretch")

with c6:
    st.subheader(L["table"])
    table = monthly.pivot(index="city", columns="month", values=selected_var).round(1)
    st.dataframe(table, width="stretch")

# CSV download
st.markdown("---")
csv = df[["date","city","province",selected_var]].to_csv(index=False)
st.download_button(
    label=f"⬇️ {L['download_csv']}",
    data=csv,
    file_name=f"pakistan_{selected_var}_{start_date}_{end_date}.csv",
    mime="text/csv",
)
st.caption(L["caption"])
