from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
from database import get_max_usage, insert_memory_usage, insert_constant_max_memory_usage

app = FastAPI()

class UsageData(BaseModel):
    hostname: str
    cgroup: str
    max_usage: int
    timestamp: datetime

@app.post("/submit")
def submit_usage(data: UsageData):
    try:
        insert_constant_max_memory_usage(data.hostname, data.cgroup, data.max_usage, data.timestamp)
        current_max = get_max_usage(data.hostname, data.cgroup)

        if current_max is None or data.max_usage >  current_max:
            insert_memory_usage(data.hostname, data.cgroup, data.max_usage, data.timestamp)
            return {"status": "inserted"}
        else:
            return {"status": "ignored - not higher than current max"}
         
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

