# T08: Contradictory Budget - Swagger Testing Code

## How to Test in Swagger UI

1. Navigate to: `http://127.0.0.1:8000/docs`
2. Find endpoint: `POST /api/v1/property-search`
3. Click: **"Try it out"**
4. Clear the request body
5. Paste this JSON:

```json
{
  "requirements": {
    "original_query": "house with contradictory budget",
    "intent": "BUY_PROPERTY",
    "location": "Colombo",
    "property_type": "house",
    "listing_type": "sale",
    "minimum_budget_lkr": 50000000,
    "maximum_budget_lkr": 10000000
  },
  "top_n": 100
}
```

6. Click: **"Execute"**

---

## Expected Response

```json
{
  "returned": 0,
  "total_found": 0,
  "relaxed_filters": true,
  "results": [],
  "warnings": [
    "No properties matched. Consider broadening location or budget constraints."
  ]
}
```

---

## Test Validation Checklist

- [ ] Status Code: `200 OK` (safe, no crash) ✅
- [ ] `returned`: `0` ✅
- [ ] `total_found`: `0` ✅
- [ ] `relaxed_filters`: `true` (fallback triggered) ✅
- [ ] `results`: Empty array `[]` ✅
- [ ] `warnings`: Generic message (NOT specific contradiction detection) ✅
- [ ] No explicit error about contradictory budget ⚠️

---

## Key Observations

### 1. Contradictory Budget Detection
- **Input**: min = 50M, max = 10M (impossible condition)
- **Logic**: minimum > maximum → no properties can satisfy
- **Result**: 0 matches in hard filters

### 2. Fallback Behavior
- Fallback triggered (relaxed_filters = true)
- Budget constraints relaxed by +20%
- Still 0 matches (contradiction not resolved by relaxation)

### 3. Missing Explicit Validation
- ⚠️ **Vulnerability V-03**: No specific contradiction message
- Returns generic "No properties matched" warning
- User not explicitly told: "min_budget > max_budget is invalid"
- Feeds into vulnerability assessment (missing input validation)

### 4. Safety Assessment
- ✅ **PASS (safe)**: Doesn't crash or return incorrect results
- ✅ Gracefully handles contradiction
- ⚠️ **Opportunity**: Could validate and reject upfront with specific error

---

## Related Test Variations

### Reverse Contradiction (max < min)
```json
{
  "requirements": {
    "original_query": "house with contradictory budget",
    "intent": "BUY_PROPERTY",
    "location": "Malabe",
    "property_type": "house",
    "listing_type": "sale",
    "minimum_budget_lkr": 100000000,
    "maximum_budget_lkr": 50000000
  },
  "top_n": 100
}
```

**Expected**: Same as T08 (0 results, fallback triggered)

### Near-Contradiction (min slightly > max)
```json
{
  "requirements": {
    "original_query": "house with near-contradictory budget",
    "intent": "BUY_PROPERTY",
    "location": "Colombo",
    "property_type": "house",
    "listing_type": "sale",
    "minimum_budget_lkr": 20000000,
    "maximum_budget_lkr": 19000000
  },
  "top_n": 100
}
```

**Expected**: Same as T08 (0 results, fallback triggered)

---

## Vulnerability V-03 Evidence

This test demonstrates:
- **Missing explicit validation** for contradictory inputs
- **Generic error handling** instead of specific feedback
- **System resilience** (doesn't crash)
- **User experience gap** (no guidance on what went wrong)

**Recommendation**: Add early validation:
```python
if minimum_budget_lkr is not None and maximum_budget_lkr is not None:
    if minimum_budget_lkr > maximum_budget_lkr:
        raise ValueError("minimum_budget_lkr cannot exceed maximum_budget_lkr")
```

---

## Result

✅ **PASS (safe)** - Contradictory budget handled gracefully without crash!

However:
- ⚠️ **V-03 Confirmed**: Missing explicit contradiction detection message
- ✅ Supports vulnerability assessment documentation
- ✅ Shows need for input validation enhancement
