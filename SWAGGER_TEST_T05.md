# T05: Moderate Query / Scoring - Swagger Testing Code

## How to Test in Swagger UI

1. Navigate to: `http://127.0.0.1:8000/docs`
2. Find endpoint: `POST /api/v1/property-search`
3. Click: **"Try it out"**
4. Clear the request body
5. Paste this JSON:

```json
{
  "requirements": {
    "original_query": "3 bedroom house in Malabe under 100 million",
    "intent": "BUY_PROPERTY",
    "location": "Malabe",
    "property_type": "house",
    "listing_type": "sale",
    "maximum_budget_lkr": 100000000,
    "bedrooms": 3
  },
  "top_n": 100
}
```

6. Click: **"Execute"**

---

## Expected Response

```json
{
  "returned": 9,
  "total_found": 9,
  "relaxed_filters": false,
  "results": [
    {
      "score": 0.8884,
      "location": "Malabe",
      "bedrooms": 3.0
    },
    {
      "score": 0.8687,
      "location": "Malabe",
      "bedrooms": 3.0
    },
    {
      "score": 0.8508,
      "location": "Malabe",
      "bedrooms": 3.0
    }
  ]
}
```

---

## Test Validation Checklist

- [ ] Status Code: `200 OK`
- [ ] `returned`: `9` ✅
- [ ] `total_found`: `9` ✅
- [ ] `relaxed_filters`: `false` ✅
- [ ] Top 3 scores: `0.8884, 0.8687, 0.8508` ✅
- [ ] All scores >= `0.50` ✅
- [ ] Scores descend in order ✅
- [ ] No sub-threshold results dropped ✅

---

## Key Observations

- **Wide budget** (100M) returns more results than T01 (20M)
- **Better scoring** than T01 due to loose budget constraint
- **No sub-threshold filtering** because all 9 matched properties score >= 0.50
- **Fallback not triggered** (relaxed_filters = false) since strict filters found results

---

## Result

✅ **PASS** - Wide budget query returns properly scored results without dropping sub-0.50 properties!
