import os
from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.adk.tools import AgentTool, google_search
from google.genai import types

retry_config = types.HttpRetryOptions(
    attempts=5, exp_base=7, initial_delay=1,
    http_status_codes=[429, 500, 503, 504],
)

MODEL_NAME = "gemini-2.5-flash-lite"
APP_NAME = "meal_planner"


def build_runner(database_url: str) -> Runner:
    session_service = DatabaseSessionService(database_url)

    planner = Agent(
        name="PlannerAgent",
        model=Gemini(model=MODEL_NAME, retry_options=retry_config),
        instruction="""You are a strict, analytical meal plan generator.
        Based on the user's goal, generate a structured, multi-day meal plan.
        Browse the web for accurate calorie and macro amounts using the google_search tool.
        Create the plan according to South Indian cuisine.
        Do not add non-vegetarian options more than 2 times a week unless explicitly asked.
        Structure output clearly: breakfast, lunch, evening snacks, dinner.
        Each meal must include: food name, serving size, calories, protein, carbs, fat.
        Include daily total macros at the end.
        """,
        tools=[google_search],
        output_key="main_meal_plan",
    )

    substitution = Agent(
        name="SubstitutionAgent",
        model=Gemini(model=MODEL_NAME, retry_options=retry_config),
        instruction="""You are a meal substitution agent.
        Suggest alternatives to meals in {main_meal_plan} when asked.
        If the user ate something off-plan, adjust remaining meals to meet daily macro targets.
        Use google_search for accurate macro values. All suggestions must be South Indian cuisine.
        Return a table with columns: "Existing Plan" and "New Plan".
        """,
        tools=[google_search],
        output_key="substituted_meals",
    )

    coordinator = Agent(
        name="CoordinationAgent",
        model=Gemini(model=MODEL_NAME, retry_options=retry_config),
        instruction="""You are a coordination agent for a South Indian meal planning assistant.
        Route queries:
        - New meal plan / diet plan → call PlannerAgent
        - Substitutions / alternatives / ate something off-plan → call SubstitutionAgent
        Relay the agent's response clearly. Always present data in well-formatted tables.
        """,
        tools=[AgentTool(planner), AgentTool(substitution)],
        output_key="coordinator_response",
    )

    return Runner(agent=coordinator, app_name=APP_NAME, session_service=session_service)