import pandas as pd
import json
from rapidfuzz import fuzz, process
from confidenceLabel import confidence_label
from specialVersionMatching import find_best_alternate_match
from normalization import normalize
import configparser

alternate_bias = 1
extreme_bias = 1

alternate = []

config = configparser.ConfigParser()
config.read('resources/config.cfg')
with open(config['file_paths']['alternate_file_path'], encoding='utf-8') as f:
    alternate = json.load(f)

def is_extreme(title: str) -> bool:
    if 'extreme' in title:
        return True, title.replace('extreme', '')
    return False, title

def is_alternate(title: str) -> bool:
    for alt in alternate:
        if alt.lower() in title.lower():
            title = title.lower().replace(alt.lower(), '')
            return True, title, alt
    return False, title, "None"

def find_best_match(
    input_string: str,
    df: pd.DataFrame,
    extreme: bool = False,
) -> dict:
    alternate = "None"
    query = normalize(input_string)
    choices_title = df['songs_normalized']
    choices_both = df["combined_norm"]
    choices_both_inv = df["combined_norm_inv"]

    if extreme:
        mask = df["extreme"] == True
        alternate = "Extreme"
    else:
        mask = df["extreme"] == False

    df_sub = df.loc[mask]
    idx_mask = [i for i, m in enumerate(mask) if m]
    choices_title_sub = [choices_title.iloc[i] for i in idx_mask]
    choices_both_sub  = [choices_both.iloc[i]  for i in idx_mask]
    choices_both_sub_inv  = [choices_both_inv.iloc[i]  for i in idx_mask]

    if not choices_title_sub:
        df_sub = df
        choices_title_sub = df['songs_normalized'].tolist()
        choices_both_sub  = df["combined_norm"].tolist()
        choices_both_sub_inv  = df["combined_norm_inv"].tolist()

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

    alternateBool, alt_input_string, alt = is_alternate(input_string)
    if alternateBool: 
        print(alt)
        best_alternate = find_best_alternate_match(alt_input_string, df, alternate=alt)
        if best_alternate["similarity"] > best_score:
            row = df.iloc[best_alternate["row_index"]]
            best_score = best_alternate["similarity"]
            best_conf = best_alternate["confidence"]
            alternate = alt

    elif not extreme:
        best_extreme = find_best_match(input_string, df, extreme=True)

        if best_extreme["similarity"] > best_score + 1:
            row = df.iloc[best_extreme["row_index"]]
            best_score = best_extreme["similarity"]
            best_conf = best_extreme["confidence"]
            alternate = "Extreme"

    return {
        "best_song": row["songName"],
        "best_artist": row["ContributingArtists"],
        "similarity": float(best_score),
        "confidence": best_conf,
        "row_index": int(row.name),
        "alternate": alternate
    }
