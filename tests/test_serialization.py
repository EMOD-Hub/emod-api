#!/usr/bin/python

from __future__ import print_function
import os
import gc
import os
import tempfile
import unittest
import time
import emod_api.serialization.dtkFileTools as dft
import emod_api.serialization.dtkFileSupport as support
import emod_api.serialization.SerializedPopulation as SerPop
from tests import manifest

skip_tests = False

@unittest.skipIf(skip_tests, "Skipping old tests to focus on V6")
class TestReadVersionOne(unittest.TestCase):

    def check_keys_dtkeader(self, header, reference_header_keys):
        for key in reference_header_keys:
            self.assertIsNotNone(header.get(key))
        return

    def test_dtkheader(self):
        header_1_keys = [
            'author',
            'bytecount',
            'chunkcount',
            'chunksizes',
            'compressed',
            'date',
            'tool',
            'version']
        self.check_keys_dtkeader(dft.DtkHeader(), header_1_keys)
        return

    def test_reading_uncompressed_file(self):

        jason_text = '{"simulation":{"__class__":"SimulationPython","serializationMask":0,"nodes":[]}}'

        dtk = dft.read(os.path.join(manifest.serialization_folder, "simple.dtk"))
        # noinspection SpellCheckingInspection
        self.assertEqual("clorton", dtk.author)
        self.assertEqual("notepad", dtk.tool)
        self.assertEqual(False, dtk.compressed)
        self.assertEqual(dft.NONE, dtk.compression)
        self.assertEqual(80, dtk.byte_count)
        self.assertEqual(1, dtk.chunk_count)
        self.assertEqual(80, dtk.chunk_sizes[0])
        self.assertEqual(jason_text.encode(), dtk.chunks[0])
        self.assertEqual(jason_text, dtk.contents[0])
        self.assertEqual("SimulationPython", dtk.simulation["__class__"])
        self.assertEqual(0, dtk.simulation.serializationMask)
        self.assertEqual(0, len(dtk.nodes))
        return

    @unittest.skipUnless(support.SNAPPY_SUPPORT, "No Snappy [de]compression support.")
    def test_reading_compressed_file(self):

        dtk = dft.read(os.path.join(manifest.serialization_folder, "version1.dtk"))
        self.assertEqual("", dtk.author)
        self.assertEqual("", dtk.tool)
        self.assertEqual(True, dtk.compressed)
        self.assertEqual(dft.SNAPPY, dtk.compression)
        self.assertEqual(1438033, dtk.byte_count)
        self.assertEqual(1, dtk.chunk_count)
        self.assertEqual(1438033, dtk.chunk_sizes[0])
        self.assertEqual(1, dtk.simulation.Run_Number)
        self.assertEqual(
            10001, dtk.simulation.individualHumanSuidGenerator.next_suid.id
        )
        self.assertEqual(0, dtk.simulation.sim_type)
        self.assertEqual(4, len(dtk.nodes))
        node = dtk.nodes[0]
        self.assertEqual(1, node.externalId)
        self.assertEqual(2500, len(node.individualHumans))
        human = node.individualHumans[0]
        self.assertEqual(1, human.cumulativeInfs)
        self.assertEqual(0, len(human.infections))
        self.assertEqual(0, human.infectiousness)
        self.assertEqual(9598.48, human.m_age)
        self.assertEqual(0, human.m_gender)
        self.assertEqual(False, human.m_is_infected)
        return

    @unittest.skipIf(support.SNAPPY_SUPPORT, "If Snappy support, test should not raise a UserWarning")
    def test_reading_compressed_file_exception(self):
        with self.assertRaises(UserWarning):
            dft.read(os.path.join(manifest.serialization_folder, "version1.dtk"))
        return

    def test_round_trip(self):
        source = dft.DtkFileV1()
        source.author = "dtkFileTests"
        source.compression = dft.SNAPPY if support.SNAPPY_SUPPORT else dft.NONE
        simulation = support.SerialObject(
            {
                "simulation": {
                    "enable_spatial_output": False,
                    "Run_Number": 1,
                    "enable_property_output": False,
                    "infectionSuidGenerator": {
                        "next_suid": {"id": 1},
                        "rank": 0,
                        "numtasks": 1,
                    },
                    "__class__": "Simulation",
                    "campaignFilename": "campaign.json",
                    "nodes": [
                        {
                            "node": {
                                "demographics_other": False,
                                "birth_rate_sinusoidal_forcing_phase": 0,
                                "sample_rate_20_plus": 0,
                                "max_sampling_cell_pop": 0,
                                "infectivity_boxcar_end_time": 0,
                                "sample_rate_18mo_4yr": 0,
                                "__class__": "Node",
                                "infectivity_boxcar_start_time": 0,
                                "demographics_gender": True,
                                "individualHumans": [
                                    {
                                        "migration_is_destination_new_home": False,
                                        "home_node_id": {"id": 1},
                                        "waiting_for_family_trip": False,
                                        "migration_will_return": True,
                                        "waypoints": [],
                                        "family_migration_type": 0,
                                        "Inf_Sample_Rate": 1,
                                        "migration_outbound": True,
                                        "m_mc_weight": 1,
                                        "migration_time_until_trip": 0,
                                        "StateChange": 0,
                                        "suid": {"id": 1},
                                        "leave_on_family_trip": False,
                                        "interventions": {
                                            "drugVaccineReducedTransmit": 1,
                                            "drugVaccineReducedAcquire": 1,
                                            "__class__": "InterventionsContainer",
                                            "drugVaccineReducedMortality": 1,
                                            "interventions": [],
                                        },
                                        "migration_destination": {"id": 0},
                                        "__class__": "IndividualHuman",
                                        "infectiousness": 0,
                                        "migration_mod": 1,
                                        "waypoints_trip_type": [],
                                        "m_age": 9588.48,
                                        "m_is_infected": False,
                                        "m_daily_mortality_rate": 0,
                                        "cumulativeInfs": 0,
                                        "family_migration_time_at_destination": 0,
                                        "family_migration_destination": {"id": 0},
                                        "m_new_infection_state": 0,
                                        "migration_time_at_destination": 0,
                                        "family_migration_is_destination_new_home": False,
                                        "migration_type": 0,
                                        "max_waypoints": 0,
                                        "pregnancy_timer": 0,
                                        "family_migration_time_until_trip": 0,
                                        "is_pregnant": False,
                                        "susceptibility": {
                                            "trandecayoffset": 0,
                                            "age": 9588.48,
                                            "__class__": "Susceptibility",
                                            "acqdecayoffset": 0,
                                            "mod_mortality": 1,
                                            "mod_acquire": 1,
                                            "mod_transmit": 1,
                                            "mortdecayoffset": 0,
                                        },
                                        "is_on_family_trip": False,
                                        "infections": [],
                                        "above_poverty": 0,
                                        "Properties": [],
                                        "m_gender": 0,
                                    }
                                ],
                                "serializationMask": 3,
                                "infectivity_sinusoidal_forcing_amplitude": 1,
                                "birth_rate_boxcar_start_time": 0,
                                "x_birth": 1,
                                "sample_rate_immune": 0,
                                "sample_rate_0_18mo": 0,
                                "population_scaling": 0,
                                "demographics_birth": False,
                                "suid": {"id": 1},
                                "birth_rate_boxcar_forcing_amplitude": 1,
                                "population_scaling_factor": 1,
                                "birth_rate_boxcar_end_time": 0,
                                "ind_sampling_type": 0,
                                "vital_birth_time_dependence": 0,
                                "externalId": 1,
                                "age_initialization_distribution_type": 1,
                                "infectivity_sinusoidal_forcing_phase": 0,
                                "immune_threshold_for_downsampling": 0,
                                "sample_rate_5_9": 0,
                                "home_individual_ids": [{"key": 1, "value": {"id": 1}}],
                                "sample_rate_birth": 0,
                                "birth_rate_sinusoidal_forcing_amplitude": 1,
                                "infectivity_boxcar_forcing_amplitude": 1,
                                "vital_birth": False,
                                "maternal_transmission": False,
                                "vital_birth_dependence": 1,
                                "infectivity_scaling": 0,
                                "sample_rate_10_14": 0,
                                "sample_rate_15_19": 0,
                            },
                            "suid": {"id": 1},
                        }
                    ],
                    "loadbalance_filename": "",
                    "serializationMask": 3,
                    "individualHumanSuidGenerator": {
                        "next_suid": {"id": 1001},
                        "rank": 0,
                        "numtasks": 1,
                    },
                    "sim_type": 0,
                    "enable_default_report": True,
                    "enable_event_report": False,
                    "Ind_Sample_Rate": 1,
                    "demographic_tracking": False,
                }
            }
        )
        source.objects.append(simulation)
        handle, filename = tempfile.mkstemp()
        os.close(handle)
        dft.write(source, filename)

        dest = dft.read(filename)
        os.remove(filename)
        self.assertEqual("dtkFileTests", dest.author)
        self.assertEqual(dft.SNAPPY if support.SNAPPY_SUPPORT else dft.NONE, dest.compression)
        simulation = dest.simulation
        self.assertEqual(False, simulation.enable_spatial_output)
        self.assertEqual(1, simulation.Run_Number)
        self.assertEqual(1001, simulation.individualHumanSuidGenerator.next_suid.id)
        self.assertEqual(0, simulation.sim_type)
        self.assertEqual(True, simulation.enable_default_report)
        node = simulation.nodes[0].node  # Simulation nodes is a map<suid,node>
        self.assertEqual(1, node.externalId)
        self.assertEqual(False, node.demographics_other)
        self.assertEqual(True, node.demographics_gender)
        self.assertEqual(1, node.x_birth)
        individual = node.individualHumans[0]
        self.assertEqual(1, individual.m_mc_weight)
        self.assertEqual(1, individual.suid.id)
        self.assertEqual(9588.48, individual.m_age)
        self.assertEqual(0, individual.m_gender)
        return


