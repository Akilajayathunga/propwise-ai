# Agent 2 - Test Failures Fixed

## Summary

During the initial evidence report generation, 2 test cases marked as FAIL due to lack of location alias support. These have now been fixed by implementing location normalization.

## Failed Test Cases (Before Fix)

| Test ID | Description | Status | Issue |
|---------|-------------|--------|-------|
| T02c | `location="near malabe"` | ❌ FAIL | Literal substring match failed to recognize "near malabe" as "malabe" |
| T02d | `location="malabe city"` | ❌ FAIL | Literal substring match failed to recognize "malabe city" as "malabe" |

## Solution Implemented

### Location Normalization Function

Added a new helper function `_normalize_location()` that:
1. Takes a location phrase (e.g., "near malabe", "malabe city")
2. Extracts common qualifiers from start/end of phrase
3. Returns both original and normalized core location terms
4. Enables flexible matching against CSV data

### Qualifiers Stripped

```python
_LOCATION_QUALIFIERS = {
    "near", "around", "close to", "vicinity of", "vicinity",
    "city", "area", "zone", "region", "suburb",
    "district", "town", "town area",
}
```

### Files Modified

**1. `backend/app/retrieval/filters.py`**
- Added `_LOCATION_QUALIFIERS` set
- Added `_normalize_location()` function
- Updated `_mask_location()` to use normalization

**2. `backend/app/retrieval/scorer.py`**
- Added `_LOCATION_QUALIFIERS` set  
- Added `_normalize_location()` function
- Updated `_signal_location()` to apply normalization

## Fix Verification

### T02c After Fix: ✅ PASS

```json
{
  "test_id": "T02c",
  "input": {
    "location": "near malabe",
    "listing_type": "sale",
    "property_type": "house",
    "maximum_budget_lkr": 20000000,
    "bedrooms": 3
  },
  "returned": 1,
  "total_found": 1,
  "relaxed_filters": false,
  "warnings": [],
  "top_result": {
    "listing_id": "pr724-valuble-house-for-sale-in-malabe-tunadahena-for-sale-colombo",
    "score": 0.6513
  }
}
```

### T02d After Fix: ✅ PASS

```json
{
  "test_id": "T02d",
  "input": {
    "location": "malabe city",
    "listing_type": "sale",
    "property_type": "house",
    "maximum_budget_lkr": 20000000,
    "bedrooms": 3
  },
  "returned": 1,
  "total_found": 1,
  "relaxed_filters": false,
  "warnings": [],
  "top_result": {
    "listing_id": "pr724-valuble-house-for-sale-in-malabe-tunadahena-for-sale-colombo",
    "score": 0.6513
  }
}
```

## Test Coverage Summary

**Initial Test Results:**
- Total test cases: 16 (T01-T15 + T16)
- Passed: 13
- Failed: 2 (T02c, T02d)
- Not executed: 1 (T16 timing tests)

**After Fixes:**
- Total test cases: 16
- Passed: 15 ✅
- Failed: 0 ✅
- Not executed: 1 (T16 timing tests)

## Impact Analysis

### Positive Impacts
1. **User Experience:** Natural language queries with common location qualifiers now work correctly
2. **Robustness:** System handles variations like:
   - "near X"
   - "X city"
   - "X area"
   - "X zone"
   - "X suburb"
3. **Flexibility:** Both normalized and original terms are matched

### No Breaking Changes
- All previously passing tests still pass
- Scoring weights unchanged
- Filter logic unchanged except for enhanced location matching
- Backward compatible with exact location matches

## Code Quality Metrics

- Lines added: ~45 (2 functions across 2 files)
- Test coverage improvement: 13/15 → 15/15 passing (2 additional failures fixed)
- DRY violation: Both files contain identical normalized location logic (could be refactored to shared utility module in future)

## Future Improvements

1. **Refactor:** Move `_normalize_location()` to a shared utility module to avoid code duplication
2. **Configuration:** Make qualifier list configurable without code changes
3. **Performance:** Cache normalized locations if processing large batches
4. **Breadth:** Add support for:
   - Street type aliases (e.g., "St", "Street", "Ave")
   - Directional qualifiers (e.g., "North", "South")
   - Language variants (e.g., Sinhala transliterations)

## References

- Main evidence report: `AGENT2_EVIDENCE_REPORT.md`
- Evidence JSON files: `agent2_evidence/T02c_FIXED.json`, `agent2_evidence/T02d_FIXED.json`
- Modified source files:
  - `backend/app/retrieval/filters.py` (lines 26-56 and 96-97)
  - `backend/app/retrieval/scorer.py` (lines ~20-56 and ~107-134)

---

**Fixes completed:** October 5, 2026  
**Verification method:** Direct function execution via Pylance snippet  
**Test results saved:** `agent2_evidence/T02c_FIXED.json`, `agent2_evidence/T02d_FIXED.json`  
