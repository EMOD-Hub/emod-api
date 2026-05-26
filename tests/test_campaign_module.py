import unittest
import json
import os
import tempfile
import warnings

from emod_api import campaign as api_campaign
from emod_api import schema_to_class as s2c

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
OUTPUT_FOLDER = os.path.join(CURRENT_DIR, 'output')
if not os.path.isdir(OUTPUT_FOLDER):
    os.mkdir(OUTPUT_FOLDER)

SCHEMA_CANDIDATES = [
    os.path.join(CURRENT_DIR, 'package', 'common', 'schema.json'),
    os.path.join(CURRENT_DIR, 'package', 'generic', 'schema.json'),
    os.path.join(CURRENT_DIR, 'package', 'malaria', 'schema.json'),
    os.path.join(os.path.dirname(CURRENT_DIR), '..', 'emodpy-malaria',
                 'tests', 'unittests', 'current_schema', 'schema.json'),
]

SCHEMA_PATH = None
for candidate in SCHEMA_CANDIDATES:
    if os.path.isfile(candidate):
        SCHEMA_PATH = candidate
        break


def generate_sample_campaign_event(my_campaign, schema_path):
    with open(schema_path) as fid01:
        schema_json = json.load(fid01)

    broadcast_event = s2c.get_class_with_defaults("BroadcastEvent", schema_json=schema_json)
    broadcast_event.Broadcast_Event = my_campaign.get_send_trigger("Test_Event", old=True)

    coordinator = s2c.get_class_with_defaults(
        "StandardInterventionDistributionEventCoordinator", schema_json=schema_json)
    coordinator.Intervention_Config = broadcast_event

    event = s2c.get_class_with_defaults("CampaignEvent", schema_json=schema_json)
    event.Event_Coordinator_Config = coordinator
    return event


@unittest.skipIf(SCHEMA_PATH is None, "No schema.json found")
class TestCampaignWithSchema(unittest.TestCase):
    """Tests that require a real schema file."""

    def setUp(self):
        self.campaign = api_campaign
        self.campaign.set_schema(SCHEMA_PATH)

    def tearDown(self):
        self.campaign.reset()

    def test_reset_clears_all_state(self):
        sample_event = generate_sample_campaign_event(self.campaign, SCHEMA_PATH)
        self.campaign.add(sample_event)
        self.campaign.get_recv_trigger("Evt1")
        self.campaign.get_send_trigger("Evt2")
        self.campaign.set_listened_node_event("NEvt1")
        self.campaign.set_broadcast_node_event("NEvt2")
        self.campaign.set_listened_coordinator_event("CEvt1")
        self.campaign.set_broadcast_coordinator_event("CEvt2")

        self.campaign.reset()

        self.assertEqual(self.campaign.campaign_dict["Events"], [])
        self.assertEqual(self.campaign.individual_events_listened, [])
        self.assertEqual(self.campaign.individual_events_broadcast, [])
        self.assertEqual(self.campaign.node_events_listened, [])
        self.assertEqual(self.campaign.node_events_broadcast, [])
        self.assertEqual(self.campaign.coordinator_events_listened, [])
        self.assertEqual(self.campaign.coordinator_events_broadcast, [])
        self.assertEqual(self.campaign.individual_builtin_events, [])
        self.assertEqual(self.campaign.node_builtin_events, [])
        self.assertEqual(self.campaign.coordinator_builtin_events, [])

    def test_set_schema_sets_path(self):
        self.assertEqual(self.campaign.schema_path, SCHEMA_PATH)

    def test_set_schema_populates_individual_builtin_events(self):
        self.assertGreater(len(self.campaign.individual_builtin_events), 0)

    def test_get_schema_returns_loaded_json(self):
        schema = self.campaign.get_schema()
        self.assertIsNotNone(schema)
        with open(SCHEMA_PATH) as f:
            expected = json.load(f)
        self.assertDictEqual(schema, expected)

    def test_add_event(self):
        sample_event = generate_sample_campaign_event(self.campaign, SCHEMA_PATH)
        self.campaign.add(sample_event, note="TestNote")
        self.assertEqual(len(self.campaign.campaign_dict["Events"]), 1)
        self.assertEqual(self.campaign.campaign_dict["Events"][0]["Note"], "TestNote")

    def test_save(self):
        filename = os.path.join(OUTPUT_FOLDER, 'test_campaign.json')
        sample_event = generate_sample_campaign_event(self.campaign, SCHEMA_PATH)
        self.campaign.add(sample_event)
        saved = self.campaign.save(filename)
        self.assertEqual(saved, filename)
        with open(filename) as f:
            data = json.load(f)
        self.assertDictEqual(data, self.campaign.campaign_dict)

    def test_get_custom_individual_events_builtin_excluded(self):
        if not self.campaign.individual_builtin_events:
            self.skipTest("No individual builtin events in schema")
        builtin_event = self.campaign.individual_builtin_events[0]
        self.campaign.get_recv_trigger(builtin_event)
        result = self.campaign.get_custom_individual_events()
        self.assertNotIn(builtin_event, result)

    def test_get_custom_individual_events_broadcast_mirrors_builtin_warns(self):
        if not self.campaign.individual_builtin_events:
            self.skipTest("No individual builtin events in schema")
        builtin_event = self.campaign.individual_builtin_events[0]
        self.campaign.get_send_trigger(builtin_event)
        with self.assertWarns(UserWarning):
            self.campaign.get_custom_individual_events()