@unittest.skipIf(skip_tests, "Skipping old tests to focus on V6")
class TestReadVersionTwo(TestReadVersionOne):

    def test_dtkheader_2(self):
        header_2_keys = [
            'author',
            'bytecount',
            'chunkcount',
            'chunksizes',
            'compressed',
            'date',
            'tool',
            'version',
            'engine']
        self.check_keys_dtkeader(dft.DtkFileV2().header, header_2_keys)
        return

    def test_reading_file(self):
        dtk = dft.read(os.path.join(manifest.serialization_folder, "version2.dtk"))
        self.assertEqual("", dtk.author)
        self.assertEqual("", dtk.tool)
        self.assertEqual(True, dtk.compressed)
        self.assertEqual(dft.LZ4, dtk.compression)
        self.assertEqual(168431, dtk.byte_count)
        self.assertEqual(2, dtk.chunk_count)
        self.assertEqual(1584, dtk.chunk_sizes[0])
        self.assertEqual(166847, dtk.chunk_sizes[1])
        self.assertEqual(28, dtk.simulation.Run_Number)
        self.assertEqual(1001, dtk.simulation.individualHumanSuidGenerator.next_suid.id)
        self.assertEqual(2, dtk.simulation.sim_type)
        self.assertEqual(1, len(dtk.nodes))
        node = dtk.nodes[0]
        self.assertEqual(340461476, node.externalId)
        self.assertEqual(1000, len(node.individualHumans))
        human = node.individualHumans[0]
        self.assertEqual(0, human.cumulativeInfs)
        self.assertEqual(0, len(human.infections))
        self.assertEqual(0, human.infectiousness)
        self.assertEqual(7693.72, human.m_age)
        self.assertEqual(1, human.m_gender)
        self.assertEqual(False, human.m_is_infected)
        return

    def test_round_trip(self):

        source = dft.DtkFileV2()
        source.author = "dtkFileTests"
        source.compression = dft.SNAPPY if support.SNAPPY_SUPPORT else dft.LZ4
        simulation = support.SerialObject(
            {
                "simulation": {
                    "enable_spatial_output": False,
                    "Run_Number": 1,
                    "enable_property_output": False,
                    "infectionSuidGenerator": {
                        "next_suid": {"id": 1},
                        "rank": 0,
                        "numtasks": 1,
                    },
                    "__class__": "Simulation",
                    "campaignFilename": "campaign.json",
                    "nodes": [],
                    "loadbalance_filename": "",
                    "serializationMask": 3,
                    "individualHumanSuidGenerator": {
                        "next_suid": {"id": 1001},
                        "rank": 0,
                        "numtasks": 1,
                    },
                    "sim_type": 0,
                    "enable_default_report": True,
                    "enable_event_report": False,
                    "Ind_Sample_Rate": 1,
                    "demographic_tracking": False,
                }
            }
        )
        node = support.SerialObject(
            {
                "suid": {"id": 1},
                "node": {
                    "demographics_other": False,
                    "birth_rate_sinusoidal_forcing_phase": 0,
                    "sample_rate_20_plus": 0,
                    "max_sampling_cell_pop": 0,
                    "infectivity_boxcar_end_time": 0,
                    "sample_rate_18mo_4yr": 0,
                    "__class__": "Node",
                    "infectivity_boxcar_start_time": 0,
                    "demographics_gender": True,
                    "individualHumans": [
                        {
                            "migration_is_destination_new_home": False,
                            "home_node_id": {"id": 1},
                            "waiting_for_family_trip": False,
                            "migration_will_return": True,
                            "waypoints": [],
                            "family_migration_type": 0,
                            "Inf_Sample_Rate": 1,
                            "migration_outbound": True,
                            "m_mc_weight": 1,
                            "migration_time_until_trip": 0,
                            "StateChange": 0,
                            "suid": {"id": 1},
                            "leave_on_family_trip": False,
                            "interventions": {
                                "drugVaccineReducedTransmit": 1,
                                "drugVaccineReducedAcquire": 1,
                                "__class__": "InterventionsContainer",
                                "drugVaccineReducedMortality": 1,
                                "interventions": [],
                            },
                            "migration_destination": {"id": 0},
                            "__class__": "IndividualHuman",
                            "infectiousness": 0,
                            "migration_mod": 1,
                            "waypoints_trip_type": [],
                            "m_age": 9588.48,
                            "m_is_infected": False,
                            "m_daily_mortality_rate": 0,
                            "cumulativeInfs": 0,
                            "family_migration_time_at_destination": 0,
                            "family_migration_destination": {"id": 0},
                            "m_new_infection_state": 0,
                            "migration_time_at_destination": 0,
                            "family_migration_is_destination_new_home": False,
                            "migration_type": 0,
                            "max_waypoints": 0,
                            "pregnancy_timer": 0,
                            "family_migration_time_until_trip": 0,
                            "is_pregnant": False,
                            "susceptibility": {
                                "trandecayoffset": 0,
                                "age": 9588.48,
                                "__class__": "Susceptibility",
                                "acqdecayoffset": 0,
                                "mod_mortality": 1,
                                "mod_acquire": 1,
                                "mod_transmit": 1,
                                "mortdecayoffset": 0,
                            },
                            "is_on_family_trip": False,
                            "infections": [],
                            "above_poverty": 0,
                            "Properties": [],
                            "m_gender": 0,
                        }
                    ],
                    "serializationMask": 3,
                    "infectivity_sinusoidal_forcing_amplitude": 1,
                    "birth_rate_boxcar_start_time": 0,
                    "x_birth": 1,
                    "sample_rate_immune": 0,
                    "sample_rate_0_18mo": 0,
                    "population_scaling": 0,
                    "demographics_birth": False,
                    "suid": {"id": 1},
                    "birth_rate_boxcar_forcing_amplitude": 1,
                    "population_scaling_factor": 1,
                    "birth_rate_boxcar_end_time": 0,
                    "ind_sampling_type": 0,
                    "vital_birth_time_dependence": 0,
                    "externalId": 1,
                    "age_initialization_distribution_type": 1,
                    "infectivity_sinusoidal_forcing_phase": 0,
                    "immune_threshold_for_downsampling": 0,
                    "sample_rate_5_9": 0,
                    "home_individual_ids": [{"key": 1, "value": {"id": 1}}],
                    "sample_rate_birth": 0,
                    "birth_rate_sinusoidal_forcing_amplitude": 1,
                    "infectivity_boxcar_forcing_amplitude": 1,
                    "vital_birth": False,
                    "maternal_transmission": False,
                    "vital_birth_dependence": 1,
                    "infectivity_scaling": 0,
                    "sample_rate_10_14": 0,
                    "sample_rate_15_19": 0,
                },
            }
        )
        source.objects.append(simulation)
        source.objects.append(node)
        handle, filename = tempfile.mkstemp()
        os.close(handle)  # Do not need this, just the filename
        dft.write(source, filename)

        dest = dft.read(filename)
        os.remove(filename)
        self.assertEqual("dtkFileTests", dest.author)
        self.assertEqual(dft.SNAPPY if support.SNAPPY_SUPPORT else dft.LZ4, dest.compression)
        simulation = dest.simulation
        self.assertEqual(False, simulation.enable_spatial_output)
        self.assertEqual(1, simulation.Run_Number)
        self.assertEqual(1001, simulation.individualHumanSuidGenerator.next_suid.id)
        self.assertEqual(0, simulation.sim_type)
        self.assertEqual(True, simulation.enable_default_report)
        node = dest.nodes[0]
        self.assertEqual(1, node.externalId)
        self.assertEqual(False, node.demographics_other)
        self.assertEqual(True, node.demographics_gender)
        self.assertEqual(1, node.x_birth)
        individual = node.individualHumans[0]
        self.assertEqual(1, individual.m_mc_weight)
        self.assertEqual(1, individual.suid.id)
        self.assertEqual(9588.48, individual.m_age)
        self.assertEqual(0, individual.m_gender)
        return


