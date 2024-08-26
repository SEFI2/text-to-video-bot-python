import os
from dotenv import load_dotenv
import boto3
import time
import moviepy.editor as mp
import json
from contextlib import closing
import random
from threading import Lock
from polly_voices import polly_voices
import copy

load_dotenv()

mutex = Lock()
counter = 0
def get_counter():
    global counter
    with mutex:
        counter += 1
        return counter

polly = boto3.client('polly',
                aws_access_key_id=os.environ['AWS_ACCESS_KEY'],
                aws_secret_access_key=os.environ['AWS_SECRET_KEY'],
                region_name=os.environ['AWS_S3_REGION'])

def _get_engine(engines):
    for engine in engines:
        if engine == 'neural':
            return engine
    return engines[0]

def _get_standard_text(text):
    pace = os.environ['pace']
    return f'''
        <speak> 
            <prosody rate="{pace}">
                <amazon:auto-breaths volume="x-loud" frequency="x-low">  
                    {text} 
                </amazon:auto-breaths> 
            </prosody> 
        </speak>'''

def _get_input_text(text):
    pace = os.environ['pace']
    return f'''
        <speak>
            <prosody rate="{pace}">
                {text} 
            </prosody>            
        </speak>'''

def _synthesize_speech(text, output_format, voice_obj, **extra_params):
    engine = _get_engine(voice_obj['SupportedEngines'])
    if engine == 'standard':
        input_text = _get_standard_text(text)
    else:
        input_text = _get_input_text(text)

    response = polly.synthesize_speech(
        TextType='ssml',
        Text=input_text,
        OutputFormat=output_format,
        VoiceId=voice_obj['Id'],
        Engine=engine,
        **extra_params
    )
    return response

def _transcribe_audio_polly(text, voice_obj):
    response = _synthesize_speech(
        text,
        "json",
        voice_obj,
        SpeechMarkTypes=["word"]
    )

    content = response['AudioStream'].read()
    content = content.decode("utf-8")
    lines = content.split('\n')

    converted = []
    for line in lines:
        try:
            loaded = json.loads(line)
            converted.append(loaded)
        except ValueError:
            continue

    result = []
    sz = len(converted)
    i = 0
    while i < sz:
        start = round(converted[i]['time'] / 1000, 3)
        if i == sz - 1:
            end = round(converted[i]['time'] / 1000, 3) + 2
            result.append(
                ([start, end], converted[i]['value'])
            )
            break
        else:
            end = round(converted[i + 1]['time'] / 1000, 3)
            result.append(
                ([start, end], converted[i]['value'])
            )
            i += 1
    return result

voice = None
def get_voice_obj():
    global voice
    if voice:
        return voice

    voice_name = os.environ['voice']
    for s in polly_voices:
        if s['Name'] == voice_name:
            voice = copy.deepcopy(s)
            print("voice", voice_name)
            break
    return voice

def generate_audio_polly(text):
    voice_obj = get_voice_obj()
    response = _synthesize_speech(
        text,
        "mp3",
        voice_obj)

    audio_stream = response["AudioStream"]
    with closing(audio_stream) as stream:
        audio_file = f'audio_{get_counter()}.mp3'
        with open(audio_file, "wb") as file:
            file.write(stream.read())
        return audio_file, _transcribe_audio_polly(text, voice_obj)