import pandas as pd
from normalization import normalize
from confidenceLabel import confidence_label
from rapidfuzz import fuzz, process

def find_best_alternate_match(
    input_string: str,
    df: pd.DataFrame,
    alternate: str,
) -> dict:
    
    query = normalize(input_string)
    choices_title = df['songs_normalized']
    choices_both = df["combined_norm"]
    choices_both_inv = df["combined_norm_inv"]

    mask = df["alternate"] == alternate

    idx_mask = [i for i, m in enumerate(mask) if m]
    df_sub = df.loc[mask]
    choices_title_sub = [choices_title.iloc[i] for i in idx_mask]
    choices_both_sub  = [choices_both.iloc[i]  for i in idx_mask]
    choices_both_sub_inv  = [choices_both_inv.iloc[i]  for i in idx_mask]

    if not choices_title_sub:
        return {"similarity": 0, "confidence": "low", "row_index": 0}

    best_title_norm, score_title, idx_title = process.extractOne(
        query,
        choices_title_sub,
        scorer=fuzz.ratio,
    )

    best_both_norm, score_both, idx_both = process.extractOne(
        query,
        choices_both_sub,
        scorer=fuzz.ratio,
    )

    best_both_norm_inv, score_both_inv, idx_both_inv = process.extractOne(
        query,
        choices_both_sub_inv,
        scorer=fuzz.ratio,
    )

    conf_title = confidence_label(score_title, query, best_title_norm)
    conf_both  = confidence_label(score_both,  query, best_both_norm)
    conf_both_inv  = confidence_label(score_both_inv,  query, best_both_norm_inv)

    order = {"low": 0, "medium": 1, "high": 2}

    if order[conf_title] > order[conf_both] and order[conf_title] > order[conf_both_inv]:
        best_score = score_title
        best_conf  = conf_title
        idx_sub    = idx_title
    elif order[conf_both] > order[conf_title] and order[conf_both] > order[conf_both_inv]:
        best_score = score_both
        best_conf  = conf_both
        idx_sub    = idx_both
    else:
        best_score = score_both_inv
        best_conf  = conf_both_inv
        idx_sub    = idx_both_inv

    row = df_sub.iloc[idx_sub]

    return {
        "similarity": best_score,
        "confidence": best_conf,
        "row_index": idx_mask[idx_sub],
    }