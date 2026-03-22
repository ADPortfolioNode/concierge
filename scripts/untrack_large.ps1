Param(
    [string]$CommitMessage = "Remove large tracked files and add .vercelignore"
)

$patterns = @(
    "_vendor",
    "greeting_out.txt",
    "test_phase6_out3.txt"
)

Write-Host "Preparing to untrack patterns:`n" ($patterns -join "`n")

foreach ($p in $patterns) {
    if (Test-Path $p) {
        Write-Host "Removing from index: $p"
        git rm --cached -r -- "$p"
    } else {
        Write-Host "Not found (skipping): $p"
    }
}

Write-Host "Staging .vercelignore"
git add .vercelignore

Write-Host "Committing changes"
if ((git status --porcelain) -ne $null) {
    git commit -m $CommitMessage
    Write-Host "Commit created. Run 'git push' to push to remote."
} else {
    Write-Host "No changes to commit."
}
