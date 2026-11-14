import json, uuid, random
from datetime import datetime, timezone, timedelta
from statistics import mean, pstdev
from ..database import db

DOMAIN_META={
 "cardiovascular":("Cardiovascular","Heart and circulation"),
 "musculoskeletal":("Musculoskeletal","Bone and muscle health"),
 "immune":("Immune","Periodic immune assessments"),
 "behavioral":("Behavioral","Sleep, stress and cognition"),
 "radiation":("Radiation","Mission dosimetry")
}
METRICS={
 "cardiovascular":[("heart_rate","Heart rate","bpm",65,5),("hrv","Heart-rate variability","ms",62,10),("spo2","Oxygen saturation","%",98,1),("systolic_bp","Systolic blood pressure","mmHg",116,7)],
 "musculoskeletal":[("exercise_minutes","Daily exercise","min/day",75,12),("grip_strength","Grip strength","kg",38,2),("bone_marker","Bone turnover marker","a.u.",1,.12)],
 "immune":[("lymphocytes","Lymphocytes","10^9/L",1.8,.25),("crp","C-reactive protein","mg/L",1.2,.35)],
 "behavioral":[("sleep_hours","Sleep duration","h",7.4,.7),("sleep_efficiency","Sleep efficiency","%",88,4),("mood_score","Daily mood check-in","/10",7.5,.8)],
 "radiation":[("dose_rate","Dose rate","uSv/h",.12,.025),("cumulative_dose","Cumulative dose","mSv",18,2)]
}
def now(): return datetime.now(timezone.utc).isoformat()
def add_obs(conn,x):
    conn.execute("""INSERT INTO observations VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
      (x["id"],x["astronaut_id"],x["domain"],x["metric"],x["value"],x["unit"],x["observed_at"],x["source"],x["provenance"],x["quality"],json.dumps(x.get("metadata",{}))))
def baseline(conn,subject,domain,metric):
    rows=conn.execute("SELECT value FROM observations WHERE astronaut_id=? AND domain=? AND metric=? ORDER BY observed_at DESC LIMIT 60",(subject,domain,metric)).fetchall()
    vals=[float(r["value"]) for r in rows]
    if not vals:return None
    mu=mean(vals); sd=pstdev(vals) if len(vals)>1 else 0
    return {"mean":mu,"std":max(sd,abs(mu)*.025,.001),"n":len(vals)}
def assess(conn,x):
    b=baseline(conn,x["astronaut_id"],x["domain"],x["metric"])
    if not b or b["n"]<5:return None
    z=(x["value"]-b["mean"])/b["std"]
    if abs(z)<2.8:return None
    since=(datetime.now(timezone.utc)-timedelta(hours=12)).isoformat()
    duplicate=conn.execute("SELECT id FROM alerts WHERE astronaut_id=? AND metric=? AND acknowledged=0 AND created_at>? LIMIT 1",(x["astronaut_id"],x["metric"],since)).fetchone()
    if duplicate:return None
    a={"id":str(uuid.uuid4()),"astronaut_id":x["astronaut_id"],"domain":x["domain"],"metric":x["metric"],
       "severity":"high" if abs(z)>=4 else "attention","title":f'{x["metric"].replace("_"," ").title()} differs from baseline',
       "message":f'Observed {x["value"]} {x["unit"]}; personal baseline {b["mean"]:.2f} {x["unit"]} ({z:+.1f} SD). Review quality, context and approved protocol.',
       "observed_value":x["value"],"baseline_value":b["mean"],"deviation":z,"created_at":now(),"acknowledged":0}
    conn.execute("INSERT INTO alerts VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",tuple(a.values()))
    return a
def ensure_seed():
    with db() as c:
        c.execute("INSERT OR IGNORE INTO astronauts VALUES(?,?,?,?,?)",("crew-01","Commander Alex Morgan","Asteria-1 · Mars transit simulation",96,now()))
        n=c.execute("SELECT COUNT(*) FROM observations WHERE astronaut_id='crew-01'").fetchone()[0]
        if n:return
        rng=random.Random(17); t=datetime.now(timezone.utc)
        for day in range(14,0,-1):
            for domain,items in METRICS.items():
                if domain in ("immune","musculoskeletal") and day%3:continue
                for key,label,unit,mu,sd in items:
                    x={"id":str(uuid.uuid4()),"astronaut_id":"crew-01","domain":domain,"metric":key,"value":round(rng.gauss(mu,sd*.35),3),"unit":unit,"observed_at":(t-timedelta(days=day)).isoformat(),"source":"mission-simulator","provenance":"SYNTHETIC","quality":.98,"metadata":{"label":label}}
                    add_obs(c,x)
def simulate(scenario="nominal",samples=1,subject="crew-01"):
    rng=random.Random(); made=[]
    with db() as c:
        for _ in range(samples):
            for domain,items in METRICS.items():
                if domain in ("immune","musculoskeletal") and rng.random()<.55:continue
                for key,label,unit,mu,sd in items:
                    val=rng.gauss(mu,sd*.45)
                    if scenario=="sleep_disruption" and key in ("sleep_hours","sleep_efficiency","mood_score"):val-={"sleep_hours":2.2,"sleep_efficiency":14,"mood_score":1.4}[key]
                    if scenario=="cardiovascular_strain" and key in ("heart_rate","hrv","systolic_bp"):val+={"heart_rate":22,"hrv":-22,"systolic_bp":16}[key]
                    if scenario=="exercise_decline" and key=="exercise_minutes":val-=38
                    if scenario=="radiation_increase" and key in ("dose_rate","cumulative_dose"):val+=.25 if key=="dose_rate" else 2.8
                    x={"id":str(uuid.uuid4()),"astronaut_id":subject,"domain":domain,"metric":key,"value":round(max(0,val),3),"unit":unit,"observed_at":now(),"source":"mission-simulator","provenance":"SYNTHETIC","quality":round(rng.uniform(.94,1),2),"metadata":{"label":label}}
                    add_obs(c,x); a=assess(c,x); made.append({"observation":x,"alert":a})
        c.execute("UPDATE astronauts SET mission_day=mission_day+? WHERE id=?",(samples,subject))
    return made
def dashboard(subject="crew-01"):
    with db() as c:
        crew=c.execute("SELECT * FROM astronauts WHERE id=?",(subject,)).fetchone()
        domains=[]
        for domain,(label,desc) in DOMAIN_META.items():
            metrics=[]
            for key,title,unit,_,_ in METRICS[domain]:
                r=c.execute("SELECT * FROM observations WHERE astronaut_id=? AND domain=? AND metric=? ORDER BY observed_at DESC LIMIT 1",(subject,domain,key)).fetchone()
                b=baseline(c,subject,domain,key)
                if r:metrics.append({"metric":key,"label":title,"value":r["value"],"unit":r["unit"],"observed_at":r["observed_at"],"quality":r["quality"],"provenance":r["provenance"],"baseline":round(b["mean"],2) if b else None})
            status="review" if any(m["baseline"] is not None and abs(m["value"]-m["baseline"])>max(abs(m["baseline"])*.025,.001)*2.8 for m in metrics) else "nominal"
            domains.append({"id":domain,"label":label,"description":desc,"status":status,"metrics":metrics})
        alerts=[dict(x) for x in c.execute("SELECT * FROM alerts WHERE astronaut_id=? ORDER BY created_at DESC LIMIT 30",(subject,)).fetchall()]
        count=c.execute("SELECT COUNT(*) FROM observations WHERE astronaut_id=?",(subject,)).fetchone()[0]
        open_count=sum(1 for a in alerts if not a["acknowledged"])
        return {"astronaut":dict(crew) if crew else None,"domains":domains,"alerts":alerts,"observation_count":count,"open_alerts":open_count,"system_mode":"ONBOARD"}
def forecast(subject,domain,metric,horizon=8):
    with db() as c:
        rows=c.execute("SELECT value FROM observations WHERE astronaut_id=? AND domain=? AND metric=? ORDER BY observed_at DESC LIMIT 30",(subject,domain,metric)).fetchall()
    y=[float(r["value"]) for r in reversed(rows)]
    if len(y)<3:return {"metric":metric,"method":"insufficient-history","points":[]}
    x=list(range(len(y))); xb=mean(x); yb=mean(y); den=sum((v-xb)**2 for v in x) or 1
    slope=sum((a-xb)*(b-yb) for a,b in zip(x,y))/den; intercept=yb-slope*xb
    residual=[v-(intercept+slope*i) for i,v in enumerate(y)]
    sigma=(sum(v*v for v in residual)/max(1,len(y)-2))**.5
    pts=[]
    for step in range(1,horizon+1):
        pred=intercept+slope*(len(y)-1+step); band=1.96*sigma*(1+step/len(y))**.5
        pts.append({"step":step,"prediction":round(pred,3),"lower":round(pred-band,3),"upper":round(pred+band,3)})
    return {"metric":metric,"method":"OLS trend baseline","history_count":len(y),"points":pts,"warning":"Exploratory only; not a clinical prediction."}
