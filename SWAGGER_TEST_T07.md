# T07: Non-existent Location - Swagger Testing Code

## How to Test in Swagger UI

1. Navigate to: `http://127.0.0.1:8000/docs`
2. Find endpoint: `POST /api/v1/property-search`
3. Click: **"Try it out"**
4. Clear the request body
5. Paste this JSON:

```json
{
  "requirements": {
    "original_query": "house in Atlantis",
    "intent": "BUY_PROPERTY",
    "location": "Atlantis",
    "property_type": "house",
    "listing_type": "sale",
    "maximum_budget_lkr": 50000000
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

- [ ] Status Code: `200 OK` (no crash) ✅
- [ ] `returned`: `0` ✅
- [ ] `total_found`: `0` ✅
- [ ] `relaxed_filters`: `true` (fallback triggered) ✅
- [ ] `results`: Empty array `[]` ✅
- [ ] `warnings`: Contains helpful message ✅
- [ ] No error response or exception ✅

---

## Key Observations

### 1. Non-Existent Location Handling
- "Atlantis" doesn't exist in dataset
- Hard filters return 0 matches
- Graceful handling without crash

### 2. Fallback Mechanism Activated
- `relaxed_filters = true` indicates fallback triggered
- Budget +20% and bedroom constraint dropped
- Still no matches after relaxation

### 3. User-Friendly Response
- Returns empty results (not null/error)
- Includes helpful warning message
- Guides user to broaden constraints

### 4. Robustness
- Unknown location doesn't crash API
- Proper error handling demonstrated
- Clean response structure maintained

---

## Additional Test Variations

### Typo in Location
```json
{
  "requirements": {
    "original_query": "house in Colomboo (typo)",
    "intent": "BUY_PROPERTY",
    "location": "Colomboo",
    "property_type": "house",
    "listing_type": "sale",
    "maximum_budget_lkr": 50000000
  },
  "top_n": 100
}
```

**Expected**: Same as T07 (0 results, fallback triggered)

### Completely Invalid Location
```json
{
  "requirements": {
    "original_query": "house in XYZ123ABC",
    "intent": "BUY_PROPERTY",
    "location": "XYZ123ABC",
    "property_type": "house",
    "listing_type": "sale",
    "maximum_budget_lkr": 50000000
  },
  "top_n": 100
}
```

**Expected**: Same as T07 (0 results, fallback triggered)

---

## Result

✅ **PASS** - Non-existent location handled gracefully with proper fallback and no crash!

This test validates:
- Error resilience ✅
- Graceful fallback mechanism ✅
- User-friendly messaging ✅
- No hard crashes on invalid input ✅
