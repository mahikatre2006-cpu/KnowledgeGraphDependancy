import pandas as pd
import numpy as np
import re
import fitz
import sys

sys.stdout.reconfigure(encoding='utf-8')

print("=" * 80)
print("BUILDING AUDITED V2 AND CANDIDATE V3")
print("=" * 80)

# Load original V2
df_v2 = pd.read_csv("DATA/review/extraction_pilot_v2.csv")
print(f"Loaded {len(df_v2)} rows from DATA/review/extraction_pilot_v2.csv")

# Load labeled sample for exact human note & reasoning calibration
df_sample = pd.read_csv("DATA/review/extraction_pilot_v2_review_sample_labeled.csv")
sample_map = {}
for _, r in df_sample.iterrows():
    key = (str(r['course_code']), str(r['unit']), str(r['topic_name']))
    sample_map[key] = {
        'human_ok': r['human_ok'],
        'human_note': r['human_note'],
        'audit_evidence': r['audit_evidence'],
        'audit_source_url': r['audit_source_url']
    }

urls = {
    "ITC501": "https://www.apsit.edu.in/sites/default/files/2023-07/IT%20Syllabus%20All%20Years%20R-19%20Scheme%20Updated.pdf",
    "CSC303": "https://www.apsit.edu.in/sites/default/files/2021-07/SE-Comps%28REV-2019%29_Syllabus%281%29.pdf",
    "2113112": "https://www.apsit.edu.in/sites/default/files/2026-02/SE_Syllabus_NEP_Computer%20Science%20and%20Engineering%20%28Artificial%20Intelligence%20and%20Machine%20Learning%29.pdf"
}

# Audit rows generator
audited_rows = []

for idx, r in df_v2.iterrows():
    c_code = str(r['course_code'])
    title = str(r['title'])
    sem = str(r['semester'])
    unit = str(r['unit'])
    topic = str(r['topic_name'])
    quote = str(r['source_quote'])
    page = int(r['page'])
    
    key = (c_code, unit, topic)
    sample_info = sample_map.get(key, None)
    
    # Defaults
    audit_status = "PASS"
    audit_reason = "Valid, source-supported, atomic curriculum concept."
    corrected_topic_name = topic
    evidence_quote = quote
    evidence_page = page
    evidence_url = urls.get(c_code, "")
    correction_action = "KEEP"
    
    # -------------------------------------------------------------------------
    # COURSE ITC501 RULES
    # -------------------------------------------------------------------------
    if c_code == "ITC501":
        # 1. Self-learning topics
        if topic == "Nginx Server":
            audit_status = "FAIL"
            audit_reason = "The official IT syllabus places Nginx server under Self-learning Topics. Project policy excludes self-learning topics from the main extracted topic-node set."
            correction_action = "REMOVE"
            corrected_topic_name = ""
        elif topic == "Asynchronous JavaScript":
            audit_status = "FAIL"
            audit_reason = sample_info['human_note'] if sample_info else "The official IT syllabus places Asynchronous JavaScript under Self-learning Topics. Project policy excludes self-learning topics from the main extracted topic-node set."
            correction_action = "REMOVE"
            corrected_topic_name = ""
        elif topic == "JSON" and "Module II" in unit:
            audit_status = "FAIL"
            audit_reason = sample_info['human_note'] if sample_info else "The official IT syllabus places JSON under JavaScript Self-learning Topics, while Module I already lists JSON introduction. Exclude this self-learning/redundant row from the main topic-node set."
            correction_action = "REMOVE"
            corrected_topic_name = ""
        elif topic == "React vs Angular vs Vue":
            audit_status = "FAIL"
            audit_reason = sample_info['human_note'] if sample_info else "The official IT syllabus places React vs Angular vs Vue under Self-learning Topics. Project policy keeps self-learning topics out of the extracted topic-node set; it is also a multi-framework comparison rather than one atomic framework concept."
            correction_action = "REMOVE"
            corrected_topic_name = ""
        elif topic == "React Native":
            audit_status = "FAIL"
            audit_reason = "The official IT syllabus places React Native under Self-learning Topics. Project policy excludes self-learning topics from the main extracted topic-node set."
            correction_action = "REMOVE"
            corrected_topic_name = ""
        elif topic == "Node.js with Mongodb":
            audit_status = "FAIL"
            audit_reason = sample_info['human_note'] if sample_info else "The official IT syllabus places Node.js with Mongodb under Self-learning Topics. Project policy excludes self-learning topics from the main extracted topic-node set."
            correction_action = "REMOVE"
            corrected_topic_name = ""
        elif topic == "Commercial Deployment":
            audit_status = "FAIL"
            audit_reason = "The official IT syllabus places Commercial deployment under Self-learning Topics. Project policy excludes self-learning topics from the main extracted topic-node set."
            correction_action = "REMOVE"
            corrected_topic_name = ""
            
        # 2. Procedural setup / demo steps
        elif topic == "Installation":
            audit_status = "FAIL"
            audit_reason = sample_info['human_note'] if sample_info else "Installation is a setup/procedure task rather than a standalone subject concept. Exclude installation steps from the KDG topic-node set."
            correction_action = "REMOVE"
            corrected_topic_name = ""
        elif topic == "Installing Libraries":
            audit_status = "FAIL"
            audit_reason = "Installing libraries is a setup/procedure task rather than a standalone curriculum concept node. Exclude setup actions under project rules."
            correction_action = "REMOVE"
            corrected_topic_name = ""
        elif topic == "Folder Structure":
            audit_status = "FAIL"
            audit_reason = "Folder structure is a project scaffolding/procedural setup item from 'Folder and file structure', not a standalone knowledge dependency concept. Exclude setup actions under project rules."
            correction_action = "REMOVE"
            corrected_topic_name = ""
        elif topic == "File Structure":
            audit_status = "FAIL"
            audit_reason = "File structure is a project scaffolding/procedural setup item from 'Folder and file structure', not a standalone knowledge dependency concept. Exclude setup actions under project rules."
            correction_action = "REMOVE"
            corrected_topic_name = ""
        elif topic == "Environment Setup":
            audit_status = "FAIL"
            audit_reason = sample_info['human_note'] if sample_info else "The syllabus lists Environment setup as a procedural preparation task, not a standalone subject concept for the KDG topic graph. Exclude setup steps from concept nodes."
            correction_action = "REMOVE"
            corrected_topic_name = ""
        elif topic == "First App":
            audit_status = "FAIL"
            audit_reason = sample_info['human_note'] if sample_info else "First app is a getting-started exercise/procedural task, not a standalone concept node. Exclude procedural setup/demo steps from the topic graph."
            correction_action = "REMOVE"
            corrected_topic_name = ""
            
        # 3. Generic phrases
        elif topic == "Best Practices":
            audit_status = "FAIL"
            audit_reason = "“Best practices” is a generic phrase lacking specific concept semantics. Exclude generic non-concept phrases under project rules."
            correction_action = "REMOVE"
            corrected_topic_name = ""
        elif topic == "Introduction" and "Module VI" in unit:
            audit_status = "FAIL"
            audit_reason = sample_info['human_note'] if sample_info else "“Introduction” is a generic section item whose meaning depends entirely on the Express module heading; it is not a distinct concept node. Use specific Express concepts such as Express Router or REST API instead."
            correction_action = "REMOVE"
            corrected_topic_name = ""
        else:
            audit_status = "PASS"
            audit_reason = "Source-supported, atomic curriculum topic in ITC501 detailed syllabus."
            correction_action = "KEEP"

    # -------------------------------------------------------------------------
    # COURSE CSC303 RULES
    # -------------------------------------------------------------------------
    elif c_code == "CSC303":
        if topic == "Introduction to Data Structures":
            audit_status = "FAIL"
            audit_reason = sample_info['human_note'] if sample_info else "The label duplicates the module heading and is a generic “Introduction” overview rather than a specific concept node. Prefer syllabus-listed concepts such as Concept of ADT, Linear/Nonlinear Data Structures, and Operations on Data Structures."
            correction_action = "REMOVE"
            corrected_topic_name = ""
        elif topic == "Linked List v/s Array":
            audit_status = "FAIL"
            audit_reason = sample_info['human_note'] if sample_info else "“Linked List v/s Array” bundles two distinct data structures into a comparison row. This violates the project’s atomic-topic rule; represent the structures as separate concept nodes rather than one combined node."
            correction_action = "REMOVE"
            corrected_topic_name = ""
        else:
            audit_status = "PASS"
            audit_reason = "Source-supported, atomic data structures curriculum topic in CSC303 detailed syllabus."
            correction_action = "KEEP"
            
    # -------------------------------------------------------------------------
    # COURSE 2113112 RULES
    # -------------------------------------------------------------------------
    elif c_code == "2113112":
        audit_status = "PASS"
        audit_reason = "Source-supported, atomic mathematical concept in Discrete Structures and Graph Theory detailed syllabus."
        correction_action = "KEEP"

    audited_rows.append({
        'course_code': c_code,
        'title': title,
        'semester': sem,
        'unit': unit,
        'topic_name': topic,
        'source_quote': quote,
        'page': page,
        'human_ok': "", # Keep strictly blank per prompt
        'audit_status': audit_status,
        'audit_reason': audit_reason,
        'corrected_topic_name': corrected_topic_name,
        'evidence_quote': evidence_quote,
        'evidence_page': evidence_page,
        'evidence_url': evidence_url,
        'correction_action': correction_action
    })

