try:
    from transformers import CLIPImageProcessor
    print("Success: CLIPImageProcessor imported from transformers")
except ImportError as e:
    print(f"ImportError: {e}")

try:
    import transformers
    print(f"Transformers version: {transformers.__version__}")
    print(f"Transformers file: {transformers.__file__}")
except Exception as e:
    print(f"Error checking transformers: {e}")
