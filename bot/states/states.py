from aiogram.fsm.state import State, StatesGroup


class Onboarding(StatesGroup):
    q_age = State()
    q_occupation = State()
    q_living = State()
    q_pain = State()
    q_change = State()
    q_emotions = State()
    q_triggers = State()
    q_stress = State()
    q_assertiveness = State()
    q_help = State()
    q_people_pleasing = State()
    q_trust = State()
    q_goal = State()


class OnboardingLevel2(StatesGroup):
    q_childhood_family = State()
    q_childhood_relationship = State()
    q_core_belief_self = State()
    q_core_belief_others = State()
    q_core_belief_world = State()
    q_repeating_pattern = State()


class OnboardingLevel3(StatesGroup):
    q_romantic_pattern = State()
    q_self_esteem = State()
    q_psychosomatic = State()
    q_values = State()
    q_boundaries = State()


class SituationCollect(StatesGroup):
    waiting = State()
    collecting = State()


class SituationConfirm(StatesGroup):
    waiting_confirm = State()


class WorkOnProblem(StatesGroup):
    choosing = State()
    discussing = State()
    plan_review = State()


class CheckIn(StatesGroup):
    mood = State()
    situations = State()
    tasks = State()


class FreeTalk(StatesGroup):
    talking = State()
