from concurrent.futures import ThreadPoolExecutor
from scene import create_video_for_scene
import moviepy.editor as mp
from openai import OpenAI
import moviepy.editor as mp


def _run_io_tasks_in_parallel(tasks):
    media_list = []
    with ThreadPoolExecutor() as executor:
        running_tasks = [executor.submit(task) for task in tasks]
        for running_task in running_tasks:
            result = running_task.result()
            if not result:
                continue
            if hasattr(result, "__len__"):
                media_list = media_list + result
            else:
                media_list.append(result)
    return media_list    

def _wrapper_func(scene):
    return lambda: create_video_for_scene(scene)

def generate(scenes):
    print(scenes)
    task_list = []
    for scene in scenes:
        task = _wrapper_func(scene)
        task_list.append(task)
    print ("task_list", task_list)
    media_list = _run_io_tasks_in_parallel(task_list)
    print(media_list)
    final_clip = mp.concatenate_videoclips(media_list, method='chain')
    result_path = "./video.mp4"
    final_clip.write_videofile(
        result_path,
        audio_codec='aac',
        codec="libx264",
        fps=24,
        threads=100,
        logger=None,
        verbose=False,
        preset='medium'
    )
    return result_path

def get_story_prompt(user_prompt):
    prompt = f'''
        Write a viral short story for the given topic with great hook under 150 words . 

        Topic: {user_prompt}.
        Story:
    '''
    return prompt

def get_scenes_prompt(user_prompt):
    prompt = f'''
For the given text, construct many scenes which include voiceover text and image description.
Voiceover is the sentence from the given text.
Image is the field that describes a detailed visuals for Voiceover field in English.

Example Text:
  Fascinating facts about the Roman Empire during its peak, the Roman Empire encompassed merely 12% of the global population, making it a relatively modest empire in terms of its size compared to others throughout history.

Example Output:
Scene 1:
Voiceover: Fascinating facts about the Roman Empire during its peak.
Image: Roman Empire.

Scene 2:
Voiceover: the Roman Empire encompassed merely 12% of the global population
Image: Many Roman people from Roman Empire standing

Scene 3:
Voiceover: making it a relatively modest empire in terms of its size compared to others throughout history.
Image: Historians studying Roman Empire


Text: 
  {user_prompt}

Output:
    '''
    return prompt

    return prompt

def _use_openai(prompt):
    openai_client = OpenAI()
    response = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{
            "role": "user",
            "content": prompt
        }]
    )
    return response.choices[0].message.content

def _story_to_scenes(story):
    prompt = get_scenes_prompt(story)    
    scenes = _use_openai(prompt)
    return scenes

def _generate_story(topic):
    prompt = get_story_prompt(topic)
    story = _use_openai(prompt)
    return story

def _scenes_to_json(scenes):
    voiceovers = []
    images = []
    for line in scenes.split("\n"):
        if line.startswith("Voiceover:"):
            voiceovers.append(line.replace("Voiceover:", "").strip())
    for line in scenes.split("\n"):
        if line.startswith("Image:"):
            images.append(line.replace("Image:", "").strip())
    array_scenes = []
    for i, _ in enumerate(images):
        array_scenes.append({
            "voiceover": voiceovers[i],
            "image": images[i]
        })
    return array_scenes

def _generate_scenes(user_prompt):
    story = _generate_story(user_prompt)
    print("story", story)
    scenes = _story_to_scenes(story)
    print("scenes", scenes)
    array_scenes = _scenes_to_json(scenes)
    return array_scenes

def start(prompt):
    scenes = _generate_scenes(prompt)
    video_path = generate(scenes)
    print (video_path)
    return True


start("Story about Batman")