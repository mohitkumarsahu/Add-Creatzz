from PIL import Image
import numpy as np

# Create a small noisy image
data = np.random.randint(0, 255, (128, 128, 3), dtype=np.uint8)
img = Image.fromarray(data)
img.save("input_test.png")
print("Created input_test.png")
