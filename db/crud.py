import datetime
from typing import Optional

from sqlalchemy import select, delete, desc
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Profile, Case, Problem, Plan, MoodLog, Conversation


async def get_profile(session: AsyncSession, user_id: int) -> Optional[Profile]:
    result = await session.execute(select(Profile).where(Profile.user_id == user_id))
    return result.scalar_one_or_none()


async def create_profile(session: AsyncSession, user_id: int) -> Profile:
    profile = Profile(user_id=user_id)
    session.add(profile)
    await session.commit()
    return profile


async def update_profile(session: AsyncSession, user_id: int, **kwargs) -> Profile:
    profile = await get_profile(session, user_id)
    if not profile:
        profile = await create_profile(session, user_id)
    for key, value in kwargs.items():
        if hasattr(profile, key) and value is not None:
            setattr(profile, key, value)
    profile.updated_at = datetime.datetime.utcnow()
    await session.commit()
    return profile


async def get_cases(session: AsyncSession, user_id: int, limit: int = 5) -> list[Case]:
    result = await session.execute(
        select(Case).where(Case.user_id == user_id).order_by(desc(Case.created_at)).limit(limit)
    )
    return list(result.scalars().all())


async def create_case(session: AsyncSession, user_id: int, **kwargs) -> Case:
    case = Case(user_id=user_id, **kwargs)
    session.add(case)
    await session.commit()
    return case


async def get_problems(session: AsyncSession, user_id: int) -> list[Problem]:
    result = await session.execute(
        select(Problem).where(Problem.user_id == user_id).order_by(desc(Problem.probability * Problem.severity))
    )
    return list(result.scalars().all())


async def get_problem(session: AsyncSession, problem_id: int) -> Optional[Problem]:
    result = await session.execute(select(Problem).where(Problem.id == problem_id))
    return result.scalar_one_or_none()


async def create_problem(session: AsyncSession, user_id: int, **kwargs) -> Problem:
    problem = Problem(user_id=user_id, **kwargs)
    session.add(problem)
    await session.commit()
    return problem


async def update_problem(session: AsyncSession, problem_id: int, **kwargs) -> Optional[Problem]:
    problem = await get_problem(session, problem_id)
    if not problem:
        return None
    for key, value in kwargs.items():
        if hasattr(problem, key) and value is not None:
            setattr(problem, key, value)
    problem.updated_at = datetime.datetime.utcnow()
    await session.commit()
    return problem


async def get_plans(session: AsyncSession, user_id: int) -> list[Plan]:
    result = await session.execute(select(Plan).where(Plan.user_id == user_id))
    return list(result.scalars().all())


async def get_plan(session: AsyncSession, plan_id: int) -> Optional[Plan]:
    result = await session.execute(select(Plan).where(Plan.id == plan_id))
    return result.scalar_one_or_none()


async def create_plan(session: AsyncSession, user_id: int, **kwargs) -> Plan:
    plan = Plan(user_id=user_id, **kwargs)
    session.add(plan)
    await session.commit()
    return plan


async def update_plan(session: AsyncSession, plan_id: int, **kwargs) -> Optional[Plan]:
    plan = await get_plan(session, plan_id)
    if not plan:
        return None
    for key, value in kwargs.items():
        if hasattr(plan, key) and value is not None:
            setattr(plan, key, value)
    await session.commit()
    return plan


async def create_mood_log(session: AsyncSession, user_id: int, **kwargs) -> MoodLog:
    log = MoodLog(user_id=user_id, **kwargs)
    session.add(log)
    await session.commit()
    return log


async def get_mood_logs(session: AsyncSession, user_id: int, limit: int = 30) -> list[MoodLog]:
    result = await session.execute(
        select(MoodLog).where(MoodLog.user_id == user_id).order_by(desc(MoodLog.date)).limit(limit)
    )
    return list(result.scalars().all())


async def get_active_conversation(session: AsyncSession, user_id: int, mode: str) -> Optional[Conversation]:
    result = await session.execute(
        select(Conversation).where(
            Conversation.user_id == user_id,
            Conversation.mode == mode,
            Conversation.is_active == True,
        )
    )
    return result.scalar_one_or_none()


async def create_conversation(session: AsyncSession, user_id: int, mode: str) -> Conversation:
    conv = Conversation(user_id=user_id, mode=mode)
    session.add(conv)
    await session.commit()
    return conv


async def add_message_to_conversation(session: AsyncSession, conv_id: int, role: str, content: str):
    conv = await session.get(Conversation, conv_id)
    if not conv:
        return
    messages = list(conv.messages or [])
    messages.append({"role": role, "content": content, "timestamp": datetime.datetime.utcnow().isoformat()})
    conv.messages = messages
    await session.commit()


async def end_conversation(session: AsyncSession, conv_id: int):
    conv = await session.get(Conversation, conv_id)
    if not conv:
        return
    conv.is_active = False
    conv.session_end = datetime.datetime.utcnow()
    await session.commit()


async def delete_conversation(session: AsyncSession, conv_id: int):
    await session.execute(delete(Conversation).where(Conversation.id == conv_id))
    await session.commit()
