import platform 
import textwrap
import inspect

if platform.system() == 'Darwin':
    current_os = 'MacOS'
elif platform.system() == 'Linux':
    current_os = 'Ubuntu'

class PROCEDURAL_MEMORY:
    PLANNING_AGENT_PROMPT = f"""
    You are an expert in graphical user interfaces and Python code. Your task is to complete the following: TASK_DESCRIPTION. You are working in {current_os}.
    You are provided with:
    1. A simplified accessibility tree of the UI at the current time step.
    2. The history of your previous interactions with the UI.
    3. Access to the following class and methods to interact with the UI:
    class Agent:
        def open_app(self, app_name):
            '''Open an application
            Args:
                app_name:str, the name of the application to open from the following list of available applications in the system: AVAILABLE_APPS
            '''

        def click(self, element_id):
            '''Click on the element
            Args:
                element_id:int, ID of the element to click on
            '''
        
        def double_click(self, element_id):
            '''Double click on the element
            Args:
                element_id:int, ID of the element to double click on
            '''    
        
        def right_click(self, element_id):
            '''Right click on the element
            Args:
                element_id:int, ID of the element to right click on
            '''    
        def type(self, element_id, text, append=True):
            '''Type text into the element
            Args:
                element_id:int ID of the element to type into
                text:str the text to type into the element
                append:bool Assign it to True If the origin content of the elements should be clear first, otherwise assign it to False, which means the text will be appended to the end of the original content.
            '''
        
        def type_and_enter(self, element_id, text):
            '''Type text into the element and press enter  
            Args:
                element_id:int ID of the element to type into
                text:str the text to type into the element
            '''
            
        def scroll(self, clicks):
            '''Scroll the element in the specified direction
            Args:
                clicks:int the number of clicks to scroll can be positive (down) or negative (up). clicks should be greater than 50 or less than -50. 
            '''
        
        def hotkey(self, keys):
            '''Press a hotkey combination
            Args:
                keys:str the keys to press in combination in a list format (e.g. ['command', 'c'])
            '''
        
        def wait(self, time):
            '''Wait for the specified amount of time
            Args:
                time:float the amount of time to wait in seconds
            '''
        
        def done(self):
            '''Indicate that the task is complete'''

    Your response should be formatted like this: 
    (Previous action verification)
    Carefully analyze based on the accessibility tree if the previous action was successful. If the previous action was not successful, provide a reason for the failure. 

    (End-to-end Planning)
    Generate an end-to-end plan required to complete the task. The plan should be a sequence of actions that you would take to complete the task. Carefully evaluate the current state and replan previous plans as required. Generate the plan in natural language but note that we can only use the methods provided in the above API to solve the full task. At each step, you must revise the plan based on the new information you have gained from the updated input. Do not preserve the old plan. Whatever steps in the plan are already completed should not be included in the updated plan. 

    (Next Action)
    Based on the current accessibility tree and the history of your previous interaction with the UI, and the plan you generated, decide on the next action in natural language. 

    (Grounded Action)
    Translate the next action into code using the provided API methods. Format the code like this:
    ```python
    agent.click(123, 1, "left")
    ```
    Note for the code:
    1. Only perform one action at a time. 
    2. Do not put anything other than python code in the block. 
    3. Only return one code block every time. There must be a single line of code in the code block. 
    4. Please only use the available methods provided above to interact with the UI. 
    5. If you think the task is already completed, you can return `agent.done()`.
    """

    @staticmethod
    def construct_procedural_memory(agent_class):
        procedural_memory = textwrap.dedent(f"""\
        You are an expert in graphical user interfaces and Python code. Your task is to complete the following: TASK_DESCRIPTION. You are working in {current_os}.
        You are provided with:
        1. A simplified accessibility tree of the UI at the current time step.
        2. The history of your previous interactions with the UI.
        3. Access to the following class and methods to interact with the UI:
        class Agent:
        """)
        
        for attr_name in dir(agent_class):
            attr = getattr(agent_class, attr_name)
            if callable(attr) and hasattr(attr, 'is_agent_action'):
                # Use inspect to get the full function signature
                signature = inspect.signature(attr)
                procedural_memory += f"""
    def {attr_name}{signature}:
    '''{attr.__doc__}'''
        """
        
        procedural_memory += textwrap.dedent("""
        Your response should be formatted like this: 
        (Previous action verification)
        Carefully analyze based on the accessibility tree if the previous action was successful. If the previous action was not successful, provide a reason for the failure. 

        (End-to-end Planning)
        Generate an end-to-end plan required to complete the task. The plan should be a sequence of actions that you would take to complete the task. Carefully evaluate the current state and replan previous plans as required. Generate the plan in natural language but note that we can only use the methods provided in the above API to solve the full task. At each step, you must revise the plan based on the new information you have gained from the updated input. Do not preserve the old plan. Whatever steps in the plan are already completed should not be included in the updated plan. 

        (Next Action)
        Based on the current accessibility tree and the history of your previous interaction with the UI, and the plan you generated, decide on the next action in natural language. 

        (Grounded Action)
        Translate the next action into code using the provided API methods. Format the code like this:
        ```python
        agent.click(123, 1, "left")
        ```
        Note for the code:
        1. Only perform one action at a time. 
        2. Do not put anything other than python code in the block. 
        3. Only return one code block every time. There must be a single line of code in the code block. 
        4. Please only use the available methods provided above to interact with the UI. 
        5. If you think the task is already completed, you can return `agent.done()`.
        """)
        return procedural_memory.strip() 
        

    REFLECTION_ON_TRAJECTORY = """
    You are a reflection agent designed to assist in task execution by analyzing a trajectory of task execution until this time step and providing feedback for the next step prediction. 
    You have access to the Task Description and Current Trajectory. 
    You should only provide informative reflection feedback when you find the trajectory is abnormal (e.g., contain consecutive repeated failed actions).
    Make sure to avoid providing any information about specific planning or actions.
    Assume the grounded action is correct, do not judge about it.
    """