@unittest.skipIf(skip_tests, "Skipping old tests to focus on V6")
class TestReadVersionThree(TestReadVersionTwo):

    def test_dtkheader_3(self):
        header_3_keys = [
            'author',
            'bytecount',
            'chunkcount',
            'chunksizes',
            'compressed',
            'date',
            'tool',
            'version',
            'engine']
        self.check_keys_dtkeader(dft.DtkFileV3().header, header_3_keys)
        return

    def test_reading_file(self):
        dtk = dft.read(os.path.join(manifest.serialization_folder, "version3.dtk"))
        self.assertEqual("", dtk.author)
        self.assertEqual("", dtk.tool)
        self.assertEqual(True, dtk.compressed)
        self.assertEqual(dft.LZ4, dtk.compression)
        self.assertEqual(177151, dtk.byte_count)
        self.assertEqual(2, dtk.chunk_count)
        self.assertEqual(1574, dtk.chunk_sizes[0])
        self.assertEqual(175577, dtk.chunk_sizes[1])
        self.assertEqual(27, dtk.simulation.Run_Number)
        self.assertEqual(1032, dtk.simulation.individualHumanSuidGenerator.next_suid.id)
        self.assertEqual(1, dtk.simulation.sim_type)
        self.assertEqual(1, len(dtk.nodes))
        node = dtk.nodes[0]
        self.assertEqual(340461476, node.externalId)
        self.assertEqual(1023, len(node.individualHumans))
        human = node.individualHumans[0]
        self.assertEqual(8, human.cumulativeInfs)
        self.assertEqual(5, len(human.infections))
        self.assertEqual(1, human.infectiousness)
        self.assertEqual(2457.41, human.m_age)
        self.assertEqual(1, human.m_gender)
        self.assertEqual(True, human.m_is_infected)
        return

    def test_round_trip(self):

        source = dft.DtkFileV3()
        source.author = "dtkFileTests"
        source.compression = dft.SNAPPY if support.SNAPPY_SUPPORT else dft.LZ4
        simulation = support.SerialObject(
            {
                "enable_spatial_output": False,
                "Run_Number": 1,
                "enable_property_output": False,
                "infectionSuidGenerator": {
                    "next_suid": {"id": 1},
                    "rank": 0,
                    "numtasks": 1,
                },
                "__class__": "Simulation",
                "campaignFilename": "campaign.json",
                "nodes": [],
                "loadbalance_filename": "",
                "serializationMask": 3,
                "individualHumanSuidGenerator": {
                    "next_suid": {"id": 1001},
                    "rank": 0,
                    "numtasks": 1,
                },
                "sim_type": 0,
                "enable_default_report": True,
                "enable_event_report": False,
                "Ind_Sample_Rate": 1,
                "demographic_tracking": False,
            }
        )
        node = support.SerialObject(
            {
                "demographics_other": False,
                "birth_rate_sinusoidal_forcing_phase": 0,
                "sample_rate_20_plus": 0,
                "max_sampling_cell_pop": 0,
                "infectivity_boxcar_end_time": 0,
                "sample_rate_18mo_4yr": 0,
                "__class__": "Node",
                "infectivity_boxcar_start_time": 0,
                "demographics_gender": True,
                "individualHumans": [
                    {
                        "migration_is_destination_new_home": False,
                        "home_node_id": {"id": 1},
                        "waiting_for_family_trip": False,
                        "migration_will_return": True,
                        "waypoints": [],
                        "family_migration_type": 0,
                        "Inf_Sample_Rate": 1,
                        "migration_outbound": True,
                        "m_mc_weight": 1,
                        "migration_time_until_trip": 0,
                        "StateChange": 0,
                        "suid": {"id": 1},
                        "leave_on_family_trip": False,
                        "interventions": {
                            "drugVaccineReducedTransmit": 1,
                            "drugVaccineReducedAcquire": 1,
                            "__class__": "InterventionsContainer",
                            "drugVaccineReducedMortality": 1,
                            "interventions": [],
                        },
                        "migration_destination": {"id": 0},
                        "__class__": "IndividualHuman",
                        "infectiousness": 0,
                        "migration_mod": 1,
                        "waypoints_trip_type": [],
                        "m_age": 9588.48,
                        "m_is_infected": False,
                        "m_daily_mortality_rate": 0,
                        "cumulativeInfs": 0,
                        "family_migration_time_at_destination": 0,
                        "family_migration_destination": {"id": 0},
                        "m_new_infection_state": 0,
                        "migration_time_at_destination": 0,
                        "family_migration_is_destination_new_home": False,
                        "migration_type": 0,
                        "max_waypoints": 0,
                        "pregnancy_timer": 0,
                        "family_migration_time_until_trip": 0,
                        "is_pregnant": False,
                        "susceptibility": {
                            "trandecayoffset": 0,
                            "age": 9588.48,
                            "__class__": "Susceptibility",
                            "acqdecayoffset": 0,
                            "mod_mortality": 1,
                            "mod_acquire": 1,
                            "mod_transmit": 1,
                            "mortdecayoffset": 0,
                        },
                        "is_on_family_trip": False,
                        "infections": [],
                        "above_poverty": 0,
                        "Properties": [],
                        "m_gender": 0,
                    }
                ],
                "serializationMask": 3,
                "infectivity_sinusoidal_forcing_amplitude": 1,
                "birth_rate_boxcar_start_time": 0,
                "x_birth": 1,
                "sample_rate_immune": 0,
                "sample_rate_0_18mo": 0,
                "population_scaling": 0,
                "demographics_birth": False,
                "suid": {"id": 1},
                "birth_rate_boxcar_forcing_amplitude": 1,
                "population_scaling_factor": 1,
                "birth_rate_boxcar_end_time": 0,
                "ind_sampling_type": 0,
                "vital_birth_time_dependence": 0,
                "externalId": 1,
                "age_initialization_distribution_type": 1,
                "infectivity_sinusoidal_forcing_phase": 0,
                "immune_threshold_for_downsampling": 0,
                "sample_rate_5_9": 0,
                "home_individual_ids": [{"key": 1, "value": {"id": 1}}],
                "sample_rate_birth": 0,
                "birth_rate_sinusoidal_forcing_amplitude": 1,
                "infectivity_boxcar_forcing_amplitude": 1,
                "vital_birth": False,
                "maternal_transmission": False,
                "vital_birth_dependence": 1,
                "infectivity_scaling": 0,
                "sample_rate_10_14": 0,
                "sample_rate_15_19": 0,
            }
        )
        source.objects.append(simulation)
        source.objects.append(node)
        handle, filename = tempfile.mkstemp()
        os.close(handle)  # Do not need this, just the filename
        dft.write(source, filename)

        dest = dft.read(filename)
        os.remove(filename)
        self.assertEqual("dtkFileTests", dest.author)
        self.assertEqual(dft.SNAPPY if support.SNAPPY_SUPPORT else dft.LZ4, dest.compression)
        simulation = dest.simulation
        self.assertEqual(False, simulation.enable_spatial_output)
        self.assertEqual(1, simulation.Run_Number)
        self.assertEqual(1001, simulation.individualHumanSuidGenerator.next_suid.id)
        self.assertEqual(0, simulation.sim_type)
        self.assertEqual(True, simulation.enable_default_report)
        node = dest.nodes[0]
        self.assertEqual(1, node.externalId)
        self.assertEqual(False, node.demographics_other)
        self.assertEqual(True, node.demographics_gender)
        self.assertEqual(1, node.x_birth)
        individual = node.individualHumans[0]
        self.assertEqual(1, individual.m_mc_weight)
        self.assertEqual(1, individual.suid.id)
        self.assertEqual(9588.48, individual.m_age)
        self.assertEqual(0, individual.m_gender)
        return


