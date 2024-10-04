import platform 
import pyautogui
if platform.system() == 'Darwin':
    platform_name = 'macos'
    from macos.Grounding import GroundingAgent
    from macos.UIElement import UIElement
elif platform.system() == 'Linux':
    from ubuntu.Grounding import GroundingAgent
    from ubuntu.UIElement import UIElement
    platform_name = 'ubuntu'
else:
    raise NotImplementedError

import os
import re
import json 
import io 
import sys 
import logging
from agent_s.DAGPlanner import Planner
from agent_s.TaskExecutor import Executor
from typing import List, Dict, Tuple
import time 
logger = logging.getLogger("desktopenv.agent")

# Get the directory of the current script
working_dir = os.path.dirname(os.path.abspath(__file__))

# Construct the full path to the JSON file
file_path = os.path.join(working_dir, "kb", "formulate_query.json")

NUM_IMAGE_TOKEN = 1105  # Value set of screen of size 1920x1080 for openai vision


class GraphSearchAgent:
    def __init__(self,
                 engine_params,
                 platform="ubuntu",
                 max_tokens=1500,
                 top_p=0.9,
                 temperature=0.5,
                 action_space="pyautogui",
                 observation_type="a11y_tree",
                 max_trajectory_length=10,
                 a11y_tree_max_tokens=10000,
                 enable_reflection=True,
                 engine="perplexica",
                 vm_version="old",
                 update_reflection=True):  

        # resets the agent by initializing submodules
        self.engine_params = engine_params
        self.action_space = action_space
        self.observation_type = observation_type
        self.max_trajectory_length = 5
        self.engine = engine
        self.a11y_tree_max_tokens = a11y_tree_max_tokens
        self.vm_version = vm_version
        self.self_eval = True
        self.update_reflection = update_reflection

        self.reset()

    def reset(self):
        # Initialize Agents
        self.grounding_agent = GroundingAgent()
        self.planner = Planner(self.engine_params, self.grounding_agent)
        self.executor = Executor(self.engine_params, self.grounding_agent)
        self.replan = True
        self.get_next_subtask = True
        self.step_count = 0
        self.turn_count = 0
        self.failure_feedback = ''
        self.send_action = False
        self.done_tasks = []
        self.subtask_info = None

    def reset_executor_evaluator_states(self):
        self.executor.reset()
        self.step_count = 0

    def predict(self, instruction: str, obs: Dict) -> Tuple[Dict, List]:
        """
        Predict the next action(s) based on the current observation.
        """

        # Initialize the three info dictionaries
        planner_info = {}
        executor_info = {}
        evaluator_info = {
            'obs_evaluator_response': '',
            'num_input_tokens_evaluator': 0,
            'num_output_tokens_evaluator': 0,
            'evaluator_cost': 0.
        }
        actions = []

        # If the DONE response by the executor is for a subtask, then the agent should continue with the next subtask without sending the action to the environment
        while not self.send_action:
            self.subtask_status = 'In'
            # if replan is true, generate a new plan. True at start, then true again after a failed plan
            if self.replan:
                logger.info("(RE)PLANNING...")
                # failure feedback is the reason for the failure of the previous plan
                planner_info, self.subtasks = self.planner.get_action_queue(
                    instruction=instruction,
                    initial_observation=obs,
                    failure_feedback=self.failure_feedback,
                    replan=False if self.turn_count == 0 else self.replan)

                self.replan = False
                if 'search_query' in planner_info:
                    self.search_query = planner_info['search_query']
                else:
                    self.search_query = ""

            # use the exectuor to complete the topmost subtask
            if self.get_next_subtask:
                logger.info("GETTING NEXT SUBTASK...")
                self.current_subtask = self.subtasks.pop(0)
                logger.info(f"NEXT SUBTASK: {self.current_subtask}")
                self.get_next_subtask = False
                self.subtask_status = 'Start'

            # get the next action from the executor
            executor_info, actions = self.executor.generate_next_action(
                instruction=instruction,
                search_query=self.search_query,
                subtask=self.current_subtask.name,
                subtask_info=self.current_subtask.info,
                future_tasks=self.subtasks,
                done_task=self.done_tasks,
                obs=obs)

            self.step_count += 1

            # set the send_action flag to True if the executor returns an action
            self.send_action = True
            if 'FAIL' in actions:
                self.replan = True
                # set the failure feedback to the evaluator feedback
                self.failure_feedback = f"Completed subtasks: {self.done_tasks}. The subtask {self.current_subtask} cannot be completed. Please try another approach. {executor_info['plan_code']}. Please replan."
                self.get_next_subtask = True

                # reset the step count, executor, and evaluator
                self.reset_executor_evaluator_states()

                # if more subtasks are remaining, we don't want to send DONE to the environment but move on to the next subtask
                if self.subtasks:
                    self.send_action = False

            elif 'DONE' in actions:
                self.replan = False
                self.done_tasks.append(self.current_subtask)
                self.get_next_subtask = True
                if self.subtasks:
                    self.send_action = False
                self.subtask_status = 'Done'

                self.reset_executor_evaluator_states()

            self.turn_count += 1
        # reset the send_action flag for next iteration
        self.send_action = False

        # concatenate the three info dictionaries
        info = {**{k: v for d in [planner_info or {}, executor_info or {},
                                  evaluator_info or {}] for k, v in d.items()}}
        info.update({
        'subtask': self.current_subtask.name,
        'subtask_info': self.current_subtask.info,
        'subtask_status': self.subtask_status})

        return info, actions
    
    def update_narrative_memory(self, traj):
        """
        Update the narrative memory with the current observation.
        """
        try:
            if self.pdate_reflection:
                print(self.search_query)
                try:
                    reflection_path = os.path.join(working_dir, "kb", platform_name, "lifelong_learning_knowledge_base.json")
                    lifelong_learning_reflections = json.load(open(reflection_path))
                except:
                    lifelong_learning_reflections = {}
                if self.planner.search_query not in lifelong_learning_reflections.keys():
                    lifelong_learning_reflection = self.planner.generate_lifelong_learning_reflection(traj)
                    lifelong_learning_reflections[self.search_query] = lifelong_learning_reflection
                else:
                    pass
                with open(reflection_path, "w") as fout:
                    json.dump(lifelong_learning_reflections, fout, indent=2)
        except Exception as e:
            print(e)

    def update_episodic_memory(self, meta_data, subtask_traj):
        """
        Update the episodic memory with the current observation.
        """
        subtask = meta_data['subtask']
        subtask_info = meta_data['subtask_info']
        subtask_status = meta_data['subtask_status']
        # Handle subtask trajectory
        if subtask_status == 'Start' or subtask_status == 'Done':
            # If it's a new subtask start, finalize the previous subtask trajectory if it exists
            if subtask_traj:
                subtask_traj += '\nSubtask Completed.\n'
                subtask_key = subtask_traj.split("\n----------------------\n\nPlan:\n")[0]
                try:
                    subtask_path = os.path.join(working_dir, "kb", platform_name, "subtask_experience_knowledge_base.json")
                    kb = json.load(open(subtask_path))
                except:
                    kb = {}
                if subtask_key not in kb.keys():
                    subtask_summarization = self.planner.generate_subtask_summarization(subtask_traj)
                    kb[subtask_key] = subtask_summarization
                else:
                    subtask_summarization = kb[subtask_key]
                logger.info("subtask_key: %s", subtask_key)
                logger.info("subtask_summarization: %s", subtask_summarization)
                with open(subtask_path, "w") as fout:
                    json.dump(kb, fout, indent=2)
                # Reset for the next subtask
                subtask_traj = ''
            # Start a new subtask trajectory
            subtask_traj = 'Task:\n' + self.search_query + '\n\nSubtask: ' + subtask + '\nSubtask Instruction: ' + subtask_info + '\n----------------------\n\nPlan:\n' + meta_data['executor_plan'] + '\n'
        elif subtask_status == 'In':
            # Continue appending to the current subtask trajectory if it's still ongoing
            subtask_traj += '\n----------------------\n\nPlan:\n' + meta_data['executor_plan'] + '\n'

        return subtask_traj
    
    def run(self, instruction: str):
        obs = {}
        traj = 'Task:\n' + instruction
        subtask_traj = ""
        for _ in range(15):
            obs['accessibility_tree'] = UIElement.systemWideElement()
                
            # Get screen shot using pyautogui.
            # Take a screenshot
            screenshot = pyautogui.screenshot()

            # Save the screenshot to a BytesIO object
            buffered = io.BytesIO()
            screenshot.save(buffered, format="PNG")

            # Get the byte value of the screenshot
            screenshot_bytes = buffered.getvalue()
            # Convert to base64 string.
            obs['screenshot'] = screenshot_bytes 

            info, code = self.predict(instruction=instruction, obs=obs)

            if 'done' in code[0].lower() or 'fail' in code[0].lower():
                if platform.system() == 'Darwin':
                    os.system(f'osascript -e \'display dialog "Task Completed" with title "OpenACI Agent" buttons "OK" default button "OK"\'')
                elif platform.system() == 'Linux':
                    os.system(f'zenity --info --title="OpenACI Agent" --text="Task Completed" --width=200 --height=100')
                
                self.update_narrative_memory(traj)
                break 
        
            if _ == 3:
                self.update_narrative_memory(traj)
            
            if 'next' in code[0].lower():
                continue

            if 'wait' in code[0].lower():
                time.sleep(5)
                continue

            else:
                # if platform.system() == 'Darwin':
                #     # macOS: Use AppleScript to display a Yes/No dialog
                #     user_confirmation = os.popen(f'osascript -e \'display dialog "Do you want to proceed with the next action: {info["plan_code"]}?" with title "OpenACI Agent" buttons {"Yes", "No", "Exit"} default button "Yes"\'').read()
                #     if "No" in user_confirmation:
                #         continue
                #     elif "Exit" in user_confirmation:
                #         sys.exit(0)

                # elif platform.system() == 'Linux':
                #     # Linux: Use Zenity to display a Yes/No dialog
                #     user_confirmation = os.system(f'zenity --question --title="OpenACI Agent" --text="Do you want to proceed with the next action: {info["plan_code"]}?" --ok-label="Yes" --cancel-label="No" --extra-button="Exit" --width=200 --height=100')
                #     if user_confirmation == 1:
                #         continue
                #     elif user_confirmation == 2:
                #         sys.exit(0)

                time.sleep(1.)
                print("EXECUTING CODE:", code[0])
                exec(code[0])
                
                time.sleep(1.)
                
                # Update task and subtask trajectories and optionally the episodic memory
                traj += '\n\nReflection:\n' + str(info['reflection']) + '\n\n----------------------\n\nPlan:\n' + info['executor_plan']
                subtask_traj = self.update_episodic_memory(info, subtask_traj)
