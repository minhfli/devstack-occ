import openstack.connection
from openstack.orchestration.v1.stack import Stack
import openstack
import json
from datetime import datetime, timezone
import logging

# temp, to make stack update only once
stack_update_delay = 30000000  # seconds

scale_levels = [
    {
        "cpu_threshold_hi": 210000000000.0,
        "cpu_threshold_lo": 90000000000.0,
        "ram": 1024,
        "vcpu": 1,
        "level": 0,
    },
    {
        "cpu_threshold_hi": 420000000000.0,
        "cpu_threshold_lo": 180000000000.0,
        "ram": 1024,
        "vcpu": 2,
        "level": 1,
    },
    {
        "cpu_threshold_hi": 630000000000.0,
        "cpu_threshold_lo": 270000000000.0,
        "ram": 1024,
        "vcpu": 3,
        "level": 2,
    },
]


def get_current_scale_level(stack: Stack):
    stack_params = stack.parameters
    # logging.info(stack_params)
    return json.loads(stack_params.get("VDU1-scale-level", '{"level": 0}'))


def update_scale_level(
    cloud: openstack.connection.Connection, stack: Stack, level: int
):

    cloud.update_stack(
        stack.id,
        parameters={"VDU1-scale-level": json.dumps(scale_levels[level])},
        existing=True,
    )


def handle_scale_request(
    stack: Stack,
    method: str,
    alarm_body: dict,
    cloud: openstack.connection.Connection,
):
    # Determine the scale level
    current_scale_level = get_current_scale_level(stack)
    logging.info(current_scale_level)
    logging.info(method)
    if method == "scale_in":
        new_scale_level = max(current_scale_level["level"] - 1, 0)
    elif method == "scale_out":
        new_scale_level = min(current_scale_level["level"] + 1, 2)
    else:
        return

    # Chcck time for scaling
    logging.info(f"Scaling to {new_scale_level}")
    last_update_time = stack.updated_at
    if last_update_time is None:
        last_update_time = stack.created_at

    current_time = datetime.utcnow().replace(tzinfo=timezone.utc)
    last_update_time = datetime.strptime(
        last_update_time, "%Y-%m-%dT%H:%M:%SZ"
    ).replace(tzinfo=timezone.utc)

    logging.info("current time:    ", current_time)
    logging.info("last stack time: ", last_update_time)
    time_passed = current_time - last_update_time
    logging.debug("time passed (s): ", int(time_passed.total_seconds()))
