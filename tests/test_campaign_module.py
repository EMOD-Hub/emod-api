import json
import os
from emod_api import campaign as api_campaign
from emod_api import schema_to_class as s2c

from tests import manifest


def generate_sample_campaign_event(my_campaign, schema_path):
    with open(schema_path) as fid01:
        schema_json = json.load(fid01)

    broadcast_event = s2c.get_class_with_defaults("BroadcastEvent", schema_json=schema_json)
    broadcast_event.Broadcast_Event = my_campaign.get_send_trigger("Test_Event", old=True)

    coordinator = s2c.get_class_with_defaults("StandardInterventionDistributionEventCoordinator", schema_json=schema_json)
    coordinator.Intervention_Config = broadcast_event

    event = s2c.get_class_with_defaults("CampaignEvent", schema_json=schema_json)
    event.Event_Coordinator_Config = coordinator
    return event


class TestCampaign():
    def setUp(self):
        self.campaign = api_campaign
        self.schema_path = manifest.common_schema_path

    def test_reset(self):
        self.campaign.set_schema(self.schema_path)
        sample_event = generate_sample_campaign_event(self.campaign, manifest.common_schema_path)
        self.campaign.add(sample_event)
        self.campaign.reset()
        self.assertEqual(self.campaign.campaign_dict["Events"], [])

    def test_set_schema(self):
        self.campaign.set_schema(self.schema_path)
        self.assertEqual(self.campaign.schema_path, self.schema_path)
        self.assertEqual(len(self.campaign.campaign_dict['Events']), 0)

    def test_get_schema(self):
        self.campaign.set_schema(self.schema_path)
        schema = self.campaign.get_schema()
        with open(self.schema_path) as schema_file:
            expected_schema = json.load(schema_file)
        self.assertDictEqual(schema, expected_schema)
        self.assertIsNotNone(schema)

    def test_add(self):
        self.campaign.set_schema(self.schema_path)
        sample_event = generate_sample_campaign_event(self.campaign, manifest.common_schema_path)
        self.campaign.add(sample_event, name="TestEvent")
        self.assertEqual(len(self.campaign.campaign_dict["Events"]), 1)
        self.assertEqual(self.campaign.campaign_dict["Events"][0]["Event_Name"], "TestEvent")

    def test_get_trigger_list(self):
        self.campaign.set_schema(self.schema_path)
        trigger_list = self.campaign.get_trigger_list()
        self.assertIsNotNone(trigger_list)
        self.assertNotIn("Test_Event", trigger_list)

    def test_save(self):
        filename = os.path.join(manifest.output_folder, 'test_campaign.json')
        self.campaign.set_schema(self.schema_path)
        sample_event = generate_sample_campaign_event(self.campaign, manifest.common_schema_path)
        self.campaign.add(sample_event)
        saved_filename = self.campaign.save(filename)
        self.assertEqual(saved_filename, filename)
        with open(filename, "r") as file:
            data = json.load(file)
            self.assertDictEqual(data, self.campaign.campaign_dict)

    def test_get_adhocs(self):
        self.campaign.set_schema(self.schema_path)
        sample_event = generate_sample_campaign_event(self.campaign, manifest.common_schema_path)
        self.campaign.add(sample_event)
        adhocs = self.campaign.get_adhocs()
        self.assertDictEqual(adhocs, {'Test_Event': 'Test_Event'})

    def test_get_recv_trigger(self):
        self.campaign.set_schema(self.schema_path)
        trigger = "TestTrigger1"
        recv_trigger = self.campaign.get_recv_trigger(trigger, old=True)
        self.assertIn(trigger, self.campaign.pubsub_signals_subbing)
        self.assertEqual(recv_trigger, trigger)

    def test_get_send_trigger(self):
        self.campaign.set_schema(self.schema_path)
        trigger = "TestTrigger2"
        send_trigger = self.campaign.get_send_trigger(trigger, old=True)
        self.assertIn(trigger, self.campaign.pubsub_signals_pubbing)
        self.assertEqual(send_trigger, trigger)

    def test_get_event(self):
        self.campaign.set_schema(self.schema_path)
        event = "TestEvent"
        mapped_event = self.campaign.get_event(event, old=True)
        self.assertEqual(mapped_event, event)
