from google import genai
from google.genai import types
from PIL import Image
import io

client = genai.Client(api_key='AIzaSyBrla7MeU2C8jcH1VsmJa-yyD3KA6EKmUY')

try:
    img = Image.open('input_test.png')
    response = client.models.generate_content(
        model='gemini-2.5-flash-image',
        contents=[img, 'make this look like a digital painting'],
        config=types.GenerateContentConfig(
            response_modalities=['IMAGE']
        )
    )
    print("Success with gemini-2.5-flash-image")
except Exception as e:
    print(f"Error with gemini-2.5-flash-image: {e}")

try:
    img = Image.open('input_test.png')
    response = client.models.generate_content(
        model='nano-banana-pro-preview',
        contents=[img, 'make this look like a digital painting'],
        config=types.GenerateContentConfig(
            response_modalities=['IMAGE']
        )
    )
    print("Success with nano-banana-pro-preview")
except Exception as e:
    print(f"Error with nano-banana-pro-preview: {e}")
