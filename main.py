import cursor_key_screen
import transcript_listener
#import navi

def main():
    print("Hello, World!")
    cursor_key_screen.run()
    #navi.

def shema():
    OBSlistener()


if __name__ == "__main__":
    main()

    from overlay import OverlayWindow
from ingestor import Ingestor

app = QApplication([])
window = OverlayWindow()
logger = Ingestor()

# Connect the Overlay's signal to the Ingestor's function
window.text_received.connect(logger.ingest)

window.show()
app.exec()