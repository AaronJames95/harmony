import os

# Set your absolute Linux path here
# Example: "/home/username/transcripts" or "/var/www/output"
DESTINATION = "/home/aharon/Desktop/2_Roots/Second Brain/vault-alpha/0_Sunlight" 

def deliver_transcript(markdown_text, original_filename):
    """
    Handles the final output of the AI pipeline.
    """
    # Use the destination variable; expanduser() allows you to use '~' in the path
    if DESTINATION:
        output_dir = os.path.expanduser(DESTINATION)
    else:
        output_dir = os.path.join(os.path.dirname(__file__), "transcripts")
    
    # Create the directory (and any parent directories) if they don't exist
    os.makedirs(output_dir, exist_ok=True)
    
    file_name = f"{original_filename}.md"
    save_path = os.path.join(output_dir, file_name)
    
    with open(save_path, "w", encoding="utf-8") as f:
        f.write(markdown_text)
    
    print(f"📧 Transcript delivered to: {save_path}")
    # You can add your email logic here later!