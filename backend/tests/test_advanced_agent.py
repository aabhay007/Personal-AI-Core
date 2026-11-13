"""Tests for Phase 7 Advanced Multi-Step Planning and Human-in-the-Loop Approvals."""
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.models.agent_task import AgentTask, AgentStep
from app.ai.agent_runner import AgentTaskRunner
from app.core.security import hash_password


@pytest.mark.asyncio
async def test_multi_step_task_planning_and_execution(db_session: AsyncSession):
    """Test full multi-step task planning and execution with native tools."""
    user = User(
        id=uuid.uuid4(),
        email="planner@example.com",
        password_hash=hash_password("Pass123!"),
        full_name="Planner"
    )
    ws = Workspace(id=uuid.uuid4(), name="Agent Lab", owner_id=user.id)
    ws_member = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="owner")
    db_session.add_all([user, ws, ws_member])
    await db_session.commit()

    custom_plan = [
        {
            "step_number": 1,
            "name": "Check Current Timestamp",
            "description": "Retrieve current server time.",
            "tool_name": "get_current_datetime",
            "tool_arguments": {"timezone_name": "UTC"},
            "requires_approval": False
        },
        {
            "step_number": 2,
            "name": "Compute Metric",
            "description": "Calculate math metric (100 * 2.5).",
            "tool_name": "calculator",
            "tool_arguments": {"expression": "100 * 2.5"},
            "requires_approval": False
        }
    ]

    # 1. Create and plan task
    task = await AgentTaskRunner.create_and_plan_task(
        db=db_session,
        workspace_id=ws.id,
        title="Automated Health & Calculation Task",
        goal="Fetch time and compute metrics",
        user_id=user.id,
        custom_plan=custom_plan
    )
    assert task.status == "running"
    assert len(task.plan) == 2

    # 2. Run task to completion
    completed_task = await AgentTaskRunner.run_task(db=db_session, task_id=task.id)
    assert completed_task.status == "completed"
    assert completed_task.current_step_index == 2
    assert "Successfully executed all 2 steps" in completed_task.result_summary


@pytest.mark.asyncio
async def test_human_in_the_loop_approval_flow(db_session: AsyncSession):
    """Test that sensitive steps pause in waiting_approval until human approves."""
    user = User(
        id=uuid.uuid4(),
        email="approver@example.com",
        password_hash=hash_password("Pass123!"),
        full_name="Approver"
    )
    ws = Workspace(id=uuid.uuid4(), name="Approval WS", owner_id=user.id)
    ws_member = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="owner")
    db_session.add_all([user, ws, ws_member])
    await db_session.commit()

    custom_plan = [
        {
            "step_number": 1,
            "name": "Non-sensitive step",
            "description": "Check time",
            "tool_name": "get_current_datetime",
            "tool_arguments": {"timezone_name": "UTC"},
            "requires_approval": False
        },
        {
            "step_number": 2,
            "name": "Sensitive database operation",
            "description": "Perform sensitive read query",
            "tool_name": "calculator",
            "tool_arguments": {"expression": "500 * 10"},
            "requires_approval": True
        }
    ]

    task = await AgentTaskRunner.create_and_plan_task(
        db=db_session,
        workspace_id=ws.id,
        title="Sensitive Approval Task",
        goal="Check time then run sensitive calc",
        user_id=user.id,
        custom_plan=custom_plan
    )

    # 1. Run task -> should pause at step 2
    paused_task = await AgentTaskRunner.run_task(db=db_session, task_id=task.id)
    assert paused_task.status == "waiting_approval"
    assert paused_task.current_step_index == 1

    # Check step 2 status
    step_2 = paused_task.steps[1]
    assert step_2.status == "waiting_approval"
    assert step_2.approval_status == "pending"

    # 2. Approve step -> task should resume and complete
    resumed_task = await AgentTaskRunner.approve_step(
        db=db_session,
        task_id=task.id,
        step_id=step_2.id,
        user_id=user.id
    )
    assert resumed_task.status == "completed"
    assert resumed_task.current_step_index == 2
    assert step_2.approval_status == "approved"
    assert step_2.status == "completed"
    assert step_2.tool_result["result"] == 5000.0


@pytest.mark.asyncio
async def test_human_in_the_loop_rejection_flow(db_session: AsyncSession):
    """Test that rejecting a sensitive step halts the task with proper error recording."""
    user = User(
        id=uuid.uuid4(),
        email="rejector@example.com",
        password_hash=hash_password("Pass123!"),
        full_name="Rejector"
    )
    ws = Workspace(id=uuid.uuid4(), name="Reject WS", owner_id=user.id)
    ws_member = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="owner")
    db_session.add_all([user, ws, ws_member])
    await db_session.commit()

    custom_plan = [
        {
            "step_number": 1,
            "name": "Dangerous mutation action",
            "description": "Requires explicit confirmation",
            "tool_name": "calculator",
            "tool_arguments": {"expression": "1 + 1"},
            "requires_approval": True
        }
    ]

    task = await AgentTaskRunner.create_and_plan_task(
        db=db_session,
        workspace_id=ws.id,
        title="Rejection Task",
        goal="Test human rejection",
        user_id=user.id,
        custom_plan=custom_plan
    )

    paused_task = await AgentTaskRunner.run_task(db=db_session, task_id=task.id)
    assert paused_task.status == "waiting_approval"

    # Reject step
    step_1 = paused_task.steps[0]
    cancelled_task = await AgentTaskRunner.reject_step(
        db=db_session,
        task_id=task.id,
        step_id=step_1.id,
        reason="Security policy violation"
    )
    assert cancelled_task.status == "cancelled"
    assert "Security policy violation" in cancelled_task.error_message
    assert step_1.status == "failed"
    assert step_1.approval_status == "rejected"


@pytest.mark.asyncio
async def test_tasks_api_endpoints(async_client: AsyncClient, db_session: AsyncSession):
    """Test REST API endpoints for tasks creation, listing, execution, and approval."""
    # 1. Register & login
    reg_res = await async_client.post("/api/v1/auth/register", json={
        "email": "agentuser@example.com",
        "password": "Password123!",
        "full_name": "Agent User"
    })
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create workspace
    ws_res = await async_client.post("/api/v1/workspaces", json={"name": "Agent Workspace"}, headers=headers)
    ws_id = ws_res.json()["id"]

    # 3. Create Task via API
    task_res = await async_client.post(
        f"/api/v1/tasks?workspace_id={ws_id}",
        json={
            "title": "API Multi-Step Task",
            "goal": "Verify server uptime",
            "custom_plan": [
                {
                    "step_number": 1,
                    "name": "Get Server Time",
                    "description": "Retrieve timezone",
                    "tool_name": "get_current_datetime",
                    "tool_arguments": {"timezone_name": "UTC"},
                    "requires_approval": False
                }
            ]
        },
        headers=headers
    )
    assert task_res.status_code == 201
    task_data = task_res.json()
    task_id = task_data["id"]
    assert len(task_data["steps"]) == 1

    # 4. List tasks
    list_res = await async_client.get(f"/api/v1/tasks?workspace_id={ws_id}", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

    # 5. Run task via API
    run_res = await async_client.post(f"/api/v1/tasks/{task_id}/run", headers=headers)
    assert run_res.status_code == 200
    completed = run_res.json()
    assert completed["status"] == "completed"
    assert completed["steps"][0]["status"] == "completed"
