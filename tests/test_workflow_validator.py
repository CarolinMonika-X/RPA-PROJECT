"""
Unit tests for Workflow and WorkflowStep schema validation.
"""

from backend.models import Workflow, WorkflowStep

def test_valid_workflow_passes_validation():
    wf = Workflow(
        id="wf_test_1",
        name="Valid Workflow",
        description="Testing validation logic",
        steps=[
            WorkflowStep(id="s1", name="Wait a bit", type="wait", params={"milliseconds": 100}),
            WorkflowStep(id="s2", name="Press Tab", type="press_key", params={"key": "tab"})
        ]
    )
    errors = wf.validate()
    assert len(errors) == 0

def test_workflow_with_empty_name_fails():
    wf = Workflow(
        id="wf_test_2",
        name="",
        description="No name workflow",
        steps=[WorkflowStep(id="s1", name="Wait", type="wait", params={"milliseconds": 100})]
    )
    errors = wf.validate()
    assert any("Workflow name cannot be empty" in e for e in errors)

def test_workflow_with_zero_steps_fails():
    wf = Workflow(
        id="wf_test_3",
        name="Empty steps",
        description="No steps",
        steps=[]
    )
    errors = wf.validate()
    assert any("must contain at least one step" in e for e in errors)

def test_invalid_step_type_fails():
    wf = Workflow(
        id="wf_test_4",
        name="Bad Step Type",
        description="Bad step",
        steps=[
            WorkflowStep(id="s1", name="Malicious Exec", type="arbitrary_eval_shell", params={"cmd": "dir"})
        ]
    )
    errors = wf.validate()
    assert any("Invalid type 'arbitrary_eval_shell'" in e for e in errors)

def test_step_parameter_requirement_validation():
    # activate_window requires title_pattern
    s1 = WorkflowStep(id="s1", name="Activate App", type="activate_window", params={})
    assert any("'title_pattern' is required" in e for e in s1.validate())

    # image_detection requires template_name
    s2 = WorkflowStep(id="s2", name="Find Button", type="image_detection", params={})
    assert any("'template_name' is required" in e for e in s2.validate())

    # press_key requires key
    s3 = WorkflowStep(id="s3", name="Send Key", type="press_key", params={})
    assert any("'key' is required" in e for e in s3.validate())
