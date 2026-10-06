# Test T02d: Location Alias "malabe city" (FIXED)
# Description: Verify that location alias with "city" suffix is correctly matched
# Expected: Should return 1 result with score 0.6513, relaxed_filters = False

Write-Host "================================" -ForegroundColor Cyan
Write-Host "TEST T02d: 'malabe city' Alias" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Test Configuration
$testId = "T02d"
$location = "malabe city"
$expectedReturned = 1
$expectedScore = 0.6513
$expectedRelaxed = $false

Write-Host "Test Configuration:"
Write-Host "  ID: $testId"
Write-Host "  Location: '$location'"
Write-Host "  Expected returned: $expectedReturned"
Write-Host "  Expected score: $expectedScore"
Write-Host "  Expected relaxed_filters: $expectedRelaxed"
Write-Host ""

# Prepare request payload
$payload = @{
    requirements = @{
        original_query = "3 bedroom house in malabe city under 20 million"
        intent = "BUY_PROPERTY"
        location = $location
        district = $null
        maximum_budget_lkr = 20000000
        minimum_budget_lkr = $null
        property_type = "house"
        listing_type = "sale"
        bedrooms = 3
        bathrooms = $null
        land_size_perches = $null
        minimum_land_size_perches = $null
        maximum_land_size_perches = $null
        minimum_house_size_sqft = $null
    }
    top_n = 100
} | ConvertTo-Json

Write-Host "Sending request to: http://127.0.0.1:8000/api/v1/property-search"
Write-Host ""

try {
    # Send request
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/v1/property-search" `
        -Method POST `
        -ContentType "application/json" `
        -Body $payload `
        -ErrorAction Stop

    # Parse response
    $result = $response.Content | ConvertFrom-Json

    Write-Host "✅ Request succeeded (Status: $($response.StatusCode))"
    Write-Host ""

    # Display response summary
    Write-Host "Response Summary:" -ForegroundColor Yellow
    Write-Host "  Status code: $($response.StatusCode)"
    Write-Host "  Returned: $($result.returned)"
    Write-Host "  Total found: $($result.total_found)"
    Write-Host "  Relaxed filters: $($result.relaxed_filters)"
    Write-Host ""

    # Display first result details
    if ($result.returned -gt 0) {
        Write-Host "First Result:" -ForegroundColor Yellow
        Write-Host "  Listing ID: $($result.results[0].listing_id)"
        Write-Host "  Location: $($result.results[0].location)"
        Write-Host "  Score: $($result.results[0].score)"
        Write-Host "  Bedrooms: $($result.results[0].bedrooms)"
        Write-Host "  Price: LKR $($result.results[0].sale_total_price_lkr)"
        Write-Host ""

        # Display score breakdown
        Write-Host "Score Breakdown:" -ForegroundColor Yellow
        Write-Host "  Location (0.40): $($result.results[0].score_breakdown.location)"
        Write-Host "  Budget (0.25): $($result.results[0].score_breakdown.budget_fit)"
        Write-Host "  Bedrooms (0.15): $($result.results[0].score_breakdown.bedrooms)"
        Write-Host "  Size (0.10): $($result.results[0].score_breakdown.size_fit)"
        Write-Host "  Verified (0.06): $($result.results[0].score_breakdown.verified)"
        Write-Host "  Recency (0.04): $($result.results[0].score_breakdown.recency)"
        Write-Host ""
    }

    # Validate test results
    Write-Host "Test Validation:" -ForegroundColor Yellow
    
    $testPassed = $true
    $issues = @()

    # Check returned count
    if ($result.returned -ne $expectedReturned) {
        $testPassed = $false
        $issues += "  ❌ Expected returned=$expectedReturned, got $($result.returned)"
    } else {
        Write-Host "  ✅ Returned count: $($result.returned) (expected: $expectedReturned)"
    }

    # Check score
    if ($result.returned -gt 0) {
        $actualScore = [Math]::Round($result.results[0].score, 4)
        if ($actualScore -ne $expectedScore) {
            $testPassed = $false
            $issues += "  ❌ Expected score=$expectedScore, got $actualScore"
        } else {
            Write-Host "  ✅ Score: $actualScore (expected: $expectedScore)"
        }
    }

    # Check relaxed_filters
    if ($result.relaxed_filters -ne $expectedRelaxed) {
        $testPassed = $false
        $issues += "  ❌ Expected relaxed_filters=$expectedRelaxed, got $($result.relaxed_filters)"
    } else {
        Write-Host "  ✅ Relaxed filters: $($result.relaxed_filters) (expected: $expectedRelaxed)"
    }

    Write-Host ""
    
    # Save response to file
    $outputFile = "agent2_evidence/T02d_FIXED.json"
    $result | ConvertTo-Json -Depth 10 | Out-File -FilePath $outputFile -Encoding UTF8
    Write-Host "Response saved to: $outputFile"
    Write-Host ""

    # Test result
    if ($testPassed) {
        Write-Host "================================" -ForegroundColor Green
        Write-Host "✅ TEST PASSED - T02d FIXED" -ForegroundColor Green
        Write-Host "================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "The location alias 'malabe city' is now correctly matched!"
        Write-Host "Status: PASS (FIXED) - Location normalization working"
    } else {
        Write-Host "================================" -ForegroundColor Red
        Write-Host "❌ TEST FAILED - T02d NOT FIXED" -ForegroundColor Red
        Write-Host "================================" -ForegroundColor Red
        Write-Host ""
        Write-Host "Issues found:"
        foreach ($issue in $issues) {
            Write-Host $issue
        }
    }

} catch {
    Write-Host "❌ Request failed!" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)"
    Write-Host ""
    Write-Host "Troubleshooting:"
    Write-Host "1. Make sure backend is running on http://127.0.0.1:8000"
    Write-Host "2. Start backend with: python -m uvicorn app.main:app --reload"
    Write-Host "3. Check if port 8000 is in use: netstat -ano | findstr :8000"
}

Write-Host ""
Write-Host "Test completed at: $(Get-Date)"
