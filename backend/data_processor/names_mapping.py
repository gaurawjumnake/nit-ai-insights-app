import pandas as pd
from rapidfuzz import process, fuzz
import numpy as np
from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

projects_df = pd.read_csv("backend/data_processor/data/Account Status Summary.csv")   
print(projects_df.columns)
print(projects_df["account_name"].info())
matched_df = pd.read_excel("backend/data_processor/data/rev_data.xlsx")         
print(matched_df.columns)

projects_df["account_name"].drop_duplicates(inplace=True)
print(projects_df["account_name"].info())

projects_df["name_clean"] = projects_df["account_name"].fillna("").str.lower().str.strip()
matched_df["name_clean"] = matched_df["name"].fillna("").str.lower().str.strip()
data = list(projects_df[["name_clean", "project_name"]].itertuples(index=False, name=None))

account_names = [i[0] for i in data]
account_embeddings = model.encode(account_names, normalize_embeddings=True)

def hybrid_match(query, account_embeddings, account_names, top_k=1):
    if not query:
        return None, 0, None
    query_emb = model.encode([query], normalize_embeddings=True)
    semantic_scores = util.cos_sim(query_emb, account_embeddings)[0].cpu().numpy()
    fuzzy_scores = np.array([fuzz.token_sort_ratio(query, candidate) / 100 
                             for candidate in account_names])
    hybrid_scores = 0.7 * semantic_scores + 0.3 * fuzzy_scores
    best_idx = np.argmax(hybrid_scores)
    return account_names[best_idx], hybrid_scores[best_idx], best_idx, data[best_idx][-1]

matched_df["project_name"] = matched_df["name_clean"].apply(lambda x: hybrid_match(x, account_embeddings, account_names)[-1])

matched_df.to_excel("matched_results.xlsx", index=False)

print("Matching complete. Output saved to matched_results.xlsx")



