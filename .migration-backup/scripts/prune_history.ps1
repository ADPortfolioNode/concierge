Param(
    [string[]]$PathsToRemove = @('_vendor','greeting_out.txt','test_phase6_out3.txt'),
    [string]$Remote = 'origin',
    [string]$Branch = 'main'
)

Write-Host "This script will rewrite git history to remove the following paths:`n" ($PathsToRemove -join "`n") -ForegroundColor Yellow
Write-Host "Prerequisites: install 'git-filter-repo' (preferred) or BFG. This script uses git-filter-repo if present." -ForegroundColor Cyan

function Has-Command($cmd){
    $which = (Get-Command $cmd -ErrorAction SilentlyContinue)
    return $which -ne $null
}

if (-not (Has-Command 'git')) {
    Write-Error "git is required"
    exit 1
}

$useFilterRepo = $false
try { git filter-repo --help > $null 2>&1; $useFilterRepo = $true } catch {}

if ($useFilterRepo) {
    Write-Host "Using git-filter-repo to remove paths..." -ForegroundColor Green
    $pathsArg = $PathsToRemove | ForEach-Object { "--path $_ --invert-paths" }
    # Build a temporary command that removes all specified paths
    $tmpFile = "remove_paths.txt"
    $PathsToRemove | Out-File -Encoding utf8 $tmpFile
    Write-Host "Running: git filter-repo --paths-from-file $tmpFile --invert-paths"
    git filter-repo --paths-from-file $tmpFile --invert-paths
    Remove-Item $tmpFile
} else {
    Write-Host "git-filter-repo not found. Showing BFG / filter-branch fallback instructions." -ForegroundColor Yellow
    Write-Host "You can install git-filter-repo: https://github.com/newren/git-filter-repo" -ForegroundColor Cyan
    Write-Host "Fallback (manual) example using BFG (not executed):" -ForegroundColor Cyan
    Write-Host "  bfg --delete-files 'greeting_out.txt' repo.git" -ForegroundColor Gray
    Write-Host "Or using git filter-branch (slow and discouraged):" -ForegroundColor Gray
    Write-Host "  git filter-branch --force --index-filter `"git rm -r --cached --ignore-unmatch greeting_out.txt _vendor`" --prune-empty --tag-name-filter cat -- --all"
    exit 1
}

Write-Host "Garbage-collecting and pruning refs..." -ForegroundColor Green
git reflog expire --expire=now --all
git gc --prune=now --aggressive

Write-Host "Local history rewritten. NEXT STEP: force-push to remote to replace history." -ForegroundColor Yellow
Write-Host "To push, run:" -ForegroundColor Cyan
Write-Host "  git push $Remote --force --all" -ForegroundColor White
Write-Host "  git push $Remote --force --tags" -ForegroundColor White

Write-Host "IMPORTANT: force-pushing rewrites remote history and will require collaborators to re-clone or reset their local branches." -ForegroundColor Red
