# Agent 2 Testing Guide: Swagger API & Vulnerability Assessment

## Quick Start: Test Agent 2 via Swagger

### Step 1: Start the Backend API

```powershell
cd "d:\My Projects\propwise-ai\backend"
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Expected output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

---

### Step 2: Open Swagger UI

Navigate to:
```
http://127.0.0.1:8000/docs
```

You'll see the FastAPI Swagger interface with all endpoints listed.

---

### Step 3: Locate Agent 2 Endpoint

In Swagger, find:
```
POST /api/v1/property-search
```

This is the Agent 2 endpoint.

---

## Testing Agent 2 via Swagger: Step-by-Step

### Test Case 1: Normal Query (Agent 2 with valid inputs)

1. **Expand** the `/api/v1/property-search` endpoint
2. **Click** "Try it out"
3. **Enter this JSON** in the request body:

```json
{
  "requirements": {
    "original_query": "3 bedroom house in Malabe under 20 million",
    "intent": "BUY_PROPERTY",
    "location": "Malabe",
    "district": null,
    "maximum_budget_lkr": 20000000,
    "minimum_budget_lkr": null,
    "property_type": "house",
    "listing_type": "sale",
    "bedrooms": 3,
    "bathrooms": null,
    "land_size_perches": null,
    "minimum_land_size_perches": null,
    "maximum_land_size_perches": null,
    "minimum_house_size_sqft": null
  },
  "top_n": 100
}
```

4. **Click** "Execute"
5. **Observe** the response:
   - Status: `200 OK`
   - Results should show 1-5 properties
   - Each result has `score` and `score_breakdown`

---

### Test Case 2: Location Alias (Semantic Matching)

Test the newly fixed location normalization:

#### 2a: Lowercase Alias
```json
{
  "requirements": {
    "original_query": "3 bedroom house near malabe under 20 million",
    "intent": "BUY_PROPERTY",
    "location": "near malabe",
    "property_type": "house",
    "listing_type": "sale",
    "maximum_budget_lkr": 20000000,
    "bedrooms": 3
  },
  "top_n": 100
}
```

**Expected:** Should return same results as Test Case 1 (fixed) ✅

#### 2b: Mixed Case Alias
```json
{
  "requirements": {
    "original_query": "3 bedroom house Near Malabe under 20 million",
    "intent": "BUY_PROPERTY",
    "location": "Near Malabe",
    "property_type": "house",
    "listing_type": "sale",
    "maximum_budget_lkr": 20000000,
    "bedrooms": 3
  },
  "top_n": 100
}
```

**Expected:** Should return same results as Test Case 1 (case-insensitive) ✅

#### 2c: Uppercase Alias
```json
{
  "requirements": {
    "original_query": "3 bedroom house NEAR MALABE under 20 million",
    "intent": "BUY_PROPERTY",
    "location": "NEAR MALABE",
    "property_type": "house",
    "listing_type": "sale",
    "maximum_budget_lkr": 20000000,
    "bedrooms": 3
  },
  "top_n": 100
}
```

**Expected:** Should return same results as Test Case 1 (case-insensitive) ✅

#### 2d: City Suffix Alias
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

**Expected Response:**
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

**Status:** ✅ PASS (FIXED) - "city" suffix now correctly stripped

---

### Test Case 3: Rent Query

```json
{
  "requirements": {
    "original_query": "rent apartment in Colombo under 150000",
    "intent": "RENT_PROPERTY",
    "location": "Colombo",
    "property_type": "apartment",
    "listing_type": "rent",
    "maximum_budget_lkr": 150000
  },
  "top_n": 100
}
```

**Expected:** Returns 2+ rent listings

---

### Test Case 4: Impossible Query (Fallback Trigger)

Test the two-pass fallback mechanism:

```json
{
  "requirements": {
    "original_query": "impossible query",
    "intent": "BUY_PROPERTY",
    "location": "Colombo",
    "listing_type": "sale",
    "property_type": "house",
    "maximum_budget_lkr": 100,
    "bedrooms": 5
  },
  "top_n": 100
}
```

**Expected Response:**
```json
{
  "results": [],
  "total_found": 0,
  "returned": 0,
  "relaxed_filters": true,
  "warnings": ["No properties matched. Consider broadening location or budget constraints."]
}
```

---

### Test Case 5: Sub-Threshold Filtering (0.50 Cutoff)

Verify that properties below 50% relevance are dropped:

```json
{
  "requirements": {
    "original_query": "broad Colombo search",
    "intent": "BUY_PROPERTY",
    "location": "Colombo",
    "listing_type": "sale",
    "property_type": "house",
    "maximum_budget_lkr": 100000000
  },
  "top_n": 100
}
```

**Expected:**
- `total_found`: 76+ (all matching filters)
- `returned`: 2-10 (only those >= 0.50 score)
- Difference shows properties dropped by 0.50 cutoff

---

## How to Save Swagger Responses

### Method 1: Copy-Paste from Swagger UI

1. Run request in Swagger
2. Right-click on response → Copy
3. Paste into file: `agent2_test_response_[NAME].json`

### Method 2: Use Browser Developer Tools

1. Open DevTools (F12)
2. Go to Network tab
3. Run Swagger request
4. Right-click on `property-search` request → Copy as cURL
5. Save to file

### Method 3: Use PowerShell to Call API Directly

```powershell
$payload = @{
    requirements = @{
        original_query = "3 bedroom house in Malabe under 20 million"
        intent = "BUY_PROPERTY"
        location = "Malabe"
        listing_type = "sale"
        property_type = "house"
        maximum_budget_lkr = 20000000
        bedrooms = 3
    }
    top_n = 100
} | ConvertTo-Json

