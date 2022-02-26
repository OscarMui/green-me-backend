RECOMMENDED_PROBABILITY_OF_SUCCESS = {
    # 0 means the user stated they already do the task
    0: 0.95,

    # Probabilties for hardness ratings:
    1: 0.9,
    2: 0.75,
    3: 0.5,
    4: 0.15,
    5: 0.01
}

NOT_RECOMMENDED_PROBABILITY_OF_SUCCESS = {
    # 0 means the user stated they already do the task
    0: 0.95 * 0.95,

    # Probabilties for hardness ratings:
    1: 0,
    2: 0,
    3: 0,
    4: 0,
    5: 0
}

AVERAGE_FOOTPRINT_PER_WEEK = {
    'co2': 192.0,
    'waste': 7.5
}

NUMBER_OF_TASKS_AT_ONE_TIME = 3

def get_task_template_with_id(all_task_templates, id):
    for task_template in all_task_templates:
        if task_template.id == id:
            return task_template

def get_sorted_impacts(question_id_dict, question_responses, all_task_templates, incomplete_tasks, completed_tasks):
    impacts = []
    for response in question_responses:
        hardness_rating = 0
        if response.answer1 == "yes":
            hardness_rating = 0
        else:
            hardness_rating = int(response.answer2)

        rec_prob = RECOMMENDED_PROBABILITY_OF_SUCCESS[hardness_rating]
        not_rec_prob = NOT_RECOMMENDED_PROBABILITY_OF_SUCCESS[hardness_rating]

        # Skip the planes question if the person doesn't fly
        if hardness_rating == 0 and response.question_id == 4:
            continue

        increase_in_probability = rec_prob - not_rec_prob
        task_template = get_task_template_with_id(all_task_templates, response.question_id)

        score = task_template.carbon_savings / AVERAGE_FOOTPRINT_PER_WEEK['co2']
        score += task_template.waste_savings / AVERAGE_FOOTPRINT_PER_WEEK['waste']
        score *= increase_in_probability

        impacts.append([score, response])

    impacts.sort(reverse=True)

    return impacts

def get_task_templates_to_recommend(impacts, incomplete_tasks):
    task_templates_to_recommend = []
    for [score, task_template] in impacts:
        if len(task_templates_to_recommend) + len(incomplete_tasks) == NUMBER_OF_TASKS_AT_ONE_TIME:
            break
        
        is_already_in_incomplete_tasks = False
        for incomplete_task in incomplete_tasks:
            if incomplete_task.template_id == task_template.id:
                is_already_in_incomplete_tasks = True
                break
        
        if not is_already_in_incomplete_tasks:
            task_templates_to_recommend.append(task_template)
    return task_templates_to_recommend

def recommend_tasks(question_responses, all_task_templates, incomplete_tasks, completed_tasks):
    if len(incomplete_tasks) == NUMBER_OF_TASKS_AT_ONE_TIME:
        return []

    impacts = get_sorted_impacts(question_responses, all_task_templates, incomplete_tasks, completed_tasks)
    task_templates_to_recommend = get_task_templates_to_recommend(impacts, incomplete_tasks)

    return task_templates_to_recommend