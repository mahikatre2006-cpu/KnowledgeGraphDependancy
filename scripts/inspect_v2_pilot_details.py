import json
import re
import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')

df_v2 = pd.read_csv("DATA/review/extraction_pilot_v2.csv")

print("=" * 90)
print("AUDIT & INSPECTION OF EXTRACTION PILOT V2 (196 ROWS)")
print("=" * 90)

print(f"Total Rows: {len(df_v2)}")
print(f"Columns: {list(df_v2.columns)}")
print(f"human_ok strictly blank: {bool((df_v2['human_ok'].isna() | (df_v2['human_ok'] == '')).all())}")

print("\n--- Per-Subject Summary ---")
for course in ["ITC501", "CSC303", "2113112"]:
    cdf = df_v2[df_v2["course_code"].astype(str) == course]
    gate_pass = 8 <= len(cdf) <= 60
    print(f"\nCourse {course} ({cdf['title'].iloc[0]}):")
    print(f"  Total Topics Extracted: {len(cdf)} | Quality Gate [8-60]: {'PASS' if gate_pass else 'FAIL'} ({len(cdf)} topics)")
    
    # Module distribution
    mod_counts = cdf.groupby("unit", sort=False).size()
    for mod, c in mod_counts.items():
        m_pass = c >= 3
        print(f"    {mod:<45} : {c:>2} topics [{'OK' if m_pass else 'FAIL (<3)'}]")

print("\n" + "=" * 90)
print("SPECIFIC CONCEPT SPLITTING CHECKS (TARGETED PROMPT VERIFICATION)")
print("=" * 90)

# Check target splits:
# 1. HTTP and HTTPS
itc = df_v2[df_v2["course_code"] == "ITC501"]
http_topics = itc[itc["topic_name"].str.contains("HTTP", case=False)]["topic_name"].tolist()
print(f"1. HTTP/HTTPS split in ITC501: {http_topics}")

# 2. Promises and Fetch
promise_fetch = itc[itc["topic_name"].str.contains("Promise|Fetch|Client-server", case=False)]["topic_name"].tolist()
print(f"2. Promises/Fetch/Client-server in ITC501: {promise_fetch}")

# 3. Forms and Events
forms_events = itc[itc["topic_name"].str.contains("Form|Event", case=False)]["topic_name"].tolist()
print(f"3. Forms/Events in ITC501: {forms_events}")

# 4. Linear Search / Binary Search in CSC303
csc = df_v2[df_v2["course_code"] == "CSC303"]
searches = csc[csc["topic_name"].str.contains("Search|Hash", case=False)]["topic_name"].tolist()
print(f"4. Search/Hashing in CSC303: {searches}")

# 5. Walk / Path / Circuit in 2113112
dmath = df_v2[df_v2["course_code"] == "2113112"]
graphs = dmath[dmath["topic_name"].str.contains("Walk|Path|Circuit|Connected", case=False)]["topic_name"].tolist()
print(f"5. Walk/Path/Circuit/Connected in 2113112: {graphs}")

# 6. Algebraic structures in 2113112
algebra = dmath[dmath["topic_name"].str.contains("Group|Monoid|Ring|Field", case=False)]["topic_name"].tolist()
print(f"6. Algebraic structures in 2113112: {algebra}")

