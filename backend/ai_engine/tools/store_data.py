import os
import json
from tools.app_logger import Logger
log = Logger()

def store_data_locally(data, input_path, output_path, file_type:str):
    try:
        basename = os.path.basename(input_path)
        fname = os.path.splitext(basename)[0]

        os.makedirs(output_path, exist_ok=True)
        out_fname = ""
        if file_type.lower() == "json":
            out_fname = os.path.join(output_path, f"{fname}.json")
            with open(out_fname, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        
        elif file_type.lower() == "txt":
            out_fname = os.path.join(output_path, f"{fname}.txt")
            with open(out_fname, "w", encoding="utf-8") as f:
                if isinstance(data, list):
                    f.write('\n'.join(str(item) for item in data))
                else:
                    f.write(str(data))
        else:
            log.log_error(f"Unsupported file type: {file_type}. Use 'json' or 'txt'")
        
        log.log_info(f"Data successfully saved to: {out_fname}")
        return out_fname
        
    except Exception as e:
        log.log_error(f"Error saving data: {e}")
        return None


# pdf_path = "research_papers/2506.18927v2.pdf"
# output_path = "extracted_pdf_data/embeddings"
# data =[ {"status":"scusses"}]

# store_data_locally(data, pdf_path, output_path, 'json')