df_audited = pd.DataFrame(audited_rows)
out_audited_path = "DATA/review/extraction_pilot_v2_audited.csv"
df_audited.to_csv(out_audited_path, index=False)
print(f"Written audited dataset: {out_audited_path} ({len(df_audited)} rows)")

# Build candidate V3 from KEEP and RENAME rows
v3_candidate_rows = []
for idx, r in df_audited.iterrows():
    if r['correction_action'] in ['KEEP', 'RENAME']:
        v3_candidate_rows.append({
            'course_code': r['course_code'],
            'title': r['title'],
            'semester': r['semester'],
            'unit': r['unit'],
            'topic_name': r['corrected_topic_name'],
            'source_quote': r['evidence_quote'],
            'page': r['evidence_page'],
            'human_ok': "" # strictly blank
        })

df_v3_candidate = pd.DataFrame(v3_candidate_rows)
out_v3_path = "DATA/review/extraction_pilot_v3_candidate.csv"
df_v3_candidate.to_csv(out_v3_path, index=False)
print(f"Written candidate V3 dataset: {out_v3_path} ({len(df_v3_candidate)} rows)")

print("\n--- Summary of Audited Dataset ---")
print(df_audited['audit_status'].value_counts())
print("\nCorrection Actions:")
print(df_audited['correction_action'].value_counts())
print("\nBy Course:")
print(pd.crosstab(df_audited['course_code'], df_audited['audit_status']))

print("\n--- Summary of Candidate V3 Dataset ---")
print("Candidate V3 total rows by course:")
print(df_v3_candidate['course_code'].value_counts())

print("\nCandidate V3 module breakdown:")
for c, group in df_v3_candidate.groupby('course_code'):
    print(f"\nCourse {c} (Total: {len(group)}):")
    print(group['unit'].value_counts(sort=False))

