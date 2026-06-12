#!/usr/bin/env python
"""Simple campaign builder for EMOD simulations.

Import this module, add valid campaign events via ``add``, and write the
campaign file with ``save``.
"""

import json
import warnings

from emod_api import schema_to_class as s2c

schema_path = None
_schema_json = None
campaign_dict = {"Events": [], "Use_Defaults": 1}
individual_events_listened = []
individual_events_broadcast = []
node_events_broadcast = []
node_events_listened = []
coordinator_events_broadcast = []
coordinator_events_listened = []
use_old_adhoc_handling = False
unsafe = False
implicits = list()
individual_builtin_events = []
node_builtin_events = []
coordinator_builtin_events = []


def reset():
    """Reset all campaign state to defaults.

    Clears accumulated events, signal tracking lists, event mappings,
    and the schema cache.
    """
    campaign_dict["Events"].clear()

    individual_events_listened.clear()
    individual_events_broadcast.clear()
    node_events_broadcast.clear()
    node_events_listened.clear()
    coordinator_events_broadcast.clear()
    coordinator_events_listened.clear()
    implicits.clear()
    individual_builtin_events.clear()
    node_builtin_events.clear()
    coordinator_builtin_events.clear()
    s2c.clear_schema_cache()


def _find_builtin_events(schema, reporter_key, events_key):
    """Recursively find a builtin events using reporter entry and extract its event list.

    Walks the schema looking for ``reporter_key`` as a dict key. When
    found, looks up ``events_key`` inside it and returns the
    ``"Built-in"`` list if present, otherwise the ``"enum"`` list (used in EMOD-Generic)

    Args:
        schema: The schema JSON object (or sub-object) to search.
        reporter_key: The reporter key to find (e.g.
            ``"ReportEventRecorder"``).
        events_key: The events parameter inside the reporter (e.g.
            ``"Report_Event_Recorder_Events"``).

    Returns:
        A list of event name strings, or ``None`` if the reporter
        or its event list is not found.
    """
    if isinstance(schema, dict):
        if reporter_key in schema:
            events_entry = schema[reporter_key]
            if isinstance(events_entry, dict):
                events_param = events_entry.get(events_key)
                if isinstance(events_param, dict):
                    builtin = events_param.get("Built-in")
                    if isinstance(builtin, list):
                        return builtin
                    enum = events_param.get("enum")
                    if isinstance(enum, list):
                        return enum
            return None
        for value in schema.values():
            result = _find_builtin_events(value, reporter_key, events_key)
            if result is not None:
                return result
    elif isinstance(schema, list):
        for item in schema:
            result = _find_builtin_events(item, reporter_key, events_key)
            if result is not None:
                return result
    return None


def set_schema(schema_path_in):
    """Set the schema file path and reset all campaign state.

    This is essentially the "start building a campaign" entry point.
    It clears any previously accumulated events and loads the new schema.
    Also extracts built-in event lists for individual, node, and
    coordinator levels by recursively searching for
    ``ReportEventRecorder``, ``ReportEventRecorderNode``, and
    ``ReportEventRecorderCoordinator`` in the schema.

    Args:
        schema_path_in: Path to a ``schema.json`` file.
    """
    reset()
    global schema_path, _schema_json

    schema_path = schema_path_in
    with open(schema_path_in) as schema_file:
        _schema_json = json.load(schema_file)

    found = _find_builtin_events(_schema_json, "ReportEventRecorder", "Report_Event_Recorder_Events")
    if found:
        individual_builtin_events.extend(found)

    found = _find_builtin_events(_schema_json, "ReportEventRecorderNode", "Report_Node_Event_Recorder_Events")
    if found:
        node_builtin_events.extend(found)

    found = _find_builtin_events(_schema_json, "ReportEventRecorderCoordinator", "Report_Coordinator_Event_Recorder_Events")
    if found:
        coordinator_builtin_events.extend(found)


def get_schema():
    """Return the loaded schema JSON dictionary.

    Returns:
        The parsed schema dictionary, or ``None`` if ``set_schema`` has
        not been called.
    """
    return _schema_json


def add(event, note: str = None):
    """Add a complete campaign event to the campaign builder.

    The event is assumed to be valid and is not validated here.

    Args:
        event: A complete campaign event object. It must support
            ``finalize()`` and dict-style key assignment.
        note: An optional human-readable note added to the event
            inside the output ``campaign.json`` file.
    """
    event.finalize()
    if note is not None:
        event["Note"] = note
    campaign_dict["Events"].append(event)


def save(filename: str = "campaign.json"):
    """Save the accumulated campaign events to a JSON file.

    Args:
        filename: Output file path.

    Returns:
        The filename that was written.
    """
    with open(filename, "w") as camp_file:
        json.dump(campaign_dict, camp_file, sort_keys=True, indent=4)

    return filename


