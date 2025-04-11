import os
import sqlite3
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Header
from typing import Optional
import sys
from openstack import connection
import openstack
import openstack.connection
import openstack.orchestration
import openstack.orchestration.v1
import openstack.orchestration.v1.stack
from psycopg2 import Timestamp

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(verbose=True, override=True)

db = sqlite3.connect("app.db")

app = FastAPI()
cloud = openstack.connect(cloud="envvars")
heat = openstack.orchestration.v1._proxy.Proxy(cloud)

lastest_request = None


@app.get("/")
def read_root():

    return {
        "Hello": "World!",
        "lastest_request": lastest_request,
        "cloud": {
            "auth": cloud.auth,
            # "endpoint": cloud.list_endpoints(),
        },
    }


@app.post("/heat/{stack_id}/{method}")
async def scale(
    request: Request,
    stack_id: str,
    method: str,
    authorization: Optional[str] = Header(None),
):
    # Extract route
    route = request.url.path

    # Extract headers
    headers = dict(request.headers)

    # Extract body (try JSON, fall back to raw)
    try:
        body = await request.json()
    except Exception:
        body = await request.body()
        body = body.decode("utf-8")

    try:
        stack = cloud.get_stack(stack_id)
        print(stack)
    except Exception:
        pass

    response_data = {
        "route": route,
        "auth_token": authorization or "No Authorization header",
        "stack": {
            "id": stack_id,
        },
        "headers": headers,
        "body": body,
        # "timestamp": timestamp,
    }
    lastest_request = response_data

    # print("Received POST request:", response_data)
    print("Received SCALE request")
    return None


@app.post("/{full_path:path}")
async def catch_all(request: Request):
    print("Received POST request:", request.url.path)
    pass


if __name__ == "__main__":
    # ray_app = FastAPIWrapper.bind()
    os.system(
        "uvicorn app.main:app --reload --host 0.0.0.0 --port 8080 --env-file .env"
    )
    # os.system("serve run main:ray_app")
