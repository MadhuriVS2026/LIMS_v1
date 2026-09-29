# One-off connectivity check against SAP Integration Suite (CPI) using curl.exe.
# Reads credentials from .env in this folder; never echoes the values.

$envFile = Join-Path $PSScriptRoot ".env"
$envVars = @{}
Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*([^#=]+)=(.*)$') {
        $envVars[$matches[1].Trim()] = $matches[2].Trim()
    }
}

$baseUrl = $envVars['SAP_CPI_BASE_URL']
$user = $envVars['SAP_CPI_USERNAME']
$pass = $envVars['SAP_CPI_PASSWORD']

$url = "$baseUrl/http/Dev/Get/WMS_PlantData"
Write-Host "Testing GET $url"

& curl.exe -s -o response.json -w "HTTP_STATUS:%{http_code}`n" -u "${user}:${pass}" -X GET $url

Write-Host "--- Response body (first 1000 chars) ---"
if (Test-Path response.json) {
    Get-Content response.json -Raw | ForEach-Object { $_.Substring(0, [Math]::Min(1000, $_.Length)) }
}
