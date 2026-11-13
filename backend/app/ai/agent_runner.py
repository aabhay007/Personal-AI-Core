"""Agent Task Execution Engine with checkpointing, retries, and Human-in-the-Loop approvals."""
import uuid
import time
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.agent_task import AgentTask, AgentStep
from app.tools.registry import tool_registry
from app.ai.planner import PlanGenerator

logger = logging.getLogger(__name__)


class AgentTaskRunner:
    """State machine orchestrating multi-step autonomous tasks."""

    @staticmethod
    async def create_and_plan_task(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        title: str,
        goal: str,
        user_id: Optional[uuid.UUID] = None,
        conversation_id: Optional[uuid.UUID] = None,
        custom_plan: Optional[List[Dict[str, Any]]] = None
    ) -> AgentTask:
        """Generate a plan and persist a new AgentTask with all planned steps."""
        plan = custom_plan or await PlanGenerator.generate_plan(goal=goal, title=title)

        task = AgentTask(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            created_by=user_id,
            title=title,
            goal=goal,
            status="planning",
            plan=plan,
            current_step_index=0
        )
        db.add(task)
        await db.flush()

        for idx, step_data in enumerate(plan):
            step = AgentStep(
                task_id=task.id,
                step_number=step_data.get("step_number", idx + 1),
                name=step_data.get("name", f"Step {idx + 1}"),
                description=step_data.get("description", ""),
                status="pending",
                tool_name=step_data.get("tool_name"),
                tool_arguments=step_data.get("tool_arguments") or {},
                requires_approval=bool(step_data.get("requires_approval", False)),
                approval_status="pending" if step_data.get("requires_approval") else None
            )
            db.add(step)

        task.status = "running"
        await db.commit()
        await db.refresh(task)
        return task

    @staticmethod
    async def run_task(
        db: AsyncSession,
        task_id: uuid.UUID
    ) -> AgentTask:
        """Run or resume an autonomous task through its sequential steps with checkpointing."""
        stmt = select(AgentTask).where(AgentTask.id == task_id)
        result = await db.execute(stmt)
        task = result.scalars().first()

        if not task:
            raise ValueError(f"Task '{task_id}' not found.")

        # Load ordered steps
        step_stmt = select(AgentStep).where(AgentStep.task_id == task_id).order_by(AgentStep.step_number)
        step_res = await db.execute(step_stmt)
        steps = step_res.scalars().all()

        task.status = "running"
        await db.commit()

        for i in range(task.current_step_index, len(steps)):
            step = steps[i]

            # 1. Human Approval Checkpoint
            if step.requires_approval and step.approval_status != "approved":
                step.status = "waiting_approval"
                step.approval_status = "pending"
                task.status = "waiting_approval"
                task.current_step_index = i
                await db.commit()
                logger.info(f"Task '{task.title}' paused at step {step.step_number} for human approval.")
                return task

            # 2. Step Execution
            step.status = "running"
            step.started_at = datetime.now(timezone.utc)
            await db.commit()

            start_t = time.perf_counter()
            step_success = True
            error_msg = None
            tool_output = None

            if step.tool_name:
                retries_left = task.max_retries
                step_success = False
                error_msg = None
                while retries_left >= 0:
                    try:
                        exec_res = await tool_registry.execute_tool(
                            name=step.tool_name,
                            arguments=step.tool_arguments or {},
                            workspace_id=task.workspace_id,
                            conversation_id=task.conversation_id,
                            db=db
                        )
                        if exec_res.get("success", False):
                            tool_output = exec_res.get("result")
                            step_success = True
                            error_msg = None
                            break
                        else:
                            error_msg = exec_res.get("error", "Tool execution failed")
                            step.retry_count += 1
                            retries_left -= 1
                    except Exception as e:
                        error_msg = str(e)
                        step.retry_count += 1
                        retries_left -= 1
            else:
                step_success = True
                error_msg = None

            exec_time = int((time.perf_counter() - start_t) * 1000)
            step.execution_time_ms = exec_time
            step.completed_at = datetime.now(timezone.utc)

            # 3. Checkpoint Step Outcome
            if step_success:
                step.status = "completed"
                step.tool_result = tool_output
                task.current_step_index = i + 1
                await db.commit()
            else:
                step.status = "failed"
                step.error_message = error_msg
                task.status = "failed"
                task.error_message = f"Failed at step {step.step_number} ({step.name}): {error_msg}"
                await db.commit()
                return task

        # 4. Final Task Completion
        task.status = "completed"
        task.result_summary = (
            f"Successfully executed all {len(steps)} steps for goal: '{task.goal}'. "
            f"Completed at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}."
        )
        await db.commit()
        await db.refresh(task)
        return task

    @staticmethod
    async def approve_step(
        db: AsyncSession,
        task_id: uuid.UUID,
        step_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> AgentTask:
        """Approve a pending sensitive step and resume task execution."""
        step_stmt = select(AgentStep).where(AgentStep.id == step_id, AgentStep.task_id == task_id)
        step_res = await db.execute(step_stmt)
        step = step_res.scalars().first()

        if not step:
            raise ValueError("Step not found.")

        if step.status != "waiting_approval":
            raise ValueError(f"Step is not waiting for approval (current status: {step.status}).")

        step.approval_status = "approved"
        step.approved_by = user_id
        step.approved_at = datetime.now(timezone.utc)
        step.status = "pending"
        await db.commit()

        # Resume task
        return await AgentTaskRunner.run_task(db=db, task_id=task_id)

    @staticmethod
    async def reject_step(
        db: AsyncSession,
        task_id: uuid.UUID,
        step_id: uuid.UUID,
        reason: str
    ) -> AgentTask:
        """Reject a pending sensitive step, halting the task with graceful reason logging."""
        step_stmt = select(AgentStep).where(AgentStep.id == step_id, AgentStep.task_id == task_id)
        step_res = await db.execute(step_stmt)
        step = step_res.scalars().first()

        if not step:
            raise ValueError("Step not found.")

        step.approval_status = "rejected"
        step.status = "failed"
        step.error_message = f"Rejected by user: {reason}"

        task_stmt = select(AgentTask).where(AgentTask.id == task_id)
        task_res = await db.execute(task_stmt)
        task = task_res.scalars().first()
        task.status = "cancelled"
        task.error_message = f"Action rejected at step {step.step_number}: {reason}"

        await db.commit()
        await db.refresh(task)
        return task
