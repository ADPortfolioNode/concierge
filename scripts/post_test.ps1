try {
  $r = Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:5173/api/v1/concierge/message' -Method Post -ContentType 'application/json' -Body '{"message":"smoke test"}' -ErrorAction Stop
  Write-Output $r.StatusCode
  $r.Content | Out-File post_resp.json
} catch {
  Write-Output 'ERROR'
  if ($_.Exception.Response) { $_.Exception.Response.StatusCode.Value__ } else { $_.Exception.Message }
  exit 1
}
