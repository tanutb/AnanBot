### DISCORD TOKEN ###
DISCORD_TOKEN = '<API_TOKEN>'

######## MODEL CONFIG ########
OCR_LANGUAGES = ['en']
CLIP_MODEL_NAME = "openai/clip-vit-base-patch32"
MODEL_NAME = 'openbmb/MiniCPM-Llama3-V-2_5-int4'
CHROMA_DB_PATH = "./memories/chroma.db"
COLLECTION_NAME = "v02haha"
HISTORY_MAXLEN = 100

## API for the model
MODEL_API = 'http://127.0.0.1:8119/chat' 



## CONTEXT_LENGTH_IMAGE is the number of previous images that will be used to generate the response
CONTEXT_LENGTH_IMAGE = 1
CONTEXT_LENGTH_TEXT = 5

## NAME is the name of the character that the model will be trained to generate responses for
NAME = 'NuAnantachai'

## MEMORY_PROMPT is the prompt that will be used to generate the memory for the conversation
MEMORY_PROMPT = '''\nGiven only the information above, what are 3 most salient high level questions we can answer about the subjects in the conversation? Separate each question and answer pair with \"{qa}\", \"{answer}\" respectively
For example, DO NOT COPY MY EXAMPLES 
- "{qa}What is the meaning of life? {answer}The meaning of life is 42".
- "{qa} What's capital of Thailand? {answer} Bangkok".
, and only output the question and answer, no explanations.'''


## SYSTEM_PROMPT is the prompt that will be used to generate the response for the character "NuAnantachai"
SYSTEM_PROMPT = '''Continue the chat dialogue below. Write only a single reply for the character's name "NuAnantachai" without quotes. Answer in not long sentance.
NuAnantachai is a character in the chat dialogue. This character is a human who is a professor. The character will answer questions with the rough personality and strong language.
This character is gay.
'''


THRESHOLD = 1
MEMORY_RECALL_COUNT = 2


# PROMPT for deciding if an image should be generated
IMAGE_DECISION_PROMPT = """\n\n
Based on the user's input, decide if an image needs to be generated.

If the user requests an image, respond with: {gen} followed by relevant keywords describing the image.
If no image is needed, respond with: {no}.
Do not include any additional text.
Examples:
USER: Can you show me a picture of a cat?
BOT: {gen} cat

USER: Generate an image with keywords: cat, dog, bird, girl, cute.
BOT: {gen} cat, dog, bird, girl, cute

USER: I don't need an image.
BOT: {no}

USER: Hello
BOT: {no}

"""


# Stable WebUI API
STABLE_WEBUI_API = "http://127.0.0.1:7860/sdapi/v1/txt2img"
NEGATIVE_PROMPTS = '''
modern, recent, old, oldest, cartoon, graphic, text, painting, crayon, graphite, abstract, glitch, 
deformed, mutated, ugly, disfigured, long body, lowres, bad anatomy, 
(bad hands, missing fingers, extra digit, fewer digits:1.2), cropped, 
very displeasing, (worst quality, bad quality:1.2), bad anatomy, sketch, 
jpeg artifacts, signature, watermark, username, simple background, conjoined, ai-generated
'''