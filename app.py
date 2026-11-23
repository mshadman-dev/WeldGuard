import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
import random, sqlite3, io
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

st.set_page_config(page_title="WeldGuard | Industrial Safety", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")
DB_PATH = Path(__file__).with_name("weldguard.db")
BAYS = ["Bay 01", "Bay 02", "Bay 03"]

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
:root{--bg:#0a1018;--panel:#111c29;--line:#26384a;--muted:#91a4b8;--text:#edf4fb;--cyan:#36c5d9;--green:#39d98a;--amber:#f5b942;--red:#ff5d67}
html,body,[class*="css"]{font-family:'Manrope',sans-serif}.stApp{background:radial-gradient(ellipse at 70% -20%,#18334a 0%,#0a1018 48%);color:var(--text)}
.block-container{padding-top:1.35rem;padding-bottom:2rem;max-width:1550px}[data-testid="stSidebar"]{background:#0c1520;border-right:1px solid #26384a}[data-testid="stSidebar"] *{color:#dce8f3}
h1,h2,h3{color:#edf4fb!important;letter-spacing:-.03em}.smallcaps{color:#91a4b8;font-size:11px;font-weight:800;letter-spacing:.14em;text-transform:uppercase}
.hero{background:linear-gradient(110deg,rgba(25,49,69,.96),rgba(16,29,43,.96));border:1px solid #2b455b;border-radius:18px;padding:23px 26px;margin:8px 0 18px}
.hero-title{font-size:27px;font-weight:800;letter-spacing:-.04em;color:#f3f8fc}.hero-sub{color:#9eb2c5;font-size:13px;margin-top:5px}
.metric-card{background:linear-gradient(145deg,#142333,#101a26);border:1px solid #293c4f;border-radius:15px;padding:16px 18px;min-height:112px}
.metric-label{color:#9aafc2;font-size:11px;text-transform:uppercase;letter-spacing:.12em;font-weight:800}.metric-value{color:#f2f7fb;font-size:29px;font-weight:800;letter-spacing:-.05em;margin-top:7px}.metric-foot{color:#8da2b6;font-size:11px;margin-top:4px}
.panel{background:#111c29;border:1px solid #26384a;border-radius:16px;padding:18px 20px}.panel-title{color:#eaf2f8;font-size:15px;font-weight:800;margin-bottom:3px}.panel-sub{color:#8fa4b8;font-size:11px;margin-bottom:13px}
.event{border-left:3px solid #f5b942;background:#172536;border-radius:8px;padding:11px 13px;margin:8px 0}.event.danger{border-left-color:#ff5d67}.event.ok{border-left-color:#39d98a}
.event-time{color:#91a4b8;font-family:'DM Mono',monospace;font-size:10px}.event-text{color:#e9f1f7;font-size:12px;font-weight:700;margin-top:3px}
div.stButton>button{border-radius:9px;font-weight:800;border:1px solid #35516a}div.stButton>button[kind="primary"]{background:#1c9caf;border-color:#1c9caf;color:white}
[data-testid="stMetric"]{background:#142333;border:1px solid #293c4f;border-radius:14px;padding:13px 16px}[data-testid="stMetricLabel"]{color:#9aafc2}[data-testid="stMetricValue"]{color:#f2f7fb}hr{border-color:#26384a}footer{visibility:hidden}
</style>""", unsafe_allow_html=True)

# SQLite persistence
def db():
    return sqlite3.connect(DB_PATH, timeout=15)

def init_db():
    with db() as con:
        con.execute('''CREATE TABLE IF NOT EXISTS readings(
            id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL, bay TEXT NOT NULL,
            pm1 REAL NOT NULL, pm25 REAL NOT NULL, pm10 REAL NOT NULL, fan_on INTEGER NOT NULL, level TEXT NOT NULL)''')
        con.execute('''CREATE TABLE IF NOT EXISTS events(
            id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL, bay TEXT NOT NULL,
            level TEXT NOT NULL, message TEXT NOT NULL, acknowledged INTEGER DEFAULT 0,
            acknowledged_at TEXT DEFAULT '', resolved INTEGER DEFAULT 0, resolved_at TEXT DEFAULT '')''')
        con.execute('''CREATE TABLE IF NOT EXISTS bay_settings(
            bay TEXT PRIMARY KEY, warning REAL NOT NULL DEFAULT 35, danger REAL NOT NULL DEFAULT 55,
            auto INTEGER NOT NULL DEFAULT 1, manual_fan INTEGER NOT NULL DEFAULT 0)''')
        con.execute("CREATE INDEX IF NOT EXISTS idx_readings_bay_time ON readings(bay,timestamp)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_events_bay_time ON events(bay,timestamp)")
        for bay in BAYS:
            con.execute("INSERT OR IGNORE INTO bay_settings(bay) VALUES (?)", (bay,))
init_db()

@st.cache_data(ttl=2)
def load_settings():
    with db() as con:
        rows=con.execute("SELECT bay,warning,danger,auto,manual_fan FROM bay_settings").fetchall()
    return {r[0]:{"warning":r[1],"danger":r[2],"auto":bool(r[3]),"manual_fan":bool(r[4])} for r in rows}

def save_settings(bay, warning, danger, auto, manual):
    with db() as con:
        con.execute("UPDATE bay_settings SET warning=?,danger=?,auto=?,manual_fan=? WHERE bay=?",(warning,danger,int(auto),int(manual),bay))
    load_settings.clear()

def add_event(bay, level, message):
    with db() as con:
        con.execute("INSERT INTO events(timestamp,bay,level,message) VALUES(?,?,?,?)",(datetime.now().isoformat(timespec="seconds"),bay,level,message))

def add_reading(bay, pm25, fan_on, level):
    pm1=round(pm25*.58,1); pm10=round(pm25*1.72,1)
    with db() as con:
        con.execute("INSERT INTO readings(timestamp,bay,pm1,pm25,pm10,fan_on,level) VALUES(?,?,?,?,?,?,?)",(datetime.now().isoformat(timespec="seconds"),bay,pm1,pm25,pm10,int(fan_on),level))

def get_readings(bay=None, start=None, end=None):
    sql="SELECT timestamp,bay,pm1,pm25,pm10,fan_on,level FROM readings WHERE 1=1"; args=[]
    if bay and bay!="All bays": sql+=" AND bay=?"; args.append(bay)
    if start: sql+=" AND date(timestamp)>=date(?)"; args.append(str(start))
    if end: sql+=" AND date(timestamp)<=date(?)"; args.append(str(end))
    sql+=" ORDER BY timestamp DESC"
    with db() as con: rows=con.execute(sql,args).fetchall()
    return pd.DataFrame(rows,columns=["time","bay","PM1.0","PM2.5","PM10","fan_on","level"])

def get_events(bay=None):
    sql="SELECT id,timestamp,bay,level,message,acknowledged,acknowledged_at,resolved,resolved_at FROM events"; args=[]
    if bay and bay!="All bays": sql+=" WHERE bay=?"; args.append(bay)
    sql+=" ORDER BY id DESC"
    with db() as con: rows=con.execute(sql,args).fetchall()
    return pd.DataFrame(rows,columns=["id","time","bay","level","message","acknowledged","acknowledged_at","resolved","resolved_at"])

def classify(v, s): return "DANGER" if v>=s["danger"] else "WARNING" if v>=s["warning"] else "NORMAL"

def fan_command(v,s): return bool(v>=s["warning"]) if s["auto"] else s["manual_fan"]

def seed_if_empty():
    with db() as con: count=con.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
    if count==0:
        now=datetime.now()
        for idx,bay in enumerate(BAYS):
            base=[22,31,15][idx]
            for n in range(12):
                value=round(max(5,base+random.uniform(-5,7)),1)
                cfg=load_settings()[bay]; level=classify(value,cfg); fan=fan_command(value,cfg)
                ts=(now-timedelta(minutes=33-3*n)).isoformat(timespec="seconds")
                with db() as con:
                    con.execute("INSERT INTO readings(timestamp,bay,pm1,pm25,pm10,fan_on,level) VALUES(?,?,?,?,?,?,?)",(ts,bay,round(value*.58,1),value,round(value*1.72,1),int(fan),level))
seed_if_empty()

settings=load_settings()
with st.sidebar:
    st.markdown("<div style='font-size:25px;font-weight:900;letter-spacing:-1px'>🛡️ WELD<span style='color:#36c5d9'>GUARD</span></div><div style='font-size:10px;color:#8299ad;letter-spacing:2px;margin:2px 0 22px'>WORKSHOP AIR SAFETY SYSTEM</div>",unsafe_allow_html=True)
    page=st.radio("NAVIGATION",["Overview","Workstation","Alerts & Events","Reports","System Settings"])
    st.markdown("---")
    st.markdown("<div class='smallcaps'>Selected workstation</div>",unsafe_allow_html=True)
    selected_bay=st.selectbox("Bay",BAYS,index=0,label_visibility="collapsed")
    st.markdown("---")
    st.markdown("<div class='smallcaps'>Prototype status</div>",unsafe_allow_html=True)
    st.markdown("<span style='color:#39d98a'>●</span> <span style='font-size:12px'>Local SQLite storage ready</span>",unsafe_allow_html=True)
    st.caption("DEMO BUILD 0.6.0 · LOCAL SIMULATION")

# latest reading per bay
all_data=get_readings()
latest={}
for bay in BAYS:
    sub=all_data[all_data.bay==bay]
    if not sub.empty: latest[bay]=sub.iloc[0].to_dict()
    else: latest[bay]={"PM1.0":0,"PM2.5":0,"PM10":0,"fan_on":0,"level":"NORMAL","time":"—"}

if page=="Overview":
    st.markdown("<div class='hero'><div class='smallcaps'>CENTRAL OPERATIONS / MULTI-BAY SIMULATION</div><div class='hero-title'>Workshop Safety Overview</div><div class='hero-sub'>Three configured welding bays · Independent simulated particulate streams · Central operator view</div></div>",unsafe_allow_html=True)
    normal=sum(latest[b]["level"]=="NORMAL" for b in BAYS); warning=sum(latest[b]["level"]=="WARNING" for b in BAYS); danger=sum(latest[b]["level"]=="DANGER" for b in BAYS)
    a,b,c,d=st.columns(4); a.metric("Configured bays",3); b.metric("Normal",normal); c.metric("Warning",warning); d.metric("Danger",danger)
    st.markdown("### Workstation status")
    cols=st.columns(3)
    for col,bay in zip(cols,BAYS):
        r=latest[bay]; lev=r["level"]; cc="#ff5d67" if lev=="DANGER" else "#f5b942" if lev=="WARNING" else "#39d98a"
        with col:
            st.markdown(f"<div class='metric-card'><div class='metric-label'>{bay.upper()}</div><div class='metric-value' style='color:{cc}'>{lev}</div><div class='metric-foot'>PM2.5 · {float(r['PM2.5']):.1f} µg/m³</div><div class='metric-foot'>Extraction fan · {'ON' if r['fan_on'] else 'OFF'}</div><div class='metric-foot'>Updated · {str(r['time'])[-8:]}</div></div>",unsafe_allow_html=True)
    st.write("")
    st.markdown("### Simulate a workstation")
    c1,c2,c3=st.columns([1,1,1])
    with c1: sim_bay=st.selectbox("Target bay",BAYS,key="sim_bay")
    with c2: sim_value=st.slider("Simulated PM2.5 (µg/m³)",0,150,40,key="sim_value")
    with c3:
        st.write("")
        if st.button("Save monitoring sample",type="primary",use_container_width=True):
            cfg=settings[sim_bay]; lev=classify(float(sim_value),cfg); fan=fan_command(float(sim_value),cfg)
            previous=latest[sim_bay]["level"]
            add_reading(sim_bay,float(sim_value),fan,lev)
            if lev!=previous: add_event(sim_bay,lev,f"PM2.5 changed from {previous} to {lev} at {sim_value:.1f} µg/m³")
            add_event(sim_bay,"SYSTEM",f"Monitoring sample saved · PM2.5 {sim_value:.1f} µg/m³ · fan {'ON' if fan else 'OFF'}")
            st.success(f"Sample saved for {sim_bay}."); st.rerun()
    st.markdown("### One-click demonstration scenario")
    st.caption("Creates one illustrative sample for each bay so the central dashboard can demonstrate different operating conditions.")
    scenario=st.selectbox("Choose scenario",["Mixed conditions · Bay 01 normal / Bay 02 warning / Bay 03 danger","All bays normal","All bays warning","All bays danger"],key="scenario_choice")
    if st.button("Run 3-bay demonstration",use_container_width=True):
        if scenario.startswith("Mixed"):
            scenario_values={"Bay 01":22.0,"Bay 02":45.0,"Bay 03":75.0}
        elif scenario=="All bays normal": scenario_values={bay:22.0 for bay in BAYS}
        elif scenario=="All bays warning": scenario_values={bay:45.0 for bay in BAYS}
        else: scenario_values={bay:75.0 for bay in BAYS}
        for target,value in scenario_values.items():
            cfg=settings[target]; lev=classify(value,cfg); fan=fan_command(value,cfg); previous=latest[target]["level"]
            add_reading(target,value,fan,lev)
            if lev!=previous: add_event(target,lev,f"Scenario changed state from {previous} to {lev} at {value:.1f} µg/m³")
            add_event(target,"SYSTEM",f"Demonstration scenario sample · PM2.5 {value:.1f} µg/m³ · fan {'ON' if fan else 'OFF'}")
        st.success("Demonstration samples saved for all three bays."); st.rerun()
    st.markdown("### Cross-bay particulate trend")
    hist=all_data.copy()
    if not hist.empty:
        hist["time"]=pd.to_datetime(hist["time"])
        fig=go.Figure()
        palette={"Bay 01":"#36c5d9","Bay 02":"#a78bfa","Bay 03":"#39d98a"}
        for bay in BAYS:
            part=hist[hist.bay==bay].sort_values("time")
            fig.add_trace(go.Scatter(x=part.time,y=part["PM2.5"],name=bay,mode="lines+markers",line=dict(color=palette[bay],width=2)))
        fig.update_layout(height=340,margin=dict(l=5,r=8,t=15,b=5),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font=dict(color="#91a4b8",size=10),legend=dict(orientation="h",y=1.12,x=0),xaxis=dict(showgrid=False),yaxis=dict(gridcolor="#26384a",title="PM2.5 · µg/m³"),hovermode="x unified")
        st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
    st.info("DEMONSTRATION MODE · All three bays use simulated values. No real sensor, fan or ESP32 is connected. These values and setpoints are not occupational exposure measurements or safety limits.")

elif page=="Workstation":
    st.markdown(f"<div class='hero'><div class='smallcaps'>BAY CONFIGURATION / LIVE CONCEPT MODEL</div><div class='hero-title'>{selected_bay} · Welding Workstation</div><div class='hero-sub'>Concept visualization linked to the selected bay's latest simulated status</div></div>",unsafe_allow_html=True)
    r=latest[selected_bay]; lev=r["level"]; fan=bool(r["fan_on"]); cc="#ff5d67" if lev=="DANGER" else "#f5b942" if lev=="WARNING" else "#39d98a"
    st.markdown(f"<div style='border:1px solid #2b4054;border-radius:18px;background:linear-gradient(180deg,#142638,#0d1722);height:390px;position:relative;overflow:hidden;padding:20px'><div class='smallcaps'>{selected_bay.upper()} · <span style='color:{cc}'>{lev} CONDITION</span></div><div style='position:absolute;left:8%;bottom:70px;width:42%;height:18px;background:#405a70;border-radius:4px'></div><div style='position:absolute;left:15%;bottom:0;width:10px;height:72px;background:#3c5368'></div><div style='position:absolute;left:45%;bottom:0;width:10px;height:72px;background:#3c5368'></div><div style='position:absolute;left:27%;bottom:90px;width:100px;height:14px;background:#a0b3c2;transform:skew(-12deg)'></div><div style='position:absolute;left:36%;bottom:108px;color:#ffb36a;font-size:28px;text-shadow:0 0 18px #ff6b39'>✦</div><div style='position:absolute;left:27%;top:105px;width:160px;height:20px;border-radius:8px;background:#45657e;border:1px solid #7895aa'></div><div style='position:absolute;left:33%;top:50px;width:18px;height:60px;background:#38566e'></div><div style='position:absolute;right:12%;top:42px;width:78px;height:78px;border-radius:50%;border:6px solid {"#39d98a" if fan else "#58758d"};display:grid;place-items:center;font-size:30px;background:#172c40'>🌀</div><div style='position:absolute;right:19%;bottom:80px;width:55px;height:60px;border-radius:8px;background:#1d354a;border:1px solid #7aa1ba;display:grid;place-items:center;font-size:23px'>▦</div><div style='position:absolute;left:38%;top:160px;width:30%;height:3px;background:linear-gradient(90deg,transparent,#36c5d9,transparent)'></div><div style='position:absolute;left:38%;top:180px;width:30%;height:3px;background:linear-gradient(90deg,transparent,#36c5d9,transparent)'></div><div style='position:absolute;left:6%;bottom:140px;font-size:10px;font-weight:800;color:#dce9f3'>FUME SOURCE / ARC ZONE</div><div style='position:absolute;left:25%;top:72px;font-size:10px;font-weight:800;color:#dce9f3'>LOCAL CAPTURE HOOD</div><div style='position:absolute;right:7%;top:130px;font-size:10px;font-weight:800;color:#dce9f3'>{'EXTRACTION ACTIVE' if fan else 'FAN STANDBY'}</div></div>",unsafe_allow_html=True)
    st.caption("Conceptual illustration only; not a scaled engineering drawing or proof of effective fume capture.")
    a,b,c,d=st.columns(4); a.metric("PM1.0",f"{float(r['PM1.0']):.1f} µg/m³"); b.metric("PM2.5",f"{float(r['PM2.5']):.1f} µg/m³"); c.metric("PM10",f"{float(r['PM10']):.1f} µg/m³"); d.metric("Extraction fan","ON" if fan else "OFF")
    st.markdown("**Proposed components**: capture hood · extraction duct and fan · particulate sensor · ESP32 controller · OLED display · warning indicators and buzzer.")
    st.warning("The proposed particulate sensor cannot identify the chemical composition or toxicity of welding fumes. No physical sensor or extraction device is connected in this simulation.")

elif page=="Alerts & Events":
    st.markdown("<div class='hero'><div class='smallcaps'>EVENT LOG / OPERATOR REVIEW</div><div class='hero-title'>Alerts & Event History</div><div class='hero-sub'>Bay-specific events · acknowledgement and resolution tracked separately</div></div>",unsafe_allow_html=True)
    filter_bay=st.selectbox("Filter events",["All bays"]+BAYS)
    ev=get_events(None if filter_bay=="All bays" else filter_bay)
    a,b,c=st.columns(3); a.metric("Total events",len(ev)); b.metric("Awaiting acknowledgement",int((ev.acknowledged==0).sum()) if not ev.empty else 0); c.metric("Unresolved events",int((ev.resolved==0).sum()) if not ev.empty else 0)
    if st.button("＋ Add test alert"):
        add_event(selected_bay,"WARNING","Operator initiated test alert"); st.rerun()
    st.download_button("⬇ Download event log (CSV)",ev.to_csv(index=False),"weldguard_events_v06.csv","text/csv")
    for _,e in ev.head(100).iterrows():
        cls="danger" if e.level=="DANGER" else "ok" if e.level=="SYSTEM" else ""
        left,right=st.columns([5,1.4])
        with left:
            ack="ACKNOWLEDGED" if e.acknowledged else "PENDING ACKNOWLEDGEMENT"; res=f"RESOLVED · {e.resolved_at}" if e.resolved else "UNRESOLVED"
            st.markdown(f"<div class='event {cls}'><div class='event-time'>{e.time} · {e.bay} · {e.level} · {ack} · {res}</div><div class='event-text'>{e.message}</div></div>",unsafe_allow_html=True)
        with right:
            if not e.acknowledged and st.button("Acknowledge",key=f"ack_{int(e.id)}"):
                with db() as con: con.execute("UPDATE events SET acknowledged=1,acknowledged_at=? WHERE id=?",(datetime.now().isoformat(timespec="seconds"),int(e.id)))
                st.rerun()
            if not e.resolved and st.button("Mark resolved",key=f"res_{int(e.id)}"):
                with db() as con: con.execute("UPDATE events SET resolved=1,resolved_at=? WHERE id=?",(datetime.now().isoformat(timespec="seconds"),int(e.id)))
                st.rerun()
    if ev.empty: st.info("No events for this filter yet.")
    st.caption("Acknowledgement records operator awareness. Resolution is a separate record and does not alter the simulated air-quality condition.")

elif page=="Reports":
    st.markdown("<div class='hero'><div class='smallcaps'>REPORTING / HISTORICAL RECORDS</div><div class='hero-title'>Monitoring Reports</div><div class='hero-sub'>Persistent multi-bay records stored locally in SQLite</div></div>",unsafe_allow_html=True)
    f1,f2,f3=st.columns([1,1,1.2])
    with f1: report_bay=st.selectbox("Bay",["All bays"]+BAYS)
    with f2: start_date=st.date_input("From",value=date.today()-timedelta(days=30))
    with f3: end_date=st.date_input("To",value=date.today())
    if start_date>end_date: st.error("Start date must be on or before end date."); st.stop()
    data=get_readings(report_bay,start_date,end_date); ev=get_events(None if report_bay=="All bays" else report_bay)
    if not ev.empty:
        ev=ev[(pd.to_datetime(ev.time).dt.date>=start_date)&(pd.to_datetime(ev.time).dt.date<=end_date)]
    samples=len(data); avg=data["PM2.5"].mean() if samples else 0; peak=data["PM2.5"].max() if samples else 0
    a,b,c,d=st.columns(4); a.metric("Monitoring samples",samples); b.metric("Average PM2.5",f"{avg:.1f} µg/m³"); c.metric("Peak PM2.5",f"{peak:.1f} µg/m³"); d.metric("Events recorded",len(ev))
    if samples:
        data["time"]=pd.to_datetime(data.time)
        fig=go.Figure()
        for bay,color in zip(BAYS,["#36c5d9","#a78bfa","#39d98a"]):
            p=data[data.bay==bay].sort_values("time")
            if not p.empty: fig.add_trace(go.Scatter(x=p.time,y=p["PM2.5"],name=bay,mode="lines+markers",line=dict(color=color,width=2)))
        fig.update_layout(height=300,margin=dict(l=5,r=8,t=15,b=5),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font=dict(color="#91a4b8",size=10),legend=dict(orientation="h",y=1.12,x=0),xaxis=dict(showgrid=False),yaxis=dict(gridcolor="#26384a",title="PM2.5 · µg/m³"))
        st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
        st.dataframe(data.sort_values("time",ascending=False),use_container_width=True,hide_index=True)
    else: st.info("No monitoring records in this bay/date range. Add samples from Overview.")
    st.download_button("⬇ Download monitoring CSV",data.to_csv(index=False),"weldguard_monitoring_v06.csv","text/csv",disabled=data.empty)
    st.download_button("⬇ Download events CSV",ev.to_csv(index=False),"weldguard_events_v06.csv","text/csv",disabled=ev.empty)
    if st.button("Generate PDF report",type="primary",disabled=(data.empty and ev.empty)):
        buffer=io.BytesIO(); doc=SimpleDocTemplate(buffer,pagesize=A4,rightMargin=16*mm,leftMargin=16*mm,topMargin=16*mm,bottomMargin=16*mm); styles=getSampleStyleSheet()
        styles.add(ParagraphStyle(name="WGTitle",parent=styles["Title"],textColor=colors.HexColor("#17324a"),fontSize=20,leading=24,spaceAfter=5))
        story=[Paragraph("WELDGUARD",styles["WGTitle"]),Paragraph("Multi-bay workshop monitoring · Simulation report",styles["Heading2"]),Paragraph(f"Generated {datetime.now():%Y-%m-%d %H:%M:%S} · Bay filter: {report_bay} · Period: {start_date} to {end_date}",styles["BodyText"]),Spacer(1,7*mm)]
        summary=[["Metric","Result"],["Samples",str(samples)],["Average PM2.5",f"{avg:.1f} µg/m³"],["Peak PM2.5",f"{peak:.1f} µg/m³"],["Events",str(len(ev))]]
        tb=Table(summary,colWidths=[65*mm,65*mm]); tb.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#17324a")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.4,colors.grey),("PADDING",(0,0),(-1,-1),6)])); story.extend([tb,Spacer(1,6*mm),Paragraph("Event history",styles["Heading2"])])
        if ev.empty: story.append(Paragraph("No events recorded in the selected period.",styles["BodyText"]))
        else:
            rows=[["Time","Bay","Level","Ack","Resolved","Message"]]
            for _,x in ev.head(40).iterrows(): rows.append([str(x.time),str(x.bay),str(x.level),"Yes" if x.acknowledged else "No","Yes" if x.resolved else "No",str(x.message)[:65]])
            et=Table(rows,colWidths=[29*mm,17*mm,17*mm,15*mm,19*mm,55*mm],repeatRows=1); et.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#17324a")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.3,colors.grey),("FONTSIZE",(0,0),(-1,-1),6.5),("VALIGN",(0,0),(-1,-1),"TOP"),("PADDING",(0,0),(-1,-1),4)])); story.append(et)
        story.extend([Spacer(1,6*mm),Paragraph("Important limitations",styles["Heading2"]),Paragraph("This report contains simulated demonstration data, not measured workplace exposure. The particulate sensor concept does not identify welding-fume chemical composition or toxicity. Demonstration setpoints are not occupational exposure limits. This report is not a safety certification.",styles["BodyText"])])
        doc.build(story); st.session_state["pdf_v06"]=buffer.getvalue(); st.success("PDF report generated.")
    if st.session_state.get("pdf_v06"): st.download_button("⬇ Download PDF",st.session_state["pdf_v06"],"weldguard_multi_bay_report.pdf","application/pdf")

else:
    st.markdown("<div class='hero'><div class='smallcaps'>CONFIGURATION / DEMONSTRATION</div><div class='hero-title'>System Settings</div><div class='hero-sub'>Independent demonstration thresholds and controller mode for each bay</div></div>",unsafe_allow_html=True)
    cfg=settings[selected_bay]
    with st.form("bay_settings_form"):
        st.subheader(selected_bay)
        warning=st.number_input("Warning threshold · PM2.5 (µg/m³)",min_value=1.0,max_value=499.0,value=float(cfg["warning"]),step=1.0)
        danger=st.number_input("Danger threshold · PM2.5 (µg/m³)",min_value=2.0,max_value=500.0,value=float(cfg["danger"]),step=1.0)
        auto=st.checkbox("Automatic ventilation",value=cfg["auto"])
        manual=st.checkbox("Manual fan command (used only when automatic mode is off)",value=cfg["manual_fan"],disabled=auto)
        submitted=st.form_submit_button("Save bay settings",type="primary")
    if submitted:
        if danger<=warning: st.error("Danger threshold must be higher than warning threshold.")
        else:
            save_settings(selected_bay,warning,danger,auto,manual); add_event(selected_bay,"SYSTEM",f"Settings updated · warning {warning:.0f}, danger {danger:.0f} µg/m³ · {'automatic' if auto else 'manual'} mode"); st.success("Settings saved for this bay."); st.rerun()
    st.markdown("---")
    st.markdown("**Controller logic**")
    st.write("- Automatic mode: simulated fan turns ON at or above the warning setpoint.")
    st.write("- Manual mode: operator-selected fan command is used.")
    st.write("- PM1.0 is an illustrative estimate derived from PM2.5; PM10 is also simulated from PM2.5.")
    st.write(f"- Database location: `{DB_PATH}`")
    st.markdown("### Local data backup")
    if DB_PATH.exists():
        st.download_button("Download complete SQLite backup",DB_PATH.read_bytes(),file_name="weldguard_backup.sqlite",mime="application/vnd.sqlite3",use_container_width=True)
    st.caption("Keep this backup somewhere safe before moving the project to another computer.")
    st.markdown("### Clear demonstration history")
    confirm_clear=st.checkbox("I understand this permanently deletes saved readings and events from this local prototype.")
    if st.button("Clear all monitoring history",disabled=not confirm_clear):
        with db() as con:
            con.execute("DELETE FROM readings")
            con.execute("DELETE FROM events")
        st.session_state.pop("pdf_v06",None)
        st.success("Monitoring history cleared. Bay settings were preserved.")
        st.rerun()
    st.warning("All readings, alarms and fan states are simulated. No physical sensor, fan, alarm or controller is connected. Demo thresholds are not occupational exposure limits.")

st.markdown("<div style='border-top:1px solid #26384a;margin-top:30px;padding-top:13px;display:flex;justify-content:space-between;color:#71869a;font-size:10px'><span>WELDGUARD · INDUSTRIAL AIR SAFETY CONCEPT</span><span>LOCAL PROTOTYPE · SQLITE · SIMULATED DATA · V0.6.0</span></div>",unsafe_allow_html=True)
