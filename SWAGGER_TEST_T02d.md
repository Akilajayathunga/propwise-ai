# T02d: Location Alias "malabe city" - Swagger Testing Code

## How to Test in Swagger UI

1. Navigate to: `http://127.0.0.1:8000/docs`
2. Find endpoint: `POST /api/v1/property-search`
3. Click: **"Try it out"**
4. Clear the request body
5. Paste this JSON:

```json
{
  "requirements": {
    "original_query": "3 bedroom house in malabe city under 20 million",
    "intent": "BUY_PROPERTY",
    "location": "malabe city",
    "property_type": "house",
    "listing_type": "sale",
    "maximum_budget_lkr": 20000000,
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
  "returned": 1,
  "total_found": 1,
  "relaxed_filters": false,
  "results": [
    {
      "listing_id": "pr724-valuble-house-for-sale-in-malabe-tunadahena-for-sale-colombo",
      "location": "Malabe",
      "score": 0.6513,
      "score_breakdown": {
        "budget_fit": 0.0312,
        "location": 0.4,
        "bedrooms": 0.15,
        "verified": 0.0,
        "size_fit": 0.05,
        "recency": 0.02
      },
      "sale_total_price_lkr": 17500000,
      "bedrooms": 3.0
    }
  ]
}
```

---

## Test Validation Checklist

- [ ] Status Code: `200 OK`
- [ ] `returned`: `1` ✅
- [ ] `total_found`: `1` ✅
- [ ] `relaxed_filters`: `false` ✅
- [ ] `score`: `0.6513` ✅
- [ ] Location: `Malabe` ✅

---

## Result

✅ **PASS (FIXED)** - "malabe city" suffix now correctly stripped and matched!