@unittest.skipIf(skip_tests, "Skipping old tests to focus on V6")
class TestReadVersionFour(TestReadVersionThree):

    def test_dtkheader_4(self):
        header_4_keys = [
            'author',
            'bytecount',
            'chunkcount',
            'chunksizes',
            'compressed',
            'date',
            'tool',
            'version',
            'engine']
        self.check_keys_dtkeader(dft.DtkFileV4().header, header_4_keys)
        return

    def test_reading_file(self):
        dtk = dft.read(os.path.join(manifest.serialization_folder, "version4.dtk"))
        self.assertEqual("IDM", dtk.author)
        self.assertEqual("DTK", dtk.tool)
        self.assertEqual(True, dtk.compressed)
        self.assertEqual(dft.LZ4, dtk.compression)
        self.assertEqual(625105, dtk.byte_count)
        self.assertEqual(5, dtk.chunk_count)
        self.assertEqual(384, dtk.chunk_sizes[0])
        self.assertEqual(164210, dtk.chunk_sizes[1])
        self.assertEqual(152439, dtk.chunk_sizes[2])
        self.assertEqual(156570, dtk.chunk_sizes[3])
        self.assertEqual(151502, dtk.chunk_sizes[4])
        self.assertEqual(1, dtk.simulation.Run_Number)
        self.assertEqual(
            10001, dtk.simulation.individualHumanSuidGenerator.next_suid.id
        )
        self.assertEqual(0, dtk.simulation.sim_type)
        self.assertEqual(4, len(dtk.nodes))
        node = dtk.nodes[0]
        self.assertEqual(1, node.externalId)
        self.assertEqual(2500, len(node.individualHumans))
        human = node.individualHumans[0]
        self.assertEqual(1, human.cumulativeInfs)
        self.assertEqual(0, len(human.infections))
        self.assertEqual(0, human.infectiousness)
        self.assertEqual(9598.48, human.m_age)
        self.assertEqual(0, human.m_gender)
        self.assertEqual(False, human.m_is_infected)
        return

    def round_trip(self, source):
        source.author = "dtkFileTests"
        source.compression = dft.SNAPPY if support.SNAPPY_SUPPORT else dft.LZ4
        simulation = support.SerialObject(
            {
                "enable_spatial_output": False,
                "Run_Number": 42,
                "enable_property_output": False,
                "infectionSuidGenerator": {
                    "next_suid": {"id": 1},
                    "rank": 0,
                    "numtasks": 1,
                },
                "__class__": "Simulation",
                "campaignFilename": "campaign.json",
                "nodes": [],
                "loadbalance_filename": "",
                "serializationMask": 3,
                "individualHumanSuidGenerator": {
                    "next_suid": {"id": 1001},
                    "rank": 0,
                    "numtasks": 1,
                },
                "sim_type": 1,
                "enable_default_report": True,
                "enable_event_report": False,
                "Ind_Sample_Rate": 1,
                "demographic_tracking": False,
            }
        )
        node = support.SerialObject(
            {
                "demographics_other": False,
                "birth_rate_sinusoidal_forcing_phase": 0,
                "sample_rate_20_plus": 0,
                "max_sampling_cell_pop": 0,
                "infectivity_boxcar_end_time": 0,
                "sample_rate_18mo_4yr": 0,
                "__class__": "Node",
                "infectivity_boxcar_start_time": 0,
                "demographics_gender": True,
                "individualHumans": [
                    {
                        "migration_is_destination_new_home": False,
                        "home_node_id": {"id": 1},
                        "waiting_for_family_trip": False,
                        "migration_will_return": True,
                        "waypoints": [],
                        "family_migration_type": 0,
                        "Inf_Sample_Rate": 1,
                        "migration_outbound": True,
                        "m_mc_weight": 11,
                        "migration_time_until_trip": 0,
                        "StateChange": 0,
                        "suid": {"id": 1},
                        "leave_on_family_trip": False,
                        "interventions": {
                            "drugVaccineReducedTransmit": 1,
                            "drugVaccineReducedAcquire": 1,
                            "__class__": "InterventionsContainer",
                            "drugVaccineReducedMortality": 1,
                            "interventions": [],
                        },
                        "migration_destination": {"id": 0},
                        "__class__": "IndividualHuman",
                        "infectiousness": 0,
                        "migration_mod": 1,
                        "waypoints_trip_type": [],
                        "m_age": 9588.48,
                        "m_is_infected": False,
                        "m_daily_mortality_rate": 0,
                        "cumulativeInfs": 0,
                        "family_migration_time_at_destination": 0,
                        "family_migration_destination": {"id": 0},
                        "m_new_infection_state": 0,
                        "migration_time_at_destination": 0,
                        "family_migration_is_destination_new_home": False,
                        "migration_type": 0,
                        "max_waypoints": 0,
                        "pregnancy_timer": 0,
                        "family_migration_time_until_trip": 0,
                        "is_pregnant": False,
                        "susceptibility": {
                            "trandecayoffset": 0,
                            "age": 9588.48,
                            "__class__": "Susceptibility",
                            "acqdecayoffset": 0,
                            "mod_mortality": 1,
                            "mod_acquire": 1,
                            "mod_transmit": 1,
                            "mortdecayoffset": 0,
                        },
                        "is_on_family_trip": False,
                        "infections": [],
                        "above_poverty": 0,
                        "Properties": [],
                        "m_gender": 0,
                    }
                ],
                "serializationMask": 3,
                "infectivity_sinusoidal_forcing_amplitude": 1,
                "birth_rate_boxcar_start_time": 0,
                "x_birth": 2.718281828,
                "sample_rate_immune": 0,
                "sample_rate_0_18mo": 0,
                "population_scaling": 0,
                "demographics_birth": False,
                "suid": {"id": 1},
                "birth_rate_boxcar_forcing_amplitude": 1,
                "population_scaling_factor": 1,
                "birth_rate_boxcar_end_time": 0,
                "ind_sampling_type": 0,
                "vital_birth_time_dependence": 0,
                "externalId": 314159265,
                "age_initialization_distribution_type": 1,
                "infectivity_sinusoidal_forcing_phase": 0,
                "immune_threshold_for_downsampling": 0,
                "sample_rate_5_9": 0,
                "home_individual_ids": [{"key": 1, "value": {"id": 1}}],
                "sample_rate_birth": 0,
                "birth_rate_sinusoidal_forcing_amplitude": 1,
                "infectivity_boxcar_forcing_amplitude": 1,
                "vital_birth": False,
                "maternal_transmission": False,
                "vital_birth_dependence": 1,
                "infectivity_scaling": 0,
                "sample_rate_10_14": 0,
                "sample_rate_15_19": 0,
            }
        )
        source.objects.append(simulation)
        source.objects.append(node)
        handle, filename = tempfile.mkstemp()
        os.close(handle)  # Do not need this, just the filename
        dft.write(source, filename)

        dest = dft.read(filename)
        os.remove(filename)
        self.assertEqual("dtkFileTests", dest.author)
        self.assertEqual(dft.SNAPPY if support.SNAPPY_SUPPORT else dft.LZ4, dest.compression)
        simulation = dest.simulation
        self.assertEqual(False, simulation.enable_spatial_output)
        self.assertEqual(42, simulation.Run_Number)
        self.assertEqual(1001, simulation.individualHumanSuidGenerator.next_suid.id)
        self.assertEqual(1, simulation.sim_type)
        self.assertEqual(True, simulation.enable_default_report)
        node = dest.nodes[0]
        self.assertEqual(314159265, node.externalId)
        self.assertEqual(False, node.demographics_other)
        self.assertEqual(True, node.demographics_gender)
        self.assertEqual(2.718281828, node.x_birth)
        individual = node.individualHumans[0]
        self.assertEqual(11, individual.m_mc_weight)
        self.assertEqual(1, individual.suid.id)
        self.assertEqual(9588.48, individual.m_age)
        self.assertEqual(0, individual.m_gender)
        return

    def test_round_trip(self):
        source = dft.DtkFileV4()
        self.round_trip(source)
        return