class TestEventRegistration(unittest.TestCase):
    """Tests for event registration functions (no schema needed)."""

    def setUp(self):
        self.campaign = api_campaign
        self.campaign.reset()

    def tearDown(self):
        self.campaign.reset()

    def test_get_recv_trigger(self):
        result = self.campaign.get_recv_trigger("MyListenEvent")
        self.assertEqual(result, "MyListenEvent")
        self.assertIn("MyListenEvent", self.campaign.individual_events_listened)

    def test_get_send_trigger(self):
        result = self.campaign.get_send_trigger("MyBroadcastEvent")
        self.assertEqual(result, "MyBroadcastEvent")
        self.assertIn("MyBroadcastEvent", self.campaign.individual_events_broadcast)

    def test_set_listened_node_event(self):
        result = self.campaign.set_listened_node_event("NodeListenEvent")
        self.assertEqual(result, "NodeListenEvent")
        self.assertIn("NodeListenEvent", self.campaign.node_events_listened)

    def test_set_broadcast_node_event(self):
        result = self.campaign.set_broadcast_node_event("NodeBroadcastEvent")
        self.assertEqual(result, "NodeBroadcastEvent")
        self.assertIn("NodeBroadcastEvent", self.campaign.node_events_broadcast)

    def test_set_listened_coordinator_event(self):
        result = self.campaign.set_listened_coordinator_event("CoordListenEvent")
        self.assertEqual(result, "CoordListenEvent")
        self.assertIn("CoordListenEvent", self.campaign.coordinator_events_listened)

    def test_set_broadcast_coordinator_event(self):
        result = self.campaign.set_broadcast_coordinator_event("CoordBroadcastEvent")
        self.assertEqual(result, "CoordBroadcastEvent")
        self.assertIn("CoordBroadcastEvent", self.campaign.coordinator_events_broadcast)


class TestValidateCustomEvents(unittest.TestCase):
    """Tests for _validate_custom_events and get_custom_* functions."""

    def setUp(self):
        self.campaign = api_campaign
        self.campaign.reset()

    def tearDown(self):
        self.campaign.reset()

    # --- individual ---

    def test_individual_valid_pair(self):
        self.campaign.get_recv_trigger("CustomEvt")
        self.campaign.get_send_trigger("CustomEvt")
        result = self.campaign.get_custom_individual_events()
        self.assertIn("CustomEvt", result)

    def test_individual_listened_not_broadcast_raises(self):
        self.campaign.get_recv_trigger("OrphanedEvt")
        with self.assertRaises(ValueError):
            self.campaign.get_custom_individual_events()

    def test_individual_broadcast_not_listened_warns(self):
        self.campaign.get_send_trigger("UnlistenedEvt")
        with self.assertWarns(UserWarning):
            self.campaign.get_custom_individual_events()

    # --- node ---

    def test_node_valid_pair(self):
        self.campaign.set_listened_node_event("NodeEvt")
        self.campaign.set_broadcast_node_event("NodeEvt")
        result = self.campaign.get_custom_node_events()
        self.assertIn("NodeEvt", result)

    def test_node_listened_not_broadcast_raises(self):
        self.campaign.set_listened_node_event("OrphanedNodeEvt")
        with self.assertRaises(ValueError):
            self.campaign.get_custom_node_events()

    def test_node_broadcast_not_listened_warns(self):
        self.campaign.set_broadcast_node_event("UnlistenedNodeEvt")
        with self.assertWarns(UserWarning):
            self.campaign.get_custom_node_events()

    # --- coordinator ---

    def test_coordinator_valid_pair(self):
        self.campaign.set_listened_coordinator_event("CoordEvt")
        self.campaign.set_broadcast_coordinator_event("CoordEvt")
        result = self.campaign.get_custom_coordinator_events()
        self.assertIn("CoordEvt", result)

    def test_coordinator_listened_not_broadcast_raises(self):
        self.campaign.set_listened_coordinator_event("OrphanedCoordEvt")
        with self.assertRaises(ValueError):
            self.campaign.get_custom_coordinator_events()

    def test_coordinator_broadcast_not_listened_warns(self):
        self.campaign.set_broadcast_coordinator_event("UnlistenedCoordEvt")
        with self.assertWarns(UserWarning):
            self.campaign.get_custom_coordinator_events()

    # --- builtin filtering ---

    def test_builtin_events_excluded_from_validation(self):
        builtins = ["BuiltinA", "BuiltinB"]
        result = api_campaign._validate_custom_events(
            listened_list=["BuiltinA", "CustomEvt"],
            broadcast_list=["CustomEvt"],
            builtin_list=builtins,
            level="test"
        )
        self.assertIn("CustomEvt", result)
        self.assertNotIn("BuiltinA", result)

    def test_broadcast_mirrors_builtin_warns(self):
        with self.assertWarns(UserWarning):
            api_campaign._validate_custom_events(
                listened_list=[],
                broadcast_list=["BuiltinA"],
                builtin_list=["BuiltinA"],
                level="test"
            )

    def test_empty_lists_returns_empty(self):
        result = api_campaign._validate_custom_events(
            listened_list=[],
            broadcast_list=[],
            builtin_list=[],
            level="test"
        )
        self.assertEqual(result, [])


