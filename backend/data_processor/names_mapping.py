import pandas as pd
from rapidfuzz import process, fuzz
import numpy as np
from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

projects_df = pd.read_csv("backend/data_processor/data/revenue_master_rows.csv")       
matched_df = pd.read_excel("backend/data_processor/data/matched_results.xlsx")         

projects_df["name_clean"] = projects_df["project_name"].fillna("").str.lower().str.strip()
matched_df["name_clean"] = matched_df["updated_names"].fillna("").str.lower().str.strip()
data = list(projects_df[["name_clean", "id"]].itertuples(index=False, name=None))
projects_names = [i[0] for i in data]
project_embeddings = model.encode(projects_names, normalize_embeddings=True)

def hybrid_match(query, project_embeddings, project_names, top_k=1):
    if not query:
        return None, 0, None
    query_emb = model.encode([query], normalize_embeddings=True)
    semantic_scores = util.cos_sim(query_emb, project_embeddings)[0].cpu().numpy()
    fuzzy_scores = np.array([fuzz.token_sort_ratio(query, candidate) / 100 
                             for candidate in project_names])
    hybrid_scores = 0.7 * semantic_scores + 0.3 * fuzzy_scores
    best_idx = np.argmax(hybrid_scores)
    return project_names[best_idx], hybrid_scores[best_idx], best_idx, data[best_idx]


matched_df["updated_names"] = matched_df["name_clean"].apply(lambda x: hybrid_match(x, project_embeddings, projects_names)[0])


matched_df.to_excel("matched_results.xlsx", index=False)

print("Matching complete. Output saved to matched_results.xlsx")