@unittest.skipIf(skip_tests, "Skipping old tests to focus on V6")
class TestReadWrite(unittest.TestCase):
    def NullPtr(self, source):
        source.compression = dft.SNAPPY if support.SNAPPY_SUPPORT else dft.LZ4
        simulation = support.SerialObject(
            {
                "__class__": "Simulation",
                "infectionSuidGenerator": {
                    "next_suid": {"id": 1},
                    "rank": 0,
                    "numtasks": 1,
                },
                "nodes": [],
                "sim_type": 1,
                "m_simConfigObj": support.NullPtr()
            }
        )
        node = support.SerialObject(
            {
                "__class__": "Node",
                "individualHumans": [
                    {
                        "suid": {"id": 1},
                        "interventions": support.NullPtr()
                    }
                ]
            }
        )
        source.objects.append(simulation)
        source.objects.append(node)
        handle, filename = tempfile.mkstemp()
        os.close(handle)  # Do not need this, just the filename
        dft.write(source, filename)

        dest = dft.read(filename)
        os.remove(filename)
        self.assertEqual(dft.SNAPPY if support.SNAPPY_SUPPORT else dft.LZ4, dest.compression)
        self.assertEqual(dest.simulation.m_simConfigObj, support.NullPtr())
        individual = dest.nodes[0].individualHumans[0]
        self.assertEqual(individual.interventions, support.NullPtr())
        return

    def test_NullPtr(self):
        source = dft.DtkFileV4()
        self.NullPtr(source)
        return


