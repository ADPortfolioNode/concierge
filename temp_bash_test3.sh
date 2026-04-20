set -f
py_cmd=(python)
backend_cmd=("${py_cmd[@]}" -c 'import sys; print(sys.argv)' --host 127.0.0.1 --reload --reload-exclude 'frontend/node_modules/*' --reload-exclude '**/node_modules/*')
nohup "${backend_cmd[@]}" > /tmp/test_args.log 2>&1 &
pid=$!
wait $pid
cat /tmp/test_args.log
