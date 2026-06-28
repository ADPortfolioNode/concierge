$max=30
for ($i=0; $i -lt $max; $i++) {
  try {
    $r = Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:5173/api/v1/concierge/conversation' -Method Get -ErrorAction Stop
    Write-Output $r.StatusCode
    $r.Content | Out-File convo.json
    exit 0
  } catch {
    Start-Sleep -Seconds 2
  }
}
Write-Output 'TIMEOUT'
exit 1
