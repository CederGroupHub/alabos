from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer
from threading import Thread
from alab_management.task_view.task_view import TaskView
import time
import os
import yaml

class FileHandler(PatternMatchingEventHandler):

    def __init__(self, event, patterns):
        PatternMatchingEventHandler.__init__(self, patterns=patterns)
        self.process_event = event

    def process(self, found_file):
        file_loc = found_file.src_path
        self.process_event(file_loc)

    def on_created(self, found_file):
        self.process(found_file)

class FileLogger(object):

    def __init__(self, action, patterns, path='./'):
        self.path = path
        self.event_handler = FileHandler(action, patterns)

    def start(self):
        self.observer = Observer()
        self.observer.schedule(self.event_handler, self.path, recursive=True)
        self.observer.start()

    def stop(self):
        self.observer.stop()

class TaskManager:
    """
    Task manager supports:
    - scanning for new recipe and processing new recipe into dict of operations.
    - creating task and adding necessary operations between compiled synthesis recipe. e.g., moving. Then, submit into database
    - #TODO: managing operation readiness by utilizing directed acyclic graph (DAG) to maintain operation order.
    - #TODO: grouping similar operation together [batch operation] (need new thread for checking similar operations and update task view DAG accordingly).
    - #TODO: grouping "immediate" operation together -> this can be migrated to task definition where two devices are booked together.
    - #TODO, FUTURE VERSION: update the whole code to support partial recipe starting from a given initial position.
                            For example, a pre-mixed powder, just want to be heated and XRD'ed 
                            or a pre-heated powder just want to be XRD'ed.
    """

    def __init__(self):
        self.task_view=TaskView()

    def run(self):
        """
        Start a thread to receive recipes (.yaml) and process it
        """
        stream_thread = Thread(target=self.stream())
        stream_thread.start()

    def process_recipe(self, file_loc):
        """
        Method to add necessary operations and submit processed recipe into database.

        Args:
            file_loc: recipe file location.
        """
        self.recipe=self.parse_recipe(file_loc)
        submit_full_recipe(self.recipe)

    def stream(self):
        """
        Method to create streaming tunnel of .yaml input recipes.
        """
        patterns=["*.yml","*.yaml"]
        self.file_logger = FileLogger(action=self.process_recipe, patterns=patterns, path=os.getcwd())
        self.file_logger.start()

    def parse_recipe(self, file_loc):
        """
        Method to parse a recipe into a dict of operations.

        Args:
            file_loc: recipe file location.

        Returns:
            a dict of operations.
        """
        loaded_recipe = yaml.load(open(file_loc))
        parsed_recipe={
            "op_names":[],
            "op_types":[],
            "op_parameters":[]
        }

        for i in range(len(loaded_recipe[0]['synthesis_operations'])):
            parsed_recipe["op_names"].append(loaded_recipe[0]['synthesis_operations'][i]["name"])
            parsed_recipe["op_types"].append(loaded_recipe[0]['synthesis_operations'][i]["type"])
            parsed_recipe["op_parameters"].append(loaded_recipe[0]['synthesis_operations'][i]["parameters"])
        
        return parsed_recipe

    def submit_full_recipe(self, parsed_recipe):
        """
        Method to create task and fill tasks with moving operations.

        Args:
            parsed_recipe: a dict structured parsed recipe.
        Returns:
            a dict of operations with added necessary operations.
        """
        # TODO: sample_view -> where do we call create_sample?
        for i in range(len(parsed_recipe["op_names"])):
            if i == 0:
                previous_task=self.task_view.create_task(task_type=parsed_recipe["op_types"][i], parameters=parsed_recipe["op_parameters"][i],
                                                         previous_tasks=None,next_tasks=None)
                next_task=self.task_view.create_task(task_type="moving", parameters=None,
                                                         previous_tasks=previous_task,next_tasks=None)
                self.task_view.update_next(task_id=previous_task, next_tasks=next_task)
                previous_task=next_task
            else:
                next_task=self.task_view.create_task(task_type=parsed_recipe["op_types"][i], parameters=parsed_recipe["op_parameters"][i],
                                                         previous_tasks=previous_task,next_tasks=None)
                self.task_view.update_next(task_id=previous_task, next_tasks=next_task)
                previous_task=next_task
                next_task=self.task_view.create_task(task_type="moving", parameters=None,
                                                         previous_tasks=previous_task, next_tasks=None)
                self.task_view.update_next(task_id=previous_task, next_tasks=next_task)
                previous_task=next_task
