import os
from pptx import Presentation

def extract_pptx_data(data_dir):
    """Extract data from all PowerPoint (.pptx) files in the specified directory."""
    all_ppt_data = {}

    for file_name in os.listdir(data_dir):
        if file_name.endswith(".pptx"):
            file_path = os.path.join(data_dir, file_name)
            try:
                prs = Presentation(file_path)
                slides_text = []
                for slide in prs.slides:
                    text = []
                    for shape in slide.shapes:
                        if shape.has_text_frame:
                            for p in shape.text_frame.paragraphs:
                                if p.text.strip():
                                    text.append(p.text.strip())
                    if text:
                        slides_text.append("\n".join(text))
                all_ppt_data[file_name] = slides_text
            except Exception as e:
                print(f"Error processing {file_name}: {e}")

    return all_ppt_data