def _validate_custom_events(listened_list, broadcast_list, builtin_list, level):
    """Validate that listened-to events are broadcast and vice versa.

    Built-in events are excluded from validation since they are
    handled by the simulation engine and do not need to be explicitly
    broadcast or listened to in the campaign.

    Args:
        listened_list: List of event names being listened to.
        broadcast_list: List of event names being broadcast.
        builtin_list: List of built-in event names to exclude from
            validation.
        level: Label for the event level (e.g. ``"coordinator"``
            or ``"node"``) used in error/warning messages.

    Returns:
        A deduplicated list of custom (non-built-in) broadcast event
        name strings.

    Raises:
        ValueError: If any events are listened to but never broadcast.
    """
    builtins = set(builtin_list)

    broadcast_matching_builtins = set(broadcast_list) & builtins
    if broadcast_matching_builtins:
        warnings.warn(
            f"The following {level}-level broadcast events mirror built-in {level}-level events, "
            f"therefore these events will be broadcast by the simulation as well as the campaign: "
            f"{sorted(broadcast_matching_builtins)}")

    listened = set(listened_list) - builtins
    broadcast = set(broadcast_list) - builtins

    listened_not_broadcast = listened - broadcast
    if listened_not_broadcast:
        raise ValueError(
            f"The following {level}-level events are listened to but never broadcast. This means that any campaign "
            f"interventions that rely on listening to these events will never fire. Please fix the error by either "
            f"broadcasting these events in the campaign or removing the interventions that are listening for them:\n"
            f"{sorted(listened_not_broadcast)}")

    broadcast_not_listened = broadcast - listened
    if broadcast_not_listened:
        warnings.warn(
            f"The following {level} events are broadcast but nothing is listening to them within "
            f"the campaign: {sorted(broadcast_not_listened)}")

    return list(broadcast)


def get_custom_coordinator_events():
    """Validate and return deduplicated custom coordinator-level events.

    Returns:
        A list of unique coordinator event name strings that are broadcast
        in the campaign.

    Raises:
        ValueError: If any coordinator events are listened to but
            never broadcast.
    """
    return _validate_custom_events(coordinator_events_listened, coordinator_events_broadcast, coordinator_builtin_events, "coordinator")


def get_custom_node_events():
    """Validate and return deduplicated custom node-level events.

    Returns:
        A list of unique node event name strings that are broadcast
        in the campaign.

    Raises:
        ValueError: If any node events are listened to but
            never broadcast.
    """
    return _validate_custom_events(node_events_listened, node_events_broadcast, node_builtin_events, "node")


def get_custom_individual_events():
    """Validate and return deduplicated custom individual-level events.

    Returns:
        A list of unique individual event name strings that are broadcast
        in the campaign.

    Raises:
        ValueError: If any individual events are listened to but
            never broadcast.
    """
    return _validate_custom_events(individual_events_listened, individual_events_broadcast, individual_builtin_events, "individual")


def get_recv_trigger(trigger, old=use_old_adhoc_handling):
    """Register an individual-level event as listened to.

    Tracks which individual events are used throughout the simulation
    so that ``get_custom_individual_events`` can validate that every
    listened-to event has a corresponding broadcast.

    Args:
        trigger: The individual event name string.
        old: Unused. Kept for backwards compatibility.

    Returns:
        The event name, unchanged.
    """
    if not trigger:
        raise ValueError("Event name must not be None or empty.")
    individual_events_listened.append(trigger)
    return trigger


def set_listened_node_event(event: str) -> str:
    """Register a node-level event as listened to.

    Tracks which node events are used throughout the simulation so
    that ``get_custom_node_events`` can validate that every listened-to
    event has a corresponding broadcast.

    Args:
        event: The node event name string.

    Returns:
        The event name, unchanged.
    """
    if not event:
        raise ValueError("Event name must not be None or empty.")
    node_events_listened.append(event)
    return event


def set_listened_coordinator_event(event: str) -> str:
    """Register a coordinator-level event as listened to.

    Tracks which coordinator events are used throughout the simulation
    so that ``get_custom_coordinator_events`` can validate that every
    listened-to event has a corresponding broadcast.

    Args:
        event: The coordinator event name string.

    Returns:
        The event name, unchanged.
    """
    if not event:
        raise ValueError("Event name must not be None or empty.")
    coordinator_events_listened.append(event)
    return event


def get_send_trigger(trigger, old=use_old_adhoc_handling):
    """Register an individual-level event as broadcast.

    Args:
        trigger: The individual event name string.
        old: Unused. Kept for backwards compatibility.

    Returns:
        The event name, unchanged.
    """
    if not trigger:
        raise ValueError("Event name must not be None or empty.")
    individual_events_broadcast.append(trigger)
    return trigger


def set_broadcast_node_event(event: str) -> str:
    """Register a node-level event as broadcast.

    Tracks which node events are used throughout the simulation so
    that ``get_custom_node_events`` can validate that every broadcast
    event has something listening to it.

    Args:
        event: The node event name string.

    Returns:
        The event name, unchanged.
    """
    if not event:
        raise ValueError("Event name must not be None or empty.")
    node_events_broadcast.append(event)
    return event


def set_broadcast_coordinator_event(event: str) -> str:
    """Register a coordinator-level event as broadcast.

    Tracks which coordinator events are used throughout the simulation
    so that ``get_custom_coordinator_events`` can validate that every
    broadcast event has something listening to it.

    Args:
        event: The coordinator event name string.

    Returns:
        The event name, unchanged.
    """
    if not event:
        raise ValueError("Event name must not be None or empty.")
    coordinator_events_broadcast.append(event)
    return event
