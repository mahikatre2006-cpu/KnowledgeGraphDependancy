# Phase 1 Audit Report

## 1. Duplicate subjects
**Status: FAIL** (16 issues)
* Course codes in >1 PDF: CSC402, CSC401, CSL401, CSC403, CSL405, CSL403, CSC405, CSC404
* Semester mismatches:
  - CSC402 in be_computer-engineering_second-year-se-semester-3-rev-2019-c-scheme.pdf
  - CSC405 in be_computer-engineering_second-year-se-semester-3-rev-2019-c-scheme.pdf
  - CSC404 in be_computer-engineering_second-year-se-semester-3-rev-2019-c-scheme.pdf
  - CSC401 in be_computer-engineering_second-year-se-semester-3-rev-2019-c-scheme.pdf
  - CSL403 in be_computer-engineering_second-year-se-semester-3-rev-2019-c-scheme.pdf
  - CSL401 in be_computer-engineering_second-year-se-semester-3-rev-2019-c-scheme.pdf
  - CSC403 in be_computer-engineering_second-year-se-semester-3-rev-2019-c-scheme.pdf
  - CSL405 in be_computer-engineering_second-year-se-semester-3-rev-2019-c-scheme.pdf

## 2. Empty or tiny subjects
**Status: FAIL** (14 subjects)
* Samples:
  - CSC402 (7 topics) [header-only/extraction miss]
  - CSC403 (5 topics) [header-only/extraction miss]
  - CSC302 (6 topics) [header-only/extraction miss]
  - CSC601 (6 topics) [header-only/extraction miss]
  - CSC402 (7 topics) [header-only/extraction miss]
  - CSL401 (5 topics) [lab/project]
  - CSL403 (7 topics) [lab/project]
  - CSC303 (7 topics) [header-only/extraction miss]
  - CSL405 (7 topics) [lab/project]
  - CSC403 (5 topics) [header-only/extraction miss]

## 3. Reference leakage
**Status: PASS** (0 topics leaked)

## 4. Over-dropping
**Status: FAIL** (151 topics over-dropped)
* Samples (topics dropped because they hit length or author/publisher filters but contain tech words):
  - [Length] CSC503: 3.2 Medium Access Control sublayer Channel Allocation problem, Multiple access Protocol( Aloha, Carrier Sense Multiple Access (CSMA/CD)
  - [Length] CSC301: 4.1 Function f(z)of complex variable, Limit, Continuity and Differentiability off(z), Analytic function: Necessary and sufficient conditions for f(z) to be analytic (without proof).
  - [Length] CSL405: 4.1 Graphical User interface, Networking in Python, Python database connectivity, Introduction to Django
  - [Length] CSC604: 5.1 Gray Level Transformations, Zero Memory Point Operations,
  - [Length] CSC602: 5.1 Network security basics: TCP/IP vulnerabilities (Layer wise), Network Attacks: Packet Sniffing, ARP spoofing, port scanning, IP spoofing
  - [Length] CSL405: 2.1 Files in Python, Directories, Building Modules, Packages, Text Processing, Regular expression in python.
  - [Length] CSC404: 4.2 Virtual Memory: Demand Paging, Page Replacement Strategies: FIFO, Optimal, LRU, Thrashing
  - [Length] CSC602: 2.3 Symmetric Key Distribution: KDC, Needham-schroeder protocol. Kerberos: Kerberos Authentication protocol, Symmetric key agreement: Diffie Hellman, Public key Distribution: Digital Certificate: X.509, PKI
  - [Length] CSC404: 3.3 Principles of Deadlock: Conditions and Resource, Allocation Graphs, Deadlock Prevention, Deadlock Avoidance: Banker’s Algorithm, Deadlock Detection and Recovery, Dining Philosophers Problem.
  - [Length] CSC402: 4.1 General Method, Multistage graphs, Single source shortest path: Bellman Ford Algorithm All pair shortest path: Floyd Warshall Algorithm, Assembly-line scheduling Problem0/1 knapsack Problem, Travelling Salesperson problem, Longest common subsequence

## 5. Merged/malformed topics
**Status: FAIL** (234 malformed topics found)
* Samples:
  - [>100 chars] CSC503: Congestion control algorithms: Open loop congestion control,...
  - [>100 chars] CSL304: Exception handling using try, catch, finally, throw and thro...
  - [>100 chars] CSC502: Software Engineering-process framework, the Capability Matur...
  - [>100 chars] CSC801: Web Browser Forensics, Google chrome, Other web browser inve...
  - [>100 chars] CSC501: Context Free Grammars (CFG) Definition, Sentential forms, Le...
  - [>100 chars] CSC604: Linear Convolution formulation for 1-D signal (without mathe...
  - [>100 chars] CSC404: Uniprocessor Scheduling-Types: Preemptive and Non-preemptive...
  - [>100 chars] CSC801: Optimization Learning with backpropagation, Learning Paramet...
  - [>100 chars] CSC303: Introduction, Graph Terminologies, Representation of Graph, ...
  - [>100 chars] CSC702: Introduction to Information Retrieval, Basic Concepts, Infor...

## 6. Sem 7-8 boundaries
**Status: FAIL** (1 subject out of boundary)
* CSC702 has 107 topics. Found codes in span: ['CSC801', 'CSL702', 'CSC701', 'CSL801', 'CSL701', 'CSP801', 'CSP701']

## 7. Missing theory courses
**Status: PASS** (0 missing theory courses)

## 8. Granularity (IT vs COMPS)
**Status: INFO**
* COMPS topics/subject: min=5, median=12.0, max=107
* IT topics/subject: min=3, median=5.5, max=16

## 9. Review files
**Status: FAIL** (1 error)
* extraction_check.csv column mismatched during validation (headers are pdf,page,extracted_topics,human_ok instead of PDF_Name)

### Final Audit Summary
| Check                          | Status | Count |
|--------------------------------|--------|-------|
| 1. Duplicate subjects          | FAIL   | 16    |
| 2. Empty or tiny subjects      | FAIL   | 14    |
| 3. Reference leakage           | PASS   | 0     |
| 4. Over-dropping               | FAIL   | 151   |
| 5. Merged/malformed topics     | FAIL   | 234   |
| 6. Sem 7-8 boundaries          | FAIL   | 1     |
| 7. Missing theory courses      | PASS   | 0     |
| 8. Granularity                 | INFO   | 0     |
| 9. Review files                | FAIL   | 1     |
