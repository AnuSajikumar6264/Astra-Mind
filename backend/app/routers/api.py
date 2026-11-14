import uuid
from datetime import datetime,timezone
from fastapi import APIRouter,HTTPException,Query
from ..database import db
from ..schemas import ObservationIn,SimulationIn,SyncIn
from ..services.engine import dashboard,simulate,add_obs,assess,now,forecast

router=APIRouter()
@router.get("/health")
def health():return {"status":"ok","service":"ASTRA-MIND","mode":"research-prototype"}
@router.get("/dashboard")
def get_dashboard(astronaut_id:str="crew-01"):
    d=dashboard(astronaut_id)
    if not d["astronaut"]:raise HTTPException(404,"Astronaut not found")
    return d
@router.get("/observations")
def observations(astronaut_id:str="crew-01",domain:str|None=None,limit:int=Query(100,ge=1,le=1000)):
    sql="SELECT * FROM observations WHERE astronaut_id=?"; args=[astronaut_id]
    if domain:sql+=" AND domain=?";args.append(domain)
    sql+=" ORDER BY observed_at DESC LIMIT ?";args.append(limit)
    with db() as c:return [dict(r) for r in c.execute(sql,args).fetchall()]
@router.post("/observations",status_code=201)
def create_observation(p:ObservationIn):
    x=p.model_dump();x.update(id=str(uuid.uuid4()),observed_at=(p.observed_at or datetime.now(timezone.utc)).isoformat(),metadata={})
    with db() as c:
        if not c.execute("SELECT id FROM astronauts WHERE id=?",(x["astronaut_id"],)).fetchone():raise HTTPException(404,"Astronaut not found")
        add_obs(c,x);a=assess(c,x)
    return {"stored":True,"observation_id":x["id"],"alert":a}
@router.get("/alerts")
def get_alerts(astronaut_id:str="crew-01",include_acknowledged:bool=False):
    sql="SELECT * FROM alerts WHERE astronaut_id=?";args=[astronaut_id]
    if not include_acknowledged:sql+=" AND acknowledged=0"
    sql+=" ORDER BY created_at DESC LIMIT 100"
    with db() as c:return [dict(r) for r in c.execute(sql,args).fetchall()]
@router.post("/alerts/{alert_id}/acknowledge")
def acknowledge(alert_id:str):
    with db() as c:
        cur=c.execute("UPDATE alerts SET acknowledged=1 WHERE id=?",(alert_id,))
        if not cur.rowcount:raise HTTPException(404,"Alert not found")
    return {"acknowledged":True,"alert_id":alert_id}
@router.get("/twin/{astronaut_id}")
def twin(astronaut_id:str):
    d=dashboard(astronaut_id)
    if not d["astronaut"]:raise HTTPException(404,"Astronaut not found")
    return {"astronaut":d["astronaut"],"mission_day":d["astronaut"]["mission_day"],"state":d["domains"],"open_alerts":d["open_alerts"],"interpretation":"Observed state only. Missing and periodic measurements are not inferred."}
@router.get("/forecast/{astronaut_id}")
def get_forecast(astronaut_id:str,domain:str="cardiovascular",metric:str="heart_rate",horizon:int=Query(8,ge=1,le=24)):
    return forecast(astronaut_id,domain,metric,horizon)
@router.post("/simulation/run")
def run_sim(p:SimulationIn):
    rows=simulate(p.scenario,p.samples)
    return {"created_count":len(rows),"alerts_created":sum(1 for r in rows if r["alert"]),"scenario":p.scenario,"provenance":"SYNTHETIC"}
@router.post("/sync/push")
def sync(p:SyncIn):
    with db() as c:
        if c.execute("SELECT event_id FROM sync_events WHERE event_id=?",(p.event_id,)).fetchone():return {"accepted":True,"duplicate":True,"event_id":p.event_id}
        for obs in p.observations:
            x=obs.model_dump();x.update(id=str(uuid.uuid4()),astronaut_id=p.astronaut_id,observed_at=(obs.observed_at or datetime.now(timezone.utc)).isoformat(),metadata={})
            add_obs(c,x);assess(c,x)
        c.execute("INSERT INTO sync_events VALUES(?,?,?)",(p.event_id,p.astronaut_id,now()))
    return {"accepted":True,"duplicate":False,"event_id":p.event_id,"observations_received":len(p.observations)}
