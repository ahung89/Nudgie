from Nudgie.chat.chatgpt import identify_task
from Nudgie.models import NudgieTask
from Nudgie.constants import TASK_IDENTIFICATION_PROMPT


def confirm_task(nudgie_task: NudgieTask) -> None:
    pass


def identify_task(user_id: str, user_input: str) -> (float, list[NudgieTask]):
    tasks = NudgieTask.objects.filter(user_id=user_id, completed=False)

    # If there's only one task, there's no need to perform complex task identification.
    if tasks.count() == 1:
        print("only one task, skipping chatGPT task identification task query")
        return 1, [tasks[0]]
    #


def task_completion_flow(user_id: str, user_input: str):
    certainty, identified_tasks = identify_task(user_input)
    if certainty is True or len(identified_tasks) == 1:
        # log the data point
        # generate success message
        pass
    pass
