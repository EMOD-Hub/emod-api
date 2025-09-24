#!/usr/bin/env python
"""
You use this simple campaign builder by importing it, adding valid events via "add", and writing it out with "save".
"""

import json

schema_path = None
schema_json = None
campaign_dict = {"Events": [], "Use_Defaults": 1}
pubsub_signals_subbing = []
pubsub_signals_pubbing = []
adhocs = []
custom_coordinator_events = []
custom_node_events = []
event_map = {}
use_old_adhoc_handling = False
unsafe = False
implicits = list()
trigger_list = None


def reset():
    del (campaign_dict["Events"][:])
    global pubsub_signals_subbing
    global pubsub_signals_pubbing
    global adhocs
    global event_map
    del (pubsub_signals_subbing[:])
    del (pubsub_signals_pubbing[:])
    del (adhocs[:])
    del (custom_coordinator_events[:])
    del (custom_node_events[:])
    event_map = {}
    from emod_api import schema_to_class as s2c
    s2c.clear_schema_cache()
    del (implicits[:])


def set_schema(schema_path_in):
    """
    Set the (path to) the schema file. And reset all campaign variables. This is essentially a
    "start_building_campaign" function.

    Args:
        schema_path_in. The path to a schema.json.
    Returns:
        Nothing
    """
    reset()
    global schema_path, schema_json

    schema_path = schema_path_in
    with open(schema_path_in) as schema_file:
        schema_json = json.load(schema_file)


def get_schema():
    return schema_json


def add(event, name=None, first=False):
    """
    Add a complete campaign event to the campaign builder. The new event is assumed to be a Python dict, and a 
    valid event. The new event is not validated here. 
    Set the first flag to True if this is the first event in a campaign because it functions as an
    accumulator and in some situations like sweeps it might have been used recently.
    """
    event.finalize()
    if first:
        print("Use of 'first' flag is deprecated. Use set_schema to start build a new, empty campaign.")
        global campaign_dict
        campaign_dict["Events"] = []
    if "Event_Name" not in event and name is not None:
        event["Event_Name"] = name
    if "Listening" in event:
        pubsub_signals_subbing.extend(event["Listening"])
        event.pop("Listening")
    if "Broadcasting" in event:
        pubsub_signals_pubbing.extend(event["Broadcasting"])
        event.pop("Broadcasting")
    campaign_dict["Events"].append(event)


def get_trigger_list():
    global trigger_list
    if get_schema():
        # This needs to be fixed in the schema post-processor: maybe create a new idmTime:EventEnum and replace
        # all the occurrences with a reference to that.
        try:
            trigger_list = get_schema()["idmTypes"]["idmAbstractType:EventCoordinator"]["BroadcastCoordinatorEvent"][
                "Broadcast_Event"]["enum"]
        except Exception as ex:
            trigger_list = get_schema()["idmTypes"]["idmType:IncidenceCounter"]["Trigger_Condition_List"]["Built-in"]
    return trigger_list


def save(filename="campaign.json"):
    """
    Save 'campaign_dict' as file named 'filename'.
    """
    with open(filename, "w") as camp_file:
        json.dump(campaign_dict, camp_file, sort_keys=True, indent=4)
    import copy
    ignored_events = copy.deepcopy(set(pubsub_signals_pubbing))
    non_camp_events = set()
    if len(pubsub_signals_subbing) > 0:
        for event in set(pubsub_signals_subbing):
            if event in ignored_events:
                ignored_events.remove(event)
    if len(non_camp_events) > 0:
        for event in set(non_camp_events):
            if event in get_adhocs() and not unsafe:
                raise RuntimeError(f"ERROR: Report is configured to LISTEN to the following non-existent event: \n"
                                   f"{event} \nPlease fix the error.\n")
    return filename


def get_adhocs():
    return event_map


def get_custom_coordinator_events():
    return list(set(custom_coordinator_events))


def get_custom_node_events():
    return list(set(custom_node_events))


def get_recv_trigger(trigger, old=use_old_adhoc_handling):
    """
    Get the correct representation of a trigger (also called signal or even event) that is being listened to.
    """
    pubsub_signals_subbing.append(trigger)
    return get_event(trigger, old)


def get_send_trigger(trigger, old=use_old_adhoc_handling):
    """
    Get the correct representation of a trigger (also called signal or even event) that is being broadcast.
    """
    pubsub_signals_pubbing.append(trigger)
    return get_event(trigger, old)


def get_event(event, old=False):
    """
    Basic placeholder functionality for now. This will map new ad-hoc events to GP_EVENTs and manage that 'cache'
    If event in built-ins, return event, else if in adhoc map, return mapped event, else add to adhoc_map and return
    mapped event.
    """
    if event is None or event == "":
        raise ValueError("campaign.get_event() called with an empty event. Please specify a string.")

    return_event = None
    global trigger_list
    if trigger_list is None:
        trigger_list = get_trigger_list()

    if event in trigger_list:
        return_event = event
    elif event in event_map:
        return_event = event_map[event]
    else:
        # get next entry in GP_EVENT_xxx
        new_event_name = event if old else 'GP_EVENT_{:03d}'.format(len(event_map))
        event_map[event] = new_event_name
        return_event = event_map[event]
    return return_event
