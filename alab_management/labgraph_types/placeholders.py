from labgraph import Actor


try:
    placeholder_actor = Actor.get_by_name("Placeholder before execution")
except:
    placeholder_actor = Actor(
        name="Placeholder before execution",
        description="This is a placeholder actor assigned to tasks that are planned but have not yet been executed. This actor will be replaced by the actual actor when the task is executed.",
    )
    placeholder_actor.save()
