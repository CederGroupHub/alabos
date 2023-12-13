from labgraph import Actor, ActorView


actor_view = ActorView()
try:
    PLACEHOLDER_ACTOR_FOR_TASKS_THAT_HAVENT_RUN_YET = actor_view.get_by_name(
        "Placeholder before execution"
    )[0]
except:
    PLACEHOLDER_ACTOR_FOR_TASKS_THAT_HAVENT_RUN_YET = Actor(
        name="Placeholder before execution",
        tags=["ALabOS"],
        description="This is a placeholder actor assigned to tasks that are planned but have not yet been executed. This actor will be replaced by the actual actor when the task is executed.",
    )
    actor_view.add(PLACEHOLDER_ACTOR_FOR_TASKS_THAT_HAVENT_RUN_YET)