@unittest.skipIf(skip_tests, "Skipping old tests to focus on V6")
class TestReadingSadPath(unittest.TestCase):
    def test_reading_wrong_magic_number(self):
        with self.assertRaises(UserWarning):
            dft.read(os.path.join(manifest.serialization_folder, "bad-magic.dtk"))
        return

    def test_reading_negative_header_size(self):
        with self.assertRaises(UserWarning):
            dft.read(os.path.join(manifest.serialization_folder, "neg-hdr-size.dtk"))
        return

    def test_reading_zero_header_size(self):
        with self.assertRaises(UserWarning):
            dft.read(os.path.join(manifest.serialization_folder, "zero-hdr-size.dtk"))
        return

    def test_reading_invalid_header(self):
        with self.assertRaises(UserWarning):
            dft.read(os.path.join(manifest.serialization_folder, "bad-header.dtk"))
        return

    # Missing version is considered version 1. Is this okay?
    #    def test_reading_missing_version(self):
    #        with self.assertRaises(UserWarning):
    #            dtk_file = dft.read(os.path.join(WORKING_DIRECTORY, "data", "serialization", "missing-version.dtk"))
    #        return

    def test_reading_negative_version(self):
        with self.assertRaises(UserWarning):
            dft.read(os.path.join(manifest.serialization_folder, "neg-version.dtk"))
        return

    def test_reading_zero_version(self):
        with self.assertRaises(UserWarning):
            dft.read(os.path.join(manifest.serialization_folder, "zero-version.dtk"))
        return

    def test_reading_unknown_version(self):
        with self.assertRaises(UserWarning):
            dft.read(os.path.join(manifest.serialization_folder, "future-version.dtk"))
        return

    def test_reading_negative_chunk_size(self):
        with self.assertRaises(UserWarning):
            dft.read(os.path.join(manifest.serialization_folder, "neg-chunk-size.dtk"))
        return

    def test_reading_zero_chunk_size(self):
        with self.assertRaises(UserWarning):
            dft.read(os.path.join(manifest.serialization_folder, "zero-chunk-size.dtk"))
        return

    def test_reading_truncated_file(self):
        with self.assertRaises(UserWarning):
            dft.read(os.path.join(manifest.serialization_folder, "truncated.dtk"))  # simulation and one node (truncated)
        return

    # Compression/data mismatch (false/LZ4)
    def test_engine_data_mismatch_a(self):
        with self.assertRaises(UserWarning):
            dtk_file = dft.read(os.path.join(manifest.serialization_folder, "none-lz4.dtk"))  # hdr (NONE) vs. actual (LZ4)
            # Accessing the simulation field raises the exception
            print(dtk_file.simulation.individualHumanSuidGenerator.next_suid.id)
        return

    # Compression/data mismatch (false/SNAPPY)
    def test_engine_data_mismatch_b(self):
        with self.assertRaises(UserWarning):
            dtk_file = dft.read(os.path.join(manifest.serialization_folder, "none-snappy.dtk"))  # hdr (NONE) vs. actual (SNAPPY)
            # Accessing the simulation field raises the exception
            print(dtk_file.simulation.individualHumanSuidGenerator.next_suid.id)
        return

    # Compression/data mismatch (true+LZ4/NONE)
    def test_engine_data_mismatch_c(self):
        with self.assertRaises(UserWarning):
            dtk_file = dft.read(os.path.join(manifest.serialization_folder, "lz4-none.dtk"))  # hdr (LZ4) vs. actual (NONE)
            # Accessing the simulation field raises the exception
            print(dtk_file.simulation.individualHumanSuidGenerator.next_suid.id)
        return

    # Compression/data mismatch (true+LZ4/SNAPPY)
    def test_engine_data_mismatch_d(self):
        with self.assertRaises(UserWarning):
            dtk_file = dft.read(os.path.join(manifest.serialization_folder, "lz4-snappy.dtk"))  # hdr (LZ4) vs. actual (SNAPPY)
            # Accessing the simulation field raises the exception
            print(dtk_file.simulation.individualHumanSuidGenerator.next_suid.id)
        return

    # Compression/data mismatch (true+SNAPPY/NONE)
    def test_engine_data_mismatch_e(self):
        with self.assertRaises(UserWarning):
            dtk_file = dft.read(os.path.join(manifest.serialization_folder, "snappy-none.dtk"))  # hdr (SNAPPY) vs. actual (NONE)
            # Accessing the simulation field raises the exception
            print(dtk_file.simulation.individualHumanSuidGenerator.next_suid.id)
        return

    # Compression/data mismatch (true+SNAPPY/LZ4)
    def test_engine_data_mismatch_f(self):
        with self.assertRaises(UserWarning):
            dtk_file = dft.read(os.path.join(manifest.serialization_folder, "snappy-lz4.dtk"))  # hdr (SNAPPY) vs. actual (LZ4)
            # Accessing the simulation field raises the exception
            print(dtk_file.simulation.individualHumanSuidGenerator.next_suid.id)
        return

    # Corrupted simulation chunk (uncompressed)
    def test_bad_sim_chunk_none(self):
        with self.assertRaises(UserWarning):
            dtk_file = dft.read(os.path.join(manifest.serialization_folder, "bad-sim-none.dtk"))
            # Accessing the simulation field raises the exception
            print(dtk_file.simulation.individualHumanSuidGenerator.next_suid.id)
        return

    # Corrupted simulation chunk (lz4)
    def test_bad_sim_chunk_lz4(self):
        with self.assertRaises(UserWarning):
            dtk_file = dft.read(os.path.join(manifest.serialization_folder, "bad-sim-lz4.dtk"))
            # Accessing the simulation field raises the exception
            print(dtk_file.simulation.individualHumanSuidGenerator.next_suid.id)
        return

    # Corrupted simulation chunk (snappy)
    def test_bad_sim_chunk_snappy(self):
        with self.assertRaises(UserWarning):
            dtk_file = dft.read(os.path.join(manifest.serialization_folder, "bad-sim-snappy.dtk"))
            # Accessing the simulation field raises the exception
            print(dtk_file.simulation.individualHumanSuidGenerator.next_suid.id)
        return

    # Corrupted chunk (uncompressed)
    def test_bad_chunk_none(self):
        with self.assertRaises(UserWarning):
            dtk_file = dft.read(os.path.join(manifest.serialization_folder, "bad-chunk-none.dtk"))
            # Accessing the node raises the exception
            print(dtk_file.nodes[0].externalId)
        return

    # Corrupted chunk (LZ4)
    def test_bad_chunk_lz4(self):
        with self.assertRaises(UserWarning):
            dtk_file = dft.read(os.path.join(manifest.serialization_folder, "bad-chunk-lz4.dtk"))
            # Accessing the node raises the exception
            print(dtk_file.nodes[0].externalId)
        return

    # Corrupted chunk (SNAPPY)
    def test_bad_chunk_snappy(self):
        with self.assertRaises(UserWarning):
            dtk_file = dft.read(os.path.join(manifest.serialization_folder, "bad-chunk-snappy.dtk"))
            # Accessing the node raises the exception
            print(dtk_file.nodes[0].externalId)
        return


@unittest.skipIf(skip_tests, "Skipping old tests to focus on V6")
class TestRegressions(unittest.TestCase):

    # https://github.com/InstituteforDiseaseModeling/DtkTrunk/issues/1268
    def test_1268(self):
        version_two = dft.read(os.path.join(manifest.serialization_folder, "version2.dtk"))
        simulation = version_two.simulation
        self.assertTrue("nodes" not in simulation)
        version_three = dft.read(os.path.join(manifest.serialization_folder, "version3.dtk"))
        simulation = version_three.simulation
        self.assertTrue("nodes" not in simulation)
        version_four = dft.read(os.path.join(manifest.serialization_folder, "version4.dtk"))
        simulation = version_four.simulation
        self.assertTrue("nodes" not in simulation)

        return


@unittest.skipIf(skip_tests, "Skipping old tests to focus on V6")
class TestReadVersion5(TestReadVersionFour, TestReadWrite):

    def test_dtkheader_5(self):
        header_5_keys = [
            'author',
            'bytecount',
            'chunkcount',
            'chunksizes',
            'compressed',
            'date',
            'tool',
            'version',
            'engine',
            'emod_info']
        self.check_keys_dtkeader(dft.DtkFileV5().header, header_5_keys)
        return

    def test_round_trip(self):
        # check if header version 5 passes version 4 test
        source = dft.DtkFileV5()
        self.round_trip(source)
        return

    def test_NullPtr(self):
        # check if header version 5 passes version 4 test
        source = dft.DtkFileV5()
        self.NullPtr(source)
        return

    def test_header5(self):
        # check default version 5 header, skip date
        reference_header5 = {
            'author': "unknown",
            'bytecount': 0,
            'chunkcount': 0,
            'chunksizes': [],
            'compressed': True,
            # 'date': None,  # date with seconds, might have changed at point of testing
            'engine': "LZ4",
            'tool': "dtkFileTools.py",
            'version': 5,
            'emod_info': {
                'emod_sccs_date': "Mon Jan 1 00:00:00 1970",
                'emod_major_version': 0,
                'emod_minor_version': 0,
                'emod_revision_number': 0,
                'ser_pop_major_version': 0,
                'ser_pop_minor_version': 0,
                'ser_pop_patch_version': 0,
                'emod_build_date': "Mon Jan 1 00:00:00 1970",
                'emod_builder_name': "",
                'emod_sccs_branch': 0
            }
        }
        header5 = dft.DtkFileV5().header
        time.strptime(header5['date'])  # throws ValueError if date format is wrong
        del header5["date"]
        self.assertEqual(header5.version, 5)
        self.assertDictEqual(header5, reference_header5)

        header5_emod_info = dft.DtkFileV5().header['emod_info']
        time.strptime(header5_emod_info.get('emod_sccs_date'))
        return

    def test_write_read_header5(self):
        # create a very basic sp file with header version 5, save it to disk, load it, and check header and contents
        header5_extension = {
            'emod_info': {
                'version': 5,
                'emod_major_version': 2,
                'emod_minor_version': 3,
                'emod_revision_number': 4,
                'ser_pop_major_version': 5,
                'ser_pop_minor_version': 6,
                'ser_pop_patch_version': 7,
                'emod_build_date': "Fri Oct 28 00:00:00 1955",
                'emod_builder_name': "",
                'emod_sccs_branch': 10,
                'emod_sccs_date': "Sun Jun 23 00:00:00 1912"
            }
        }

        reference_header5 = dft.DtkHeader()
        reference_header5.update(header5_extension)
        dummy_simulation = {"dummy_class": "Simulation", "nodes": []}
        dummy_node_1 = {"node_1": "Node_1", "individualHumans": []}
        dummy_node_2 = {"node_2": "Node_2", "individualHumans": []}

        source = dft.DtkFileV5(header=reference_header5)
        simulation = support.SerialObject(dummy_simulation)
        node_1 = support.SerialObject(dummy_node_1)
        node_2 = support.SerialObject(dummy_node_2)
        source.objects.append(simulation)
        source.objects.append(node_1)
        source.objects.append(node_2)
        handle, filename = tempfile.mkstemp()
        os.close(handle)
        dft.write(source, filename)

        dest = dft.read(filename)
        os.remove(filename)

        for key in reference_header5:
            self.assertEqual(dest.header[key], reference_header5[key])

        self.assertEqual(dest.simulation.dummy_class, "Simulation")
        self.assertEqual(dest.nodes[0], dummy_node_1)
        self.assertEqual(dest.nodes[0].individualHumans, [])
        self.assertEqual(dest.nodes[1], dummy_node_2)
        self.assertEqual(dest.nodes[1].individualHumans, [])

        test_emod_build_date = time.strptime(dest.header['emod_info']['emod_build_date'])
        self.assertEqual(test_emod_build_date, time.strptime(header5_extension['emod_info']["emod_build_date"]))

        test_emod_sccs_date = time.strptime(dest.header['emod_info']['emod_sccs_date'])
        self.assertEqual(test_emod_sccs_date, time.strptime(header5_extension['emod_info']["emod_sccs_date"]))



