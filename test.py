from utils.audio_processor import process_input 
from core.transcriber import transcribe_all 

source = "https://www.youtube.com/watch?v=818gGdKTB_U&list=PLxCzCOWd7aiEwaANNt3OqJPVIxwp2ebiT&index=28"

chunks = process_input(source)
print(transcribe_all(chunks))
