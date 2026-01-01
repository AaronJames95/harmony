#GOAL: print something currently being written in from RealtimeSTT import AudioToTextRecorder

def process_text(text):
    print(f"Transcribed: {text}")

if __name__ == '__main__':
    # 'tiny' is fastest for real-time testing
    recorder = AudioToTextRecorder(model="tiny", language="en")
    
    print("Say something...")
    while True:
        recorder.text(process_text)