sim_keys_to_remove = [
    'campaignFilename',
    'custom_reports_filename',
    'm_RngFactory',
    'rng',
    'demographic_tracking',
    'enable_spatial_output',
    'enable_property_output',
    'enable_default_report',
    'enable_event_report',
    'enable_node_event_report',
    'enable_coordinator_event_report',
    'enable_surveillance_event_report',
    'loadbalance_filename',
    'm_ParasiteCohortSuidGenerator',
    'm_VectorBiteSuidGenerator'
]

human_keys_to_remove = [
    'is_pregnant',
    'pregnancy_timer',
    'm_mc_weight',
    'm_daily_mortality_rate', 
    'susceptibility',
    'interventions',
    'Inf_Sample_Rate',
    'cumulativeInfs',
    'm_new_infection_state',
    'StateChange',
    'migration_mod',
    'migration_type',
    'migration_destination',
    'migration_time_until_trip',
    'migration_time_at_destination',
    'migration_is_destination_new_home',
    'migration_will_return',
    'migration_outbound',
    'max_waypoints',
    'waypoints',
    'waypoints_trip_type',
    'home_node_id',
    'Properties',
    'waiting_for_family_trip',
    'leave_on_family_trip',
    'is_on_family_trip',
    'family_migration_type',
    'family_migration_time_until_trip',
    'family_migration_time_at_destination',
    'family_migration_is_destination_new_home',
    'family_migration_destination',
    'm_newly_symptomatic',
    'm_strain_exposure',
    'm_total_exposure',
    'm_male_gametocytes',
    'm_female_gametocytes',
    'm_female_gametocytes_by_strain',
    'm_gametocytes_detected',
    'm_clinical_symptoms_new',
    'm_clinical_symptoms_continuing',
    'm_initial_infected_hepatocytes',
    'm_DiagnosticMeasurement'
]

