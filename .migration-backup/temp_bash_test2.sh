set -f
py_cmd=(python)
backend_cmd=("${py_cmd[@]}" -u -m uvicorn app:app --host 127.0.0.1 --port 8001 --reload --reload-exclude 'frontend/node_modules/*' --reload-exclude '**/node_modules/*')
printf 'CMD: %s\n' "${backend_cmd[@]}"
python -c 'import sys; print(sys.argv)' "${backend_cmd[@]:1}"
