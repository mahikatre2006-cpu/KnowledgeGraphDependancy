import os
import sys
import json
import time
import random
from pathlib import Path
import pandas as pd
from google import genai
from google.genai import types
from google.genai.errors import APIError

project_root = Path(r"c:\Users\Siddhesh\Documents\KnowledgeGraphDependancy")

COMPS_KEYS = ['computer-engineering', 'syllabus-c prog', 'sem-v']
IT_KEYS = ['aiml', 'ai-ds', 'ai-ml', 'cse', 'information-technology', 'data-science', 'extc', 'a-i-ai-ds', '02 syllabus', 'professional', 'em syllabus']

def classify(s):
    sl = str(s).lower()
    if any(k in sl for k in COMPS_KEYS): return 'COMPS'
    if any(k in sl for k in IT_KEYS): return 'IT'
    return 'OTHER'

def main():
    print("Preparing data for labeling...")
    
    # 1. Read m1 candidates
    m1_df = pd.read_csv(project_root / "DATA" / "candidates" / "m1_candidate_pairs.csv", on_bad_lines='skip', engine='python')
    
    # Apply tags
    # 6.51N exclusion
    exc_mask = m1_df['source_syllabus'] == "6.51N-B.E.-Electrical-Computer-EngineeringSem-III-IV.pdf"
    m1_df.loc[exc_mask, 'branch'] = 'EXCLUDED_AMBIGUOUS'
    
    m1_df['branch'] = m1_df.apply(lambda row: 'EXCLUDED_AMBIGUOUS' if row.get('branch') == 'EXCLUDED_AMBIGUOUS' else classify(row['source_syllabus']), axis=1)
    
    # AIML cap
    aiml_mask = m1_df['source_syllabus'] == "6.9N-AIML.pdf"
    aiml_indices = m1_df[aiml_mask].index.tolist()
    random.seed(42)
    sampled_aiml = set(random.sample(aiml_indices, min(1500, len(aiml_indices))))
    
    m1_df['cap_tag'] = 'KEEP'
    m1_df.loc[aiml_mask, 'cap_tag'] = 'AIML_CAPPED'
    m1_df.loc[list(sampled_aiml), 'cap_tag'] = 'KEEP'
    
    # Print before/after counts
    print("\nm1_candidate_pairs.csv source counts (Before Cap & Exclude):")
    print(m1_df['source_syllabus'].value_counts())
    print("\nAIML Branch Tag:", classify("6.9N-AIML.pdf"))
    
    # Filter to IT + COMPS & KEEP
    valid_m1 = m1_df[(m1_df['branch'].isin(['IT', 'COMPS'])) & (m1_df['cap_tag'] == 'KEEP')].copy()
    
    print("\nValid m1 pairs by source (After Cap):")
    print(valid_m1['source_syllabus'].value_counts())
    
    # Save excluded tags back to m1? Not explicitly asked to overwrite the file entirely, 
    # but the prompt says: "Tag its 25 rows EXCLUDED_AMBIGUOUS in m1_candidate_pairs".
    # I will save the full dataframe back to keep the tag recorded.
    m1_df.to_csv(project_root / "DATA" / "candidates" / "m1_candidate_pairs.csv", index=False)
    
    # 2. Read MU COMPS new pairs
    mu_df = pd.read_csv(project_root / "DATA" / "candidates" / "mu_comp_eng_new_pairs.csv")
    mu_df['branch'] = 'COMPS'
    
    # Combine
    # Note: mu_df does not have suggested_label, so fill with 0 for sorting
    for df in [valid_m1, mu_df]:
        if 'suggested_label' not in df.columns:
            df['suggested_label'] = 0
            
    combined = pd.concat([valid_m1, mu_df], ignore_index=True)
    combined = combined.sort_values(by=['suggested_label', 'embedding_similarity'], ascending=[False, False]).reset_index(drop=True)
    combined['pair_id'] = combined.index
    
    print(f"\nTotal pairs for labeling: {len(combined)} (IT: {sum(combined['branch'] == 'IT')}, COMPS: {sum(combined['branch'] == 'COMPS')})")
    
    # 3. LLM Labeling Logic
    client = genai.Client()
    model_name = "gemini-2.5-flash"
    
    label_log_path = project_root / "DATA" / "labeling" / "label_log.json"
    progress_path = project_root / "DATA" / "labeling" / "progress.json"
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    
    prompt_tpl = """You are labeling prerequisite relationships between academic concepts.
For each pair, determine if concept_a is a prerequisite for concept_b in an engineering curriculum.
Respond ONLY with a JSON array containing EXACTLY these pairs. No markdown, no extra text.
Format:
[{"pair_id": <id>, "label": <0_or_1>, "confidence": <float_0_to_1>}]

Pairs to label:
%s
"""
    
    batch_size = 50
    batches = [combined[i:i+batch_size] for i in range(0, len(combined), batch_size)]
    
    # Load progress
    results = {}
    if progress_path.exists():
        with open(progress_path, "r") as f:
            results = json.load(f)
            # convert string keys to int
            results = {int(k): v for k, v in results.items()}
    
    start_batch = len(results) // batch_size
    print(f"Resuming from batch {start_batch}/{len(batches)}")
    
    for i in range(start_batch, len(batches)):
        batch_df = batches[i]
        pair_data = []
        for _, row in batch_df.iterrows():
            pair_data.append(f"pair_id: {row['pair_id']}, concept_a: {row['concept_a']}, concept_b: {row['concept_b']}, course: {row['course_name']}")
            
        prompt = prompt_tpl % "\n".join(pair_data)
        
        # Exponential backoff
        max_retries = 5
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                    ),
                )
                
                resp_json = json.loads(response.text)
                for item in resp_json:
                    pid = item["pair_id"]
                    results[int(pid)] = {"label": item["label"], "confidence": item["confidence"]}
                    
                # Save progress
                with open(progress_path, "w") as f:
                    json.dump(results, f)
                print(f"Batch {i+1}/{len(batches)} success.")
                break
            except Exception as e:
                sleep_time = 2 ** attempt
                print(f"Batch {i+1} failed (attempt {attempt+1}/{max_retries}): {e}. Retrying in {sleep_time}s...")
                time.sleep(sleep_time)
                if attempt == max_retries - 1:
                    print(f"Batch {i+1} failed completely. Saving progress and halting.")
                    sys.exit(1)
        
        time.sleep(1) # Base rate limit pause
        
    print("\nLabeling complete. Processing results...")
    
    # Merge results back to combined df
    combined['llm_label'] = combined['pair_id'].map(lambda pid: results.get(pid, {}).get("label"))
    combined['confidence'] = combined['pair_id'].map(lambda pid: results.get(pid, {}).get("confidence"))
    
    # Drop rows that failed to label (should be 0)
    combined = combined.dropna(subset=['llm_label', 'confidence'])
    
    low_conf = combined[combined['confidence'] < 0.70]
    high_conf = combined[combined['confidence'] >= 0.70]
    
    low_conf.to_csv(project_root / "DATA" / "labeling" / "low_confidence.csv", index=False)
    high_conf.to_csv(project_root / "DATA" / "labeling" / "llm_labeled.csv", index=False)
    
    with open(label_log_path, "w") as f:
        json.dump({
            "model": model_name,
            "prompt_template": prompt_tpl,
            "batch_count": len(batches),
            "total_labeled": len(high_conf),
            "total_excluded_low_conf": len(low_conf)
        }, f, indent=2)
        
    print(f"✅ Step 1: LLM Labeling finished.")
    print(f"   Labeled and kept (conf >= 0.70): {len(high_conf)}")
    print(f"   Excluded (low conf): {len(low_conf)}")

if __name__ == "__main__":
    main()