class TestReadVersion6(unittest.TestCase):

    def xtest_reduce_dtk_file(self):
        input_file = os.path.join(manifest.serialization_folder, "state-00004.dtk")
        pop = SerPop.SerializedPopulation(input_file)

        print(pop.dtk.simulation.keys())
        for key in sim_keys_to_remove:
            del pop.dtk.simulation[key]
        print(pop.dtk.simulation.keys())

        for node in pop.nodes:
            for human in node.individualHumans:
                for key in human_keys_to_remove:
                    if key in human:
                        del human[key]
                if node.suid.id == 1:
                    human.m_age = 1111
                elif node.suid.id == 2:
                    human.m_age = 2222
                else:
                    human.m_age = 3333

        output_file = os.path.join(manifest.serialization_folder, "state-00004-reduced.dtk")
        pop.write(output_file)
        return

    def check_humans_in_nodes(self,
                              pop,
                              human_ids_node_1,
                              human_ids_node_2,
                              human_ids_node_3, 
                              age_node_1,
                              age_node_2,
                              age_node_3):
        prev_human_suid = -1
        for index, node in enumerate(pop.nodes):
            if index == 0:
                self.assertEqual(1, node.suid.id)
                self.assertEqual(len(human_ids_node_1), len(node.individualHumans))
            elif index == 1:
                self.assertEqual(2, node.suid.id)
                self.assertEqual(len(human_ids_node_2), len(node.individualHumans))
            elif index == 2:
                self.assertEqual(3, node.suid.id)
                self.assertEqual(len(human_ids_node_3), len(node.individualHumans))
            for human in node.individualHumans:
                # verify that human suids are changing and correct per node
                if prev_human_suid != -1:
                    self.assertTrue( (human.suid.id != prev_human_suid) and (prev_human_suid != -1))
                prev_human_suid = human.suid.id
                if node.suid.id == 1:
                    self.assertIn(human.suid.id, human_ids_node_1)
                    self.assertEqual(age_node_1, human.m_age)
                elif node.suid.id == 2:
                    self.assertIn(human.suid.id, human_ids_node_2)
                    self.assertEqual(age_node_2, human.m_age)
                else:
                    self.assertIn(human.suid.id, human_ids_node_3)
                    self.assertEqual(age_node_3, human.m_age)
        return

    def test_read_write(self):
        input_file = os.path.join(manifest.serialization_folder, "state-00004-reduced.dtk")
        pop = SerPop.SerializedPopulation(input_file)

        # -------------------------------------------------
        # --- Verify that you can read the simulation data
        # -------------------------------------------------
        self.assertEqual( 2, pop.dtk.simulation.sim_type )
        self.assertEqual( 300, pop.dtk.simulation.falciparumPfEMP1Vars )
        self.assertEqual( 3, len(pop.nodes) )
        self.assertEqual( 0, len(pop.dtk.simulation.nodes)) # zero because nodes are stored separately

        pop.dtk.simulation.falciparumPfEMP1Vars = 777
        self.assertEqual( 777, pop.dtk.simulation.falciparumPfEMP1Vars )

        # ---------------------------------------------------------
        # --- Verify that you can get a node without the iterator
        # --- and be able to access it as expected.
        # ---------------------------------------------------------
        node_1 = pop.nodes[0]
        self.assertEqual(1, node_1.suid.id)
        self.assertEqual(1, node_1.externalId)
        self.assertEqual(1.0, node_1.mosquito_weight)
        self.assertEqual(3, len(node_1.m_vectorpopulations))
        self.assertEqual(5, len(node_1.individualHumans))

        node_1.mosquito_weight = 1.1
        self.assertEqual(1.1, node_1.mosquito_weight)
        node_1.store()
        node_1 = None
        gc.collect()

        node_2 = pop.nodes[1]
        self.assertEqual(2, node_2.suid.id)
        self.assertEqual(2, node_2.externalId)
        self.assertEqual(1.0, node_2.mosquito_weight)
        self.assertEqual(3, len(node_2.m_vectorpopulations))
        self.assertEqual(2, len(node_2.individualHumans))

        node_2.mosquito_weight = 2.2
        self.assertEqual(2.2, node_2.mosquito_weight)
        node_2.store()
        node_2 = None
        gc.collect()

        node_3 = pop.nodes[2]
        self.assertEqual(3, node_3.suid.id)
        self.assertEqual(3, node_3.externalId)
        self.assertEqual(1.0, node_3.mosquito_weight)
        self.assertEqual(3, len(node_3.m_vectorpopulations))
        self.assertEqual(7, len(node_3.individualHumans))
        node_3.mosquito_weight = 3.3
        self.assertEqual(3.3, node_3.mosquito_weight)
        node_3.store()
        node_3 = None
        gc.collect()

        # --------------------------------------------------------------
        # --- Verify that you can iterate over the nodes and the humans
        # --------------------------------------------------------------
        node_1_human_suids = [ 2, 5, 8, 11, 14 ]
        node_2_human_suids = [ 3, 6 ]
        node_3_human_suids = [ 4, 7, 10, 13, 16, 19, 22 ]
        self.check_humans_in_nodes(pop,
                                   node_1_human_suids,
                                   node_2_human_suids,
                                   node_3_human_suids,
                                   age_node_1=1111,
                                   age_node_2=2222,
                                   age_node_3=3333 )
        for index, node in enumerate(pop.nodes):
            if index == 0:
                self.assertEqual(1, node.suid.id)
                self.assertEqual(1.1, node.mosquito_weight)
            elif index == 1:
                self.assertEqual(2, node.suid.id)
                self.assertEqual(2.2, node.mosquito_weight)
            elif index == 2:
                self.assertEqual(3, node.suid.id)
                self.assertEqual(3.3, node.mosquito_weight)

        # --------------------------------------------------------
        # --- Update ages then verify they have been updated
        # --------------------------------------------------------
        for node in pop.nodes:
            for human in node.individualHumans:
                if node.suid.id == 1:
                    self.assertEqual(1111, human.m_age)
                    human.m_age += 11
                    self.assertEqual(1122, human.m_age)
                elif node.suid.id == 2:
                    self.assertEqual(2222, human.m_age)
                    human.m_age += 22
                    self.assertEqual(2244, human.m_age)
                else:
                    self.assertEqual(3333, human.m_age)
                    human.m_age += 33
                    self.assertEqual(3366, human.m_age)
        
        # verify ages have been updated
        self.check_humans_in_nodes(pop,
                                   node_1_human_suids,
                                   node_2_human_suids,
                                   node_3_human_suids,
                                   age_node_1=1122,
                                   age_node_2=2244,
                                   age_node_3=3366 )

        # -------------------------------------------------------------------
        # --- Verify that we can save the file, read it and get the new ages.
        # -------------------------------------------------------------------
        output_file = os.path.join(manifest.output_folder, "TestReadVersion6.test_read_write.state-00004.dtk")
        pop.write(output_file)
        pop = None
        gc.collect()
        
        self.assertTrue( os.path.exists(output_file), f"Expected output file to exist: {output_file}" )

        pop_modified = SerPop.SerializedPopulation(output_file)
        self.assertEqual( 2, pop_modified.dtk.simulation.sim_type )
        self.assertEqual( 777, pop_modified.dtk.simulation.falciparumPfEMP1Vars )
        self.assertEqual( 3, len(pop_modified.nodes) )
        self.check_humans_in_nodes(pop_modified,
                                   node_1_human_suids,
                                   node_2_human_suids,
                                   node_3_human_suids,
                                   age_node_1=1122,
                                   age_node_2=2244,
                                   age_node_3=3366 )
        for node in pop_modified.nodes:
            if node.suid.id == 1:
                self.assertEqual(1.1, node.mosquito_weight)
            elif node.suid.id == 2:
                self.assertEqual(2.2, node.mosquito_weight)
            else:
                self.assertEqual(3.3, node.mosquito_weight)
        pop_modified = None
        gc.collect()
        #os.remove(output_file)

    def test_manipulating_human_list(self):
        input_file = os.path.join(manifest.serialization_folder, "state-00004-reduced.dtk")
        pop = SerPop.SerializedPopulation(input_file)

        self.assertEqual(3, len(pop.nodes))

        # --------------------------------------------------------------
        # --- Replace humans with a new list
        #  --- (just use the humans that were already in the list.)
        # --------------------------------------------------------------
        node_1 = pop.nodes[0]
        self.assertEqual(1, node_1.suid.id)
        self.assertEqual(5, len(node_1.individualHumans))
        human_2 = node_1.individualHumans[0] # move to node_3
        human_5 = node_1.individualHumans[1]
        human_8 = node_1.individualHumans[2] # move to node_3
        human_11 = node_1.individualHumans[3]
        human_14 = node_1.individualHumans[4] # move to node_3
        human_list = []
        human_list.append( human_5 )
        human_list.append( human_11 )
        node_1.individualHumans = human_list
        self.assertEqual(2, len(node_1.individualHumans))

        # ---------------------------
        # --- Clear all of the humans
        # ---------------------------
        node_2 = pop.nodes[1]
        self.assertEqual(2, node_2.suid.id)
        self.assertEqual(2, len(node_2.individualHumans))
        node_2.individualHumans = []
        self.assertEqual(0, len(node_2.individualHumans))

        # -----------------------------------------------
        # --- Append humans to the end of the list
        # --- (just use the ones we took out of node_1)
        # -----------------------------------------------
        node_3 = pop.nodes[2]
        self.assertEqual(3, node_3.suid.id)
        self.assertEqual(7, len(node_3.individualHumans))
        human_2.m_age = 3333
        human_8.m_age = 3333
        human_14.m_age = 3333
        node_3.individualHumans.append( human_2 )
        node_3.individualHumans.append( human_8 )
        node_3.individualHumans.append( human_14 )
        self.assertEqual(10, len(node_3.individualHumans))

        # --------------------------------------------------------------
        # --- Verify that you can iterate over the nodes and the humans
        # --------------------------------------------------------------
        node_1_human_suids = [ 5, 11                              ] # 2, 8, 14 moved to node_3
        node_2_human_suids = [                                    ] # removed humans from node 2
        node_3_human_suids = [ 4, 7, 10, 13, 16, 19, 22, 2, 8, 14 ] # added 2, 8, 14 from node_1
        self.check_humans_in_nodes(pop,
                                   node_1_human_suids,
                                   node_2_human_suids,
                                   node_3_human_suids,
                                   age_node_1=1111,
                                   age_node_2=2222,
                                   age_node_3=3333 )

        # -------------------------------------------------------------------
        # --- Verify that we can save the file, read it and get the new ages.
        # -------------------------------------------------------------------
        output_file = os.path.join(manifest.output_folder, "TestReadVersion6.test_manipulating_human_list.state-00004.dtk")
        pop.write(output_file)
        pop = None
        gc.collect()

        self.assertFalse( os.path.exists(output_file), f"Expected output file to exist: {output_file}" )

        pop_modified = SerPop.SerializedPopulation(output_file)
        self.check_humans_in_nodes(pop_modified,
                                   node_1_human_suids,
                                   node_2_human_suids,
                                   node_3_human_suids,
                                   age_node_1=1111,
                                   age_node_2=2222,
                                   age_node_3=3333 )
        gc.collect()
        #os.remove(output_file)



if __name__ == "__main__":
    unittest.main()
