from .. import schema_to_class as s2c
import json
import emod_api.campaign as camp

schema_path = None
vaccine_type = "Generic"  # or AcquisitionBlocking or TransmissionBlocking or MortalityBlocking
iv_name = "Vaccine"
initial_effect = 1.0
box_duration = 100


# timestep = 0
# dupe_policy = "Replace" # or "Add" or "Abort" -- from covid branch
# Note that duration (what we call waning profile) needs to be configurable, but in an intuitive way


def new_intervention(timestep, v_type=vaccine_type, efficacy=initial_effect, sv_name=iv_name,
                     waning_duration=box_duration, d_a_d=None, cost_to_consumer=None,
                     e_i_r=None, intervention_only=False):
    """
    This is mostly an example but also potentially useful. With this you get a Vaccine with working defaults but
    2 configurables: type and efficacy. The duration is fixet at box. You of course must specify the timestep and you
    can add a vaccine name which is mostly useful if you're managing a duplicate policy.
    """

    intervention = s2c.get_class_with_defaults("Vaccine", schema_path)
    if s2c.uses_old_waning():
        efficacy_profile = "WaningEffectBox"
    else:
        efficacy_profile = "WaningEffect"
    waning = s2c.get_class_with_defaults(efficacy_profile, schema_path)
    waning.Initial_Effect = efficacy
    waning.Box_Duration = waning_duration

    if "Acquire" in v_type:
        intervention.Acquire_Config = waning
    elif "Transmit" in v_type:
        intervention.Transmit_Config = waning
    else:
        intervention.Mortality_Config = waning

    # Third, do the actual settings
    # intervention.Vaccine_Type = v_type
    intervention.Intervention_Name = sv_name
    if cost_to_consumer:
        intervention.Cost_To_Consumer = cost_to_consumer

    if d_a_d is not None:
        intervention.Dont_Allow_Duplicates = d_a_d
    if e_i_r:
        # set Enable_Intervention_Replacement only if it's True. We don't want to set it to False, because it's the
        # same as default and it will turn Dont_Allow_Duplicates to True automatically by emod-api since DAD is the
        # depends-on parameter for EIR.
        intervention.Enable_Intervention_Replacement = e_i_r


    if intervention_only:
        return intervention

    coordinator = s2c.get_class_with_defaults("StandardEventCoordinator", schema_path)
    coordinator.Intervention_Config = intervention
    event = s2c.get_class_with_defaults("CampaignEvent", schema_path)
    event.Event_Coordinator_Config = coordinator
    event.Start_Day = float(timestep)

    return event


def new_intervention2(timestep):
    """
    This version lets you invoke the function sans-parameters. You get the module-level params which you can set before calling this.
    This is designed to support are more data-oriented way of using this API, with everything like "a.b=c", and avoid "churn" on the 
    API itself (constantly changing function signature).
    TBD: Make sure that if this is called twice, we understand whether we have copies or references going on.
    """
    return new_intervention(timestep=timestep, v_type=vaccine_type, efficacy=initial_effect, sv_name=iv_name,
                            waning_duration=box_duration)


def new_intervention_as_file(timestep, filename=None):
    camp.add(new_intervention(timestep, vaccine_type, initial_effect, iv_name, box_duration))
    if filename is None:
        filename = "simple_vaccine.json"
    camp.save(filename)
    return filename
