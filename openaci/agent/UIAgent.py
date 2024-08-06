import time
import xml.etree.ElementTree as ET

from openaci.agent.ProceduralMemory import PROCEDURAL_MEMORY
from openaci.macos.Grounding import GroundingAgent
from openaci.agent.MultimodalAgent import LMMAgent

import os 
from typing import Dict, List
import logging
import re 
from typing import Dict, List

logger = logging.getLogger("openaci.agent")

# Get the directory of the current script
working_dir = os.path.dirname(os.path.abspath(__file__))

def parse_single_code_from_string(input_string):
    input_string = input_string.strip()
    if input_string.strip() in ['WAIT', 'DONE', 'FAIL']:
        return input_string.strip()

    # This regular expression will match both ```code``` and ```python code```
    # and capture the `code` part. It uses a non-greedy match for the content inside.
    pattern = r"```(?:\w+\s+)?(.*?)```"
    # Find all non-overlapping matches in the string
    matches = re.findall(pattern, input_string, re.DOTALL)

    # The regex above captures the content inside the triple backticks.
    # The `re.DOTALL` flag allows the dot `.` to match newline characters as well,
    # so the code inside backticks can span multiple lines.

    # matches now contains all the captured code snippets

    codes = []

    for match in matches:
        match = match.strip()
        commands = ['WAIT', 'DONE', 'FAIL']  # fixme: updates this part when we have more commands

        if match in commands:
            codes.append(match.strip())
        elif match.split('\n')[-1] in commands:
            if len(match.split('\n')) > 1:
                codes.append("\n".join(match.split('\n')[:-1]))
            codes.append(match.split('\n')[-1])
        else:
            codes.append(match)

    return codes[0]

# TODO: Rename this class and unify with grounding variations and planning variations
class IDBasedGroundingUIAgent:
    def __init__(self,
                 engine_params,
                 platform="macos",
                 max_tokens=1500,
                 top_p=0.9,
                 temperature=0.5,
                 action_space="pyautogui",
                 observation_type="a11y_tree",
                 max_trajectory_length=3,
                 a11y_tree_max_tokens=10000,
                 enable_reflection=True,):

        # Initialize Agents
        self.planning_agent = LMMAgent(engine_params)
        self.reflection_agent = LMMAgent(engine_params)

        # Set parameters
        self.enable_reflection = enable_reflection
        self.platform = platform
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.temperature = temperature
        self.action_space = action_space
        self.observation_type = observation_type
        self.max_trajectory_length = max_trajectory_length
        self.a11y_tree_max_tokens = a11y_tree_max_tokens

        # Initialize variables
        self.plans = []
        self.actions = []
        self.inputs = []
        self.messages = []
        self.feedbacks = []
        self.reflections = []

        self.planning_module_system_prompt = PROCEDURAL_MEMORY.PLANNING_AGENT_PROMPT

        self.reflection_module_system_prompt = PROCEDURAL_MEMORY.REFLECTION_ON_TRAJECTORY

        self.turn_count = None

    def reset(self):
        self.turn_count = 0
        self.planner_history = []
        self.feedback_history = []
        self.action_history = []
        self.planning_agent.reset()
        self.reflection_agent.reset()

    def flush_messages(self):
        for agent in [self.planning_agent, self.reflection_agent]:
            # After every max_trajectory_length trajectories, remove messages from the start except the system prompt
            if len(agent.messages) > 2*self.max_trajectory_length + 1:
                # Remove the user message and assistant message, both are 1 because the elements will move back after 1 pop
                agent.remove_message_at(1)
                agent.remove_message_at(1)

    def call_llm(self, agent):
        # Retry if fails
        max_retries = 3  # Set the maximum number of retries
        attempt = 0
        while attempt < max_retries:
            try:
                response = agent.get_response()
                break  # If successful, break out of the loop
            except Exception as e:
                attempt += 1
                print(f"Attempt {attempt} failed: {e}")
                if attempt == max_retries:
                    print("Max retries reached. Handling failure.")
            time.sleep(1.)
        return response

    def predict(self, instruction: str, obs: Dict) -> List:
        """
        Predict the next action(s) based on the current observation.
        """
        # Provide the top_app to the Grounding Agent to remove all other applications from the tree. At t=0, top_app is None
        agent = GroundingAgent(
            obs
        )

        if self.turn_count == 0:
            self.planning_agent.add_system_prompt(
            self.planning_module_system_prompt
            .replace("TASK_DESCRIPTION", instruction))
        
        # Clear older messages 
        self.flush_messages()
        
        # Reflection generation
        reflection = None
        if self.enable_reflection and self.turn_count > 0:
            self.reflection_agent.add_system_prompt(
                self.reflection_module_system_prompt)
            self.reflection_agent.add_message(
                'Task Description: ' + instruction + '\n' + 'Current Trajectory: ' + '\n\n'.join(self.planner_history) + '\n')
            reflection = self.call_llm(self.reflection_agent)
            self.reflections.append(reflection)
            self.reflection_agent.add_message(reflection)

            logger.info("REFLECTION: %s", reflection)

        # Plan Generation
        if reflection:
            self.planning_agent.add_message('\nYou may use the reflection on the previous trajectory: ' + reflection +
                                            f"\nAccessibility Tree: {agent.linearized_accessibility_tree}")
        else:
            self.planning_agent.add_message(
                f"Accessibility Tree: {agent.linearized_accessibility_tree}")

        plan = self.call_llm(self.planning_agent)
        self.planner_history.append(plan)
        logger.info("PLAN: %s", plan)

        self.planning_agent.add_message(plan)

        # Extract code block from the plan
        plan_code = parse_single_code_from_string(plan)
        exec_code = eval(plan_code)

        # If agent selects an element that was out of range, it should not be executed just send a WAIT command. 
        if agent.index_out_of_range_flag:
            plan_code = 'WAIT'

        info = {
            'plan': plan,
            'linearized_accessibility_tree': agent.linearized_accessibility_tree,
            'plan_code': plan_code,
            'reflection': reflection,
        }

        self.turn_count+=1

        return info, [exec_code]