class TestFindBuiltinEvents(unittest.TestCase):
    """Tests for _find_builtin_events schema search."""

    def test_finds_builtin_key(self):
        schema = {
            "idmTypes": {
                "ReportEventRecorder": {
                    "Report_Event_Recorder_Events": {
                        "Built-in": ["Births", "Deaths"],
                        "enum": ["ShouldNotUseThis"]
                    }
                }
            }
        }
        result = api_campaign._find_builtin_events(
            schema, "ReportEventRecorder", "Report_Event_Recorder_Events")
        self.assertEqual(result, ["Births", "Deaths"])

    def test_falls_back_to_enum(self):
        schema = {
            "idmTypes": {
                "ReportEventRecorder": {
                    "Report_Event_Recorder_Events": {
                        "enum": ["Births", "Deaths"]
                    }
                }
            }
        }
        result = api_campaign._find_builtin_events(
            schema, "ReportEventRecorder", "Report_Event_Recorder_Events")
        self.assertEqual(result, ["Births", "Deaths"])

    def test_returns_none_when_reporter_not_found(self):
        schema = {"idmTypes": {"SomethingElse": {}}}
        result = api_campaign._find_builtin_events(
            schema, "ReportEventRecorder", "Report_Event_Recorder_Events")
        self.assertIsNone(result)

    def test_returns_none_when_reporter_has_no_events_key(self):
        schema = {
            "idmTypes": {
                "ReportEventRecorder": {
                    "SomeOtherParam": 42
                }
            }
        }
        result = api_campaign._find_builtin_events(
            schema, "ReportEventRecorder", "Report_Event_Recorder_Events")
        self.assertIsNone(result)

    def test_stops_recursing_children_after_reporter_key_match(self):
        schema = {
            "wrapper": {
                "ReportEventRecorder": {"NotTheRightKey": {}},
                "nested_child": {
                    "ReportEventRecorder": {
                        "Report_Event_Recorder_Events": {
                            "Built-in": ["ShouldNotReach"]
                        }
                    }
                }
            }
        }
        result = api_campaign._find_builtin_events(
            schema, "ReportEventRecorder", "Report_Event_Recorder_Events")
        self.assertIsNone(result)

    def test_finds_deeply_nested_reporter(self):
        schema = {
            "level1": {
                "level2": {
                    "level3": {
                        "ReportEventRecorderNode": {
                            "Report_Node_Event_Recorder_Events": {
                                "Built-in": ["NodeEvt1", "NodeEvt2"]
                            }
                        }
                    }
                }
            }
        }
        result = api_campaign._find_builtin_events(
            schema, "ReportEventRecorderNode", "Report_Node_Event_Recorder_Events")
        self.assertEqual(result, ["NodeEvt1", "NodeEvt2"])


if __name__ == '__main__':
    unittest.main()
