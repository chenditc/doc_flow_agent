import argparse
import contextlib
import io
import json
import sys
import traceback
from typing import Any, Dict


def main():
    parser = argparse.ArgumentParser(description="Safely execute a Python script.")
    parser.add_argument("--code-file", required=True, help="Path to the Python code file.")
    parser.add_argument("--context-file", required=True, help="Path to the JSON context file.")
    parser.add_argument("--output-file", required=True, help="Path to the JSON output results file.")
    args = parser.parse_args()

    with open(args.code_file, "r") as f:
        code_string = f.read()

    with open(args.context_file, "r") as f:
        context = json.load(f)

    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    return_value = None
    exception_details: Dict[str, Any] | None = None

    try:
        with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
            exec_scope: Dict[str, Any] = {}
            exec(code_string, exec_scope)

            process_step_func = exec_scope.get("process_step")

            if process_step_func and callable(process_step_func):
                return_value = process_step_func(context)
            else:
                raise NameError("Function 'process_step' not found in the provided code.")

    except Exception as e:
        tb_str = traceback.format_exc()
        exception_details = {
            "type": type(e).__name__,
            "message": str(e),
            "traceback": tb_str,
        }

    result = {
        "return_value": None,
        "exception": exception_details,
    }
    
    try:
        # Attempt to serialize the return value
        json.dumps(return_value)
        result["return_value"] = return_value
    except (TypeError, OverflowError):
        # If not serializable, convert to string
        result["return_value"] = str(return_value)


    with open(args.output_file, "w") as f:
        json.dump(result, f)

    # Print captured stdout and stderr to the actual streams
    sys.stdout.write(stdout_capture.getvalue())
    sys.stderr.write(stderr_capture.getvalue())


if __name__ == "__main__":
    main()
