from google import genai
from google.genai import types
from PIL import Image
import io

client = genai.Client(api_key='AIzaSyAcV3sUghLeYwJWUvQddQhWedycAWTr_i4')

models_to_test = [
    'gemini-3.1-pro-preview',
    'gemini-3-pro-image-preview',
    'gemini-3.1-flash-image-preview'
]

img = Image.open('input_test.png')

for model_id in models_to_test:
    try:
        print(f"Testing {model_id}...")
        response = client.models.generate_content(
            model=model_id,
            contents=[img, 'make this look like a digital painting'],
            config=types.GenerateContentConfig(
                response_modalities=['IMAGE']
            )
        )
        print(f"Success with {model_id}")
    except Exception as e:
        print(f"Error with {model_id}: {e}")
