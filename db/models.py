import datetime

from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, JSON
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Profile(Base):
    __tablename__ = "profile"

    user_id = Column(Integer, primary_key=True)
    basic_info = Column(JSON, default=dict)
    onboarding_level = Column(Integer, default=0)
    emotional_profile = Column(JSON, default=dict)
    relationships_profile = Column(JSON, default=dict)
    primary_pain = Column(Text, default="")
    desired_change = Column(Text, default="")
    goal = Column(Text, default="")
    childhood = Column(JSON, default=dict)
    core_beliefs = Column(JSON, default=dict)
    deep_profile = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    date = Column(DateTime, default=datetime.datetime.utcnow)
    situation = Column(Text, default="")
    emotions = Column(Text, default="")
    thoughts = Column(Text, default="")
    behavior = Column(Text, default="")
    trigger = Column(Text, default="")
    linked_problems = Column(JSON, default=list)
    source = Column(String(50), default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Problem(Base):
    __tablename__ = "problems"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    probability = Column(Integer, default=0)
    frequency = Column(Integer, default=0)
    linked_cases = Column(JSON, default=list)
    linked_problems = Column(JSON, default=list)
    root_cause = Column(Text, default="")
    status = Column(String(50), default="выявлена")
    severity = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    linked_problem_id = Column(Integer, nullable=False)
    tasks = Column(JSON, default=list)
    habits = Column(JSON, default=list)
    approach = Column(String(255), default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    progress = Column(Integer, default=0)


class MoodLog(Base):
    __tablename__ = "mood_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    date = Column(DateTime, default=datetime.datetime.utcnow)
    mood = Column(Integer, default=5)
    note = Column(Text, default="")
    related_cases = Column(JSON, default=list)
    tasks_completed = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    mode = Column(String(50), default="")
    messages = Column(JSON, default=list)
    session_start = Column(DateTime, default=datetime.datetime.utcnow)
    session_end = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
