import os

def deliver_transcript(markdown_text, original_filename):
    """
    Handles the final output of the AI pipeline.
    """
    output_dir = os.path.join(os.path.dirname(__file__), "transcripts")
    os.makedirs(output_dir, exist_ok=True)
    
    file_name = f"{original_filename}.md"
    save_path = os.path.join(output_dir, file_name)
    
    with open(save_path, "w", encoding="utf-8") as f:
        f.write(markdown_text)
    
    print(f"📧 Transcript delivered to: {save_path}")
    # You can add your email logic here later!