$response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/v1/property-search" `
    -Method POST `
    -ContentType "application/json" `
    -Body $payload

# Save response
$response.Content | Out-File -FilePath "agent2_response.json" -Encoding UTF8

# Display response
$response.Content | ConvertFrom-Json | Format-List
```

---

## How to Test Against Vulnerability Assessment

### Step 1: Read Your Assessment Document

Your document likely contains vulnerabilities like:
- Location alias support
- Score cutoff enforcement
- Fallback mechanism
- Missing value handling
- Contradiction detection
- etc.

### Step 2: Create Test Cases from Each Vulnerability

For each vulnerability in the document:

**Example:**
- **Vulnerability:** "Location alias 'near malabe' not recognized"
- **Test case:** Use Swagger with `location: "near malabe"`
- **Expected:** Should return Malabe properties (NOW PASSES ✅)
- **Document result:** FIXED ✓ or UNFIXED ✗

### Step 3: Build Results Table

Create a comparison table:

| Vulnerability | Test Case Input | Expected | Actual | Status |
|---|---|---|---|---|
| Location alias "near malabe" | `location: "near malabe"` | 1+ results | 1 result ✓ | ✅ FIXED |
| Location alias "malabe city" | `location: "malabe city"` | 1+ results | 1 result ✓ | ✅ FIXED |
| 50% cutoff enforcement | broad query | only score >= 0.50 | ✓ enforced | ✅ PASS |
| Fallback trigger | impossible budget | relaxed_filters=true | ✓ true | ✅ PASS |

---

## Complete Testing Workflow

### 1. Create Test Plan File

Save as `TESTING_PLAN.md`:

```markdown
# Agent 2 Testing Plan Against Vulnerabilities

## Vulnerabilities from Assessment Report

### V1: Location Alias Recognition
- [ ] Test "near malabe"
- [ ] Test "malabe city"
- [ ] Test "close to colombo"
- [ ] Record Swagger responses

### V2: Score Cutoff (>= 0.50)
- [ ] Broad query returns only >= 0.50
- [ ] Sub-threshold properties excluded
- [ ] Record total_found vs returned

### V3: Fallback Mechanism
- [ ] Impossible query triggers fallback
- [ ] relaxed_filters = true
- [ ] Budget +20% applied
- [ ] Bedroom minimum dropped

### V4: Missing Value Handling
- [ ] null location works
- [ ] null budget works
- [ ] null bedrooms works

### V5: Contradiction Detection
- [ ] min_budget > max_budget detected
- [ ] Error message provided

...
```

### 2. Run Each Test in Swagger

- Take screenshot of request
- Take screenshot of response
- Save response JSON to `agent2_evidence/test_[ID].json`

### 3: Document Results

Create `VULNERABILITY_TEST_RESULTS.md`:

```markdown
# Vulnerability Assessment Results

## V1: Location Alias Recognition

### Test: "near malabe"
**Request:**
```
location: "near malabe"
...
```

**Response (from Swagger):**
```json
{
  "returned": 1,
  "results": [
    {
      "listing_id": "pr724-valuble-house-for-sale-in-malabe-tunadahena-for-sale-colombo",
      "score": 0.6513
    }
  ]
}
```

**Status:** ✅ PASS - Location alias now correctly matched

