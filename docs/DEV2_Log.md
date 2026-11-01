# NIRMAAN Backend --- ML Risk Scoring & Validation

## Development and Git Workflow Log

**Repository:** [somil71/NIRMAAN](https://github.com/somil71/NIRMAAN)\
**Working branch:** `feature/ml-risk-validation`\
**Target branch:** `main`\
**Status:** Implementation committed and pushed; Pull Request not yet
created.

------------------------------------------------------------------------

## 1. Scope of Work

Reviewed and improved the backend machine-learning pipeline, focusing on
transaction graph analysis, suspicious-pattern detection, service
identification, risk scoring, typology classification, and transaction
tracing.

## 2. ML Implementation Changes

### 2.1 Graph Clustering and Transaction Analysis

**File:** `app/ml/graph_clustering.py`

-   Added validation for transaction endpoints, amounts, and timestamps.
-   Added safe conversion and handling of malformed or missing values.
-   Improved NetworkX graph construction.
-   Implemented degree centrality, PageRank, and approximate betweenness
    centrality.
-   Added cycle detection with a maximum cycle length of 6.
-   Limited cycle exploration to 5,000 paths and exposed whether the
    search completed.
-   Added Shannon entropy calculation for positive outgoing transaction
    values.
-   Added transfer-velocity calculation using transaction timestamps.
-   Added defensive handling for invalid graph data.

### 2.2 Peeling and Structuring Detection

**File:** `app/ml/peeling.py`

-   Added validation for transaction amounts.
-   Handled missing, malformed, negative, Boolean, and non-finite
    values.
-   Implemented peeling checks for transactions with exactly 2 or 3
    outgoing transfers.
-   Added ratio-based peeling detection with a 1--20% threshold.
-   Improved structuring detection by considering valid transactions in
    the \$8,500--\$9,999 range.
-   Added safeguards so invalid values do not silently enter the
    calculations.

### 2.3 Mixer and Service Directory

**File:** `app/ml/mixer_directory.py`

-   Added directory entries for Tornado Cash, Railgun, FixedFloat,
    TronAnonymousPool, Sinbad, and Blender.io.
-   Added chain normalization and chain-specific matching.
-   Used case-insensitive address matching for EVM chains.
-   Preserved case-sensitive matching for non-EVM chains.
-   Added explicit verification and sanctions-status metadata.
-   Marked directory entries as `UNVERIFIED` and `NOT_VERIFIED`; the
    directory metadata should not be interpreted as authoritative
    verification or proof of sanctions status.

### 2.4 Risk Scoring

**File:** `app/ml/scorer.py`

-   Integrated mixer-directory identification.
-   Integrated peeling and structuring detection.
-   Integrated graph entropy and transfer velocity.
-   Integrated typology classification.
-   Added heuristic risk scores and risk tiers for identified service
    categories.
-   Preserved low-risk handling for identified VASP exchange vaults when
    they are not matched to a directory entry.
-   Added explanatory flags and risk descriptions.
-   Maintained the eight-dimensional feature vector.
-   Added caveats to avoid treating a directory match as proof of
    suspicious activity.

**Scoring note:** The configured scores are heuristic weights, not
calibrated probabilities.

### 2.5 Syndicate / Typology Classification

**File:** `app/ml/syndicate_classifier.py`

-   Added safer input handling and chain normalization.
-   Refined priority-based classification for mixer activity, peeling,
    structuring, and rapid transaction patterns.
-   Retained the existing typology codes and function compatibility.
-   Avoided treating compatibility parameters as independent evidence
    when they are not used as classification signals.

### 2.6 Transaction Tracing

**File:** `app/core/tracer.py`

-   Removed redundant per-node centrality calculations.
-   Prevented centrality values from overwriting the existing peeling
    feature-vector dimension.
-   Preserved mixer-proximity and VASP-custody-proximity features.
-   Added directed shortest-path lookup with an undirected fallback.
-   Corrected Optional-value and numeric type handling identified by
    Pylance.

### 2.7 Dependencies

**File:** `requirements.txt`

-   Updated backend dependency declarations.
-   Added the required ReportLab dependency.
-   Constrained NumPy to `>=1.26.4,<2.0`.
-   Included the required scientific-computing and backend packages.

------------------------------------------------------------------------

## 3. Validation Tests Added

Added the following test files:

  ------------------------------------------------------------------------------------
  Test file                                        Coverage
  ------------------------------------------------ -----------------------------------
  `tests/test_ml_graph_clustering_validation.py`   Graph construction and malformed
                                                   transaction input validation

  `tests/test_ml_peeling_validation.py`            Peeling and structuring input
                                                   validation

  `tests/test_ml_mixer_risk.py`                    Mixer lookup, chain matching,
                                                   directory metadata, and VASP risk
                                                   handling
  ------------------------------------------------------------------------------------

The tests include checks for unknown addresses, chain-specific mixer
lookup, unverified directory metadata, and low-risk VASP classification
when no directory match exists.

------------------------------------------------------------------------

## 4. Git Workflow

### 4.1 Initial Implementation Commit

The initial ML implementation was committed with:

``` powershell
git add .
git commit -m "Improve ML risk scoring and validation"
```

**Commit:** `72c3d7d` --- `Improve ML risk scoring and validation`

### 4.2 Feature Branch

Created a dedicated feature branch:

``` powershell
git switch -c feature/ml-risk-validation
```

Pushed the branch and configured its upstream:

``` powershell
git push -u origin feature/ml-risk-validation
```

### 4.3 Pylance Corrections

After reviewing the VS Code Problems panel, corrected type-related
issues in:

-   `app/core/tracer.py`
-   `app/ml/peeling.py`
-   `tests/test_ml_graph_clustering_validation.py`

The corrections addressed Optional-value narrowing, numeric type
validation, and the test's intentionally malformed runtime input.

The Problems panel was rechecked and showed **0 Pylance errors**.

### 4.4 Follow-up Commit

Staged and committed the Pylance corrections:

``` powershell
git add app/core/tracer.py app/ml/peeling.py tests/test_ml_graph_clustering_validation.py
git commit -m "Fix Pylance type issues in ML validation"
```

**Commit:** `d13381f` --- `Fix Pylance type issues in ML validation`

### 4.5 Push to Remote

Pushed the follow-up commit to the existing feature branch:

``` powershell
git push origin feature/ml-risk-validation
```

The push completed successfully.

------------------------------------------------------------------------

## 5. Final Validation Results

### Test suite

Command:

``` powershell
python -m pytest -q
```

Result:

  Outcome      Count
  ---------- -------
  Passed          84
  Skipped          1
  Failed           0
  Warnings         2

**Pytest summary:** `84 passed, 1 skipped, 2 warnings`

The two warnings were deprecation/configuration warnings from the test
environment and Starlette integration. They did not cause test failures.

### Whitespace validation

Command:

``` powershell
git diff --check
```

No whitespace errors were reported.

### Static analysis

-   Pylance Problems panel: **0 errors**.

------------------------------------------------------------------------

## 6. Final Git State

Final verification commands:

``` powershell
git status
git log -2 --oneline
```

Observed commit history:

``` text
d13381f Fix Pylance type issues in ML validation
72c3d7d Improve ML risk scoring and validation
```

Final repository state:

  Check                 Result
  --------------------- -------------------------------------
  Current branch        `feature/ml-risk-validation`
  Remote branch         `origin/feature/ml-risk-validation`
  Local/remote sync     Up to date
  Working tree          Clean
  Uncommitted changes   None
  `main` branch         Unchanged at `72c3d7d`
  Pull Request          Not yet created

------------------------------------------------------------------------

## 7. Next Step

Create a Pull Request from `feature/ml-risk-validation` into `main`:

[Open the GitHub comparison
page](https://github.com/somil71/NIRMAAN/compare/main...feature/ml-risk-validation)

Before submitting, review the changed files and PR description with the
team. The branch has been pushed, but no Pull Request has been created
and no merge has been performed.

------------------------------------------------------------------------

## 8. Completion Summary

The backend ML risk-scoring and validation changes have been implemented
across the graph-clustering, peeling, mixer-directory, scoring,
typology-classification, and transaction-tracing modules. Validation
tests were added, the full test suite completed with **84 passed and 1
skipped**, Pylance reported **0 errors**, and the changes were committed
and pushed to `feature/ml-risk-validation`.

**Current handoff point:** Ready for Pull Request creation and team
review.
