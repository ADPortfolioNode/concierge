set -f
arr=('frontend/node_modules/*' '**/node_modules/*')
printf '%s\n' "${arr[@]}"