...
```

---

## Swagger Request Templates

Copy these and paste into Swagger's "Try it out" section:

### Template 1: Basic Sale Query
```json
{
  "requirements": {
    "original_query": "YOUR_QUERY_HERE",
    "intent": "BUY_PROPERTY",
    "location": "LOCATION",
    "listing_type": "sale",
    "property_type": "house",
    "maximum_budget_lkr": 20000000,
    "bedrooms": 3
  },
  "top_n": 100
}
```

### Template 2: Rent Query
```json
{
  "requirements": {
    "original_query": "YOUR_QUERY_HERE",
    "intent": "RENT_PROPERTY",
    "location": "LOCATION",
    "listing_type": "rent",
    "property_type": "apartment",
    "maximum_budget_lkr": 150000
  },
  "top_n": 100
}
```

### Template 3: Land Query
```json
{
  "requirements": {
    "original_query": "YOUR_QUERY_HERE",
    "intent": "BUY_LAND",
    "location": "LOCATION",
    "listing_type": "sale",
    "property_type": "land",
    "maximum_budget_lkr": 50000000,
    "minimum_land_size_perches": 10,
    "maximum_land_size_perches": 30
  },
  "top_n": 100
}
```

---

## How to Read Swagger Response

### Response Structure

```json
{
  "results": [                          // Array of matching properties
    {
      "listing_id": "string",           // Unique ID
      "location": "string",             // Location name
      "score": 0.6513,                  // Relevance score (0-1)
      "score_breakdown": {              // Component breakdown
        "budget_fit": 0.0312,            // Weight: 0.25
        "location": 0.4,                // Weight: 0.40
        "bedrooms": 0.15,               // Weight: 0.15
        "verified": 0.0,                // Weight: 0.06
        "size_fit": 0.05,               // Weight: 0.10
        "recency": 0.02                 // Weight: 0.04
      },
      "sale_total_price_lkr": 17500000,
      "bedrooms": 3.0,
      "land_size_perches": 7.5,
      "is_verified": false,
      "posted_date": "2023-01-25"
    }
  ],
  "total_found": 1,                     // Total matching hard filters
  "returned": 1,                        // Number in response (<= top_n, >= 0.50)
  "relaxed_filters": false,             // Was fallback triggered?
  "filters_applied": {                  // Snapshot of filters used
    "listing_type": "sale",
    "property_type": "house",
    "location": "Malabe",
    "max_budget_lkr": 20000000,
    "bedrooms_min": 3
  },
  "analysis": {                         // Market analysis
    "price_stats": {...}
  },
  "warnings": [],                       // Any warnings
  "metadata": {}                        // Additional data
}
```

### Key Fields to Check

| Field | Meaning | What to Look For |
|---|---|---|
| `returned` | Results in response | Should be > 0 for valid queries |
| `total_found` | Before 0.50 cutoff | Difference shows dropped properties |
| `relaxed_filters` | Fallback active? | true = strict filters failed |
| `score` | Relevance (0-1) | All should be >= 0.50 |
| `score_breakdown` | Component scores | Verify weights sum to score |
| `warnings` | Issues | Check for fallback messages |

---

## Quick Checklist for Testing

- [ ] Backend running on `http://127.0.0.1:8000`
- [ ] Swagger UI accessible at `http://127.0.0.1:8000/docs`
- [ ] Can see `/api/v1/property-search` endpoint
- [ ] Can "Try it out" on the endpoint
- [ ] Request body JSON is valid
- [ ] Response status is 200 OK
- [ ] Response contains `results`, `returned`, `total_found`, `relaxed_filters`
- [ ] All returned results have `score >= 0.50`
- [ ] Scores descend from first to last result
- [ ] Each result has `score_breakdown` with 6 components

---

## Troubleshooting

### Problem: 404 Error

**Cause:** Backend not running  
**Solution:** Start backend with uvicorn command above

### Problem: Connection Refused

**Cause:** Port 8000 in use  
**Solution:**
```powershell
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Problem: JSON Parse Error

**Cause:** Invalid JSON in request body  
**Solution:** 
- Check all quotes are double quotes `"`
- Check all comma placement
- Use online JSON validator before pasting

### Problem: 0 Results Returned but total_found > 0

**Cause:** All properties scored below 0.50 (strict cutoff)  
**Solution:** Broaden constraints (increase budget, remove bedrooms, etc.)

### Problem: relaxed_filters = true but still 0 results

**Cause:** Even with +20% budget and no bedroom minimum, no matches found  
**Solution:** Query is too restrictive; change location or other constraints

---

## Export Results to PDF

1. Take screenshots of each Swagger test
2. Save responses to JSON files
3. Create summary document with:
   - Test case
   - Request JSON
   - Response screenshot
   - Status (PASS/FAIL/FIXED)
4. Export to PDF using Word or Google Docs

---

## Integration with Vulnerability Assessment

For each vulnerability in your uploaded document:

| Step | Action |
|------|--------|
| 1 | Read vulnerability description |
| 2 | Design test case in Swagger |
| 3 | Execute test and save response |
| 4 | Compare actual vs expected |
| 5 | Document PASS/FAIL/FIXED status |
| 6 | Link to evidence file |

---

## Next Steps

1. **Start backend** (see Step 1 above)
2. **Open Swagger** at `http://127.0.0.1:8000/docs`
3. **Run test cases** from the templates above
4. **Save responses** to `agent2_evidence/` folder
5. **Compare against** your vulnerability assessment document
6. **Document findings** in a new report

---

**Need help?** Ask for specific test case or response interpretation.

