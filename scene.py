import replicate
import requests
import os

import random
import os
import moviepy.editor as mp
from threading import Lock
import time
from moviepy.video.tools.subtitles import SubtitlesClip, TextClip
import moviepy.video.compositing.transitions as transfx
from polly import generate_audio_polly
from dotenv import load_dotenv
import copy
from sdxl_styles import styles
from threading import Lock
import traceback

load_dotenv()

mutex = Lock()
counter = 0
def get_counter():
    global counter
    with mutex:
        counter += 1
        return counter

def _genereate_image_replicate(prompt):
    print("prompt", prompt)
    replicate_input = {
        "prompt": prompt,
        "width": int(os.environ['WIDTH']),
        "height": int(os.environ['HEIGHT']),
        "refine": "expert_ensemble_refiner",
        "scheduler": "K_EULER",
        "lora_scale": 0.6,
        "num_outputs": 1,
        "guidance_scale": 7.5,
        "apply_watermark": False,
        "high_noise_frac": 0.8,
        "negative_prompt": "",
        "prompt_strength": 0.8,
        "num_inference_steps": 25
    }

    replicate_url = replicate.run(
        "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
        input=replicate_input
    )

    response = requests.get(replicate_url[0])
    filename = f'replicate_{get_counter()}.jpg'
    with open(filename, 'wb') as f:
        f.write(response.content)
        return mp.ImageClip(filename)

def _apply_effects(clip):
    def zoomIn(clip):        
        return clip.resize(lambda t: 1 + t * 0.15)

    def slideInLeft(clip):
        return clip.fx(transfx.slide_in, 0.3, "left")

    def slideInRight(clip):
        return clip.fx(transfx.slide_in, 0.3, "right")

    def slideInBottom(clip):
        return clip.fx(transfx.slide_in, 0.3, "bottom")

    def slideInUp(clip):
        return clip.fx(transfx.slide_in, 0.3, "top")

    def fadeIn(clip):
        return clip.fadein(0.5)

    def slideOutLeft(clip):
        return clip.fx(transfx.slide_out, 0.3, "left")

    def slideOutRight(clip):
        return clip.fx(transfx.slide_out, 0.3, "right")

    def slideOutBottom(clip):
        return clip.fx(transfx.slide_out, 0.3, "bottom")

    def slideOutUp(clip):
        return clip.fx(transfx.slide_out, 0.3, "top")

    def fadeOut(clip):
        return clip.fadeout(0.2).set_position(("center", "center"))

    def noEffectOut(clip):
        return clip.set_position(("center", "center"))

    inEffects = [fadeIn]
    outEffects = [
        slideOutLeft,
        slideOutRight,
        slideOutBottom,
        slideOutUp,
        fadeOut,
        fadeOut,
        fadeOut,
        noEffectOut,
        noEffectOut,
        noEffectOut,
    ]

    inEffect = random.choice(inEffects)
    outEffect = random.choice(outEffects)

    return zoomIn(inEffect(outEffect(clip)))

def add_word_captions(subtitles, width):
    def _generate_captions(text):
        text_clip = TextClip(
            text.upper(),
            color="yellow",
            font="Bookman-DemiItalic",
            fontsize=150,
            kerning=-8,
            interline=-2,
            method='caption',
            align="center",
        )
        stroke_clip = TextClip(
            text.upper(),
            color="yellow",
            font="Bookman-DemiItalic",
            fontsize=150,
            kerning=-8,
            interline=-2,
            method='caption',
            align="center",
            stroke_color="black",
            stroke_width=40,
        )
        final_text = mp.CompositeVideoClip([stroke_clip, text_clip])
        return final_text

    return SubtitlesClip(subtitles, _generate_captions)

def start_generate_audio(text):
    audio_path, subtitles = generate_audio_polly(text)
    audio_clip = mp.AudioFileClip(audio_path)
    subtitles_clip = add_word_captions(subtitles, int(os.environ['WIDTH']))
    subtitles_clip = subtitles_clip.set_duration(audio_clip.duration)
    subtitles_clip = subtitles_clip.set_position(("center", "center"))
    return audio_clip, subtitles_clip


def main_logic(sentence, image_prompt):
    audio_clip, subtitles_clip  = start_generate_audio(sentence)

    # to avoid a bug with noisy sounds
    audio_clip = audio_clip.subclip(0, audio_clip.duration - 0.1)
    
    image_clip = _genereate_image_replicate(image_prompt)

    # do not change the order of below two lines
    image_clip = image_clip.set_duration(audio_clip.duration + 0.1)
    image_clip = image_clip.set_audio(audio_clip)
    
    # to make trembling effect less visible https://github.com/Zulko/moviepy/issues/183
    image_clip = image_clip.resize(height=int(os.environ['HEIGHT']) * 1.5)

    image_clip = _apply_effects(image_clip)

    if os.environ['caption'] == "yes":
        final_media = mp.CompositeVideoClip([image_clip, subtitles_clip])
    else:
        final_media = mp.CompositeVideoClip([image_clip])

    return final_media

def create_video_for_scene(scene):
    start_time = time.time()
    sentence = scene['voiceover']
    image_prompt = scene['image']
    final_media = main_logic(sentence, image_prompt)
    print(f'Scene was generated in {time.time() - start_time} seconds.')
    return final_media
