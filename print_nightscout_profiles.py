#!/usr/bin/env python
"""
Fetch profile changes from nightscout and display their contents
"""

# Make it work on both python 2 and 3
# Probably a bit wide, but I'm still learning
from __future__ import absolute_import, with_statement, print_function, unicode_literals

# Built-in modules
import argparse
from datetime import datetime
import json
import logging

# External modules
import requests
from texttable import Texttable

logging.basicConfig(level=logging.INFO)

TIMED_ENTRIES = ['carbratio', 'sens', 'basal', 'target_low', 'target_high']


def normalize(profile, entry):
    """
    Set entry to blank if it doesn't exist, thus avoiding KeyError
    """
    try:
        if profile[entry]:
            pass
    except KeyError:
        profile[entry] = ''


def normalize_entry(entry):
    """
    Clean up an entry before further processing
    """
    logging.debug("Normalizing entry: %s", entry)
    try:
        if entry["timeAsSeconds"]:
            pass
    except KeyError:
        entry_timeasseconds = datetime.strptime(entry["time"], "%H:%M")
        entry[
            "timeAsSeconds"] = 3600 * entry_timeasseconds.hour + 60 * entry_timeasseconds.minute
    try:
        if entry["time"]:
            pass
    except KeyError:
        entry_hour = int(entry['timeAsSeconds'] / 3600)
        entry_minute = int(entry['timeAsSeconds'] % 60)
        entry["time"] = str(entry_hour).rjust(
            2, '0') + ":" + str(entry_minute).rjust(2, '0')
    entry["start"] = entry["time"] + ":00"
    entry["minutes"] = int(entry["timeAsSeconds"]) / 60


def get_profile_switches(nightscout, token, date_from, count):
    """
    Get list of profile switch events
    """
    p_url = (
        nightscout +
        "/api/v1/treatments.json?find[eventType][$eq]=Profile%20Switch&count="
        + count + "&find[created_at][$gte]=" + date_from)
    if token is not None:
        p_url = p_url + "&token=" + token
    p_switch = requests.get(p_url).json()
    logging.debug("Profiles: %s", p_switch)
    for profile in p_switch:
        print("Profile named {} enabled at {} for duration {}".format(
            profile['profile'], profile['created_at'], profile['duration']))
        extracted_profile = json.loads(profile['profileJson'])
        extracted_profile['name'] = profile['profile']
        for key in ['timezone', 'delay', 'startDate']:
            normalize(extracted_profile, key)
        for entry_type in TIMED_ENTRIES:
            for entry in extracted_profile[entry_type]:
                normalize_entry(entry)
        display_text(extracted_profile)


def display_text(p_data):
    """
    Display profile in text format
    """
    # p_data = profile_data[0]["store"][profile_name]
    logging.debug("Data keys: %s", p_data.keys())

    # Single value data
    singletons = Texttable()
    singletons.set_deco(Texttable.HEADER)
    singletons.set_cols_align(["c", "c", "c", "c", "c", "c"])
    singletons.add_rows([
        ["Profile name", "Timezone", "Units", "DIA", "Delay", "Start date"],
        [
            p_data["name"],
            p_data["timezone"],
            p_data["units"],
            p_data["dia"],
            p_data["delay"],
            p_data["startDate"],
        ],
    ])
    print(singletons.draw() + "\n")

    times = {}
    tgt_low = {v["time"]: v["value"] for v in p_data["target_low"]}
    tgt_high = {v["time"]: v["value"] for v in p_data["target_high"]}
    carb_ratio = {v["time"]: v["value"] for v in p_data["carbratio"]}
    sens = {v["time"]: v["value"] for v in p_data["sens"]}
    basal = {v["time"]: v["value"] for v in p_data["basal"]}
    logging.debug(tgt_high, tgt_low, carb_ratio, sens, basal)
    for (time, basal) in basal.items():
        times.setdefault(time, {})
        times[time]["basal"] = basal
    for (time, sens) in sens.items():
        times.setdefault(time, {})
        times[time]["sens"] = sens
    for (time, c_r) in carb_ratio.items():
        times.setdefault(time, {})
        times[time]["carbratio"] = c_r
    for (time, tgt_h) in tgt_high.items():
        times.setdefault(time, {})
        times[time]["tgt_high"] = tgt_h
    for (time, tgt_l) in tgt_low.items():
        times.setdefault(time, {})
        times[time]["tgt_low"] = tgt_l
    logging.debug("Times: %s", times)

    times_list = [["Time", "Basal", "ISF", "CR", "Target Low", "Target High"]]
    for time in sorted(times.keys()):
        times_list.append([
            time,
            times[time].get("basal", ""),
            times[time].get("sens", ""),
            times[time].get("carbratio", ""),
            times[time].get("tgt_low", ""),
            times[time].get("tgt_high", ""),
        ])
    times_table = Texttable()
    times_table.set_cols_align(["c", "c", "c", "c", "c", "c"])
    times_table.add_rows(times_list)
    print(times_table.draw() + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Get nightscout profile.")
    parser.add_argument(
        "--nightscout",
        help="Nightscout URL",
        required=True,
        nargs="?",
        const="http://127.0.0.1:1337",
        default="http://127.0.0.1:1337",
    )
    parser.add_argument("--token", help="Authenticaton token")
    parser.add_argument("--from",
                        help="Starting date to look for profile change events",
                        dest="date_from")
    parser.add_argument("--count", help="Number of profiles to display")

    logging.debug(vars(parser.parse_args()))

    # https://stackoverflow.com/questions/4575747/get-selected-subcommand-with-argparse/44948406#44948406
    # I have no idea what it does, but it seems to do the trick
    kwargs = vars(parser.parse_args())
    get_profile_switches(**kwargs)
