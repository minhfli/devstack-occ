import openstack.connection
from openstack.orchestration.v1.stack import Stack
import openstack
import json
from datetime import datetime, timezone
import logging
from dotenv import load_dotenv
import subprocess
import os
import sys

# temp, to make stack update only once
stack_update_delay = 1000  # seconds

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


def update_scale_level(stack: Stack, level: int, wait: bool = False):
    my_env = os.environ.copy()
    my_env["PATH"] = f"/usr/sbin:/sbin:{my_env['PATH']}"
    # openstack stack update -e env1.yaml --existing stack0

    if wait == False:
        subprocess.run(
            [
                "openstack",
                "stack",
                "update",
                "--parameter",
                f"VDU1-scale-level={json.dumps(scale_levels[level])}",
                "--existing",
                stack.name,
            ],
            env=my_env,
            stderr=sys.stderr,
            stdout=sys.stdout,
        )
    else:
        subprocess.run(
            [
                "openstack",
                "stack",
                "update",
                "--parameter",
                f"VDU1-scale-level={json.dumps(scale_levels[level])}",
                "--wait",
                "--existing",
                stack.name,
            ],
            env=my_env,
            stderr=sys.stderr,
            stdout=sys.stdout,
        )


def handle_scale_request(
    stack: Stack,
    method: str,
    alarm_body: dict,
    cloud: openstack.connection.Connection,
):
    if stack.status != "UPDATE_COMPLETE" and stack.status != "CREATE_COMPLETE":
        logging.warning("Stack is not in a valid state for scaling")
        return

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

    if new_scale_level == current_scale_level["level"]:
        logging.info("No scaling needed")
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

    if time_passed.total_seconds() < stack_update_delay:
        logging.warning(
            f"Stack update delay not met: {time_passed.total_seconds()} < {stack_update_delay}"
        )
        return

    # Update the stack
    update_scale_level(stack=stack, level=new_scale_level, wait=False)
    logging.info("Stack updated")


if __name__ == "__main__":
    load_dotenv(verbose=True, override=True)

    cloud = openstack.connect()
    stack = cloud.get_stack("stack0")

    update_scale_level(stack=stack, level=1, wait=True)

    print("Stack updated")
    # print(cloud.get_stack("stack0"))
