from tools.python_executor_tool import PythonExecutorTool


def test_extract_exception_from_exec_resp_traceback():
    exec_resp = {
        "language": "python",
        "status": "error",
        "outputs": [
            {
                "output_type": "error",
                "ename": "ZeroDivisionError",
                "evalue": "division by zero",
                "traceback": [
                    "Traceback (most recent call last):",
                    "  File \"<string>\", line 1, in <module>",
                    "ZeroDivisionError: division by zero",
                ],
            }
        ],
    }

    err = PythonExecutorTool._extract_exception_from_exec_resp(exec_resp)
    assert err is not None
    assert "ZeroDivisionError" in err
    assert "division by zero" in err


def test_extract_exception_from_exec_resp_ename_evalue():
    exec_resp = {
        "language": "python",
        "status": "error",
        "outputs": [
            {
                "output_type": "error",
                "ename": "ValueError",
                "evalue": "bad value",
                "traceback": [],
            }
        ],
    }

    err = PythonExecutorTool._extract_exception_from_exec_resp(exec_resp)
    assert err == "ValueError: bad value"


def test_extract_exception_from_exec_resp_none():
    exec_resp = {
        "language": "python",
        "status": "ok",
        "outputs": [
            {"output_type": "stream", "name": "stdout", "text": "hello"}
        ],
    }
    err = PythonExecutorTool._extract_exception_from_exec_resp(exec_resp)
    assert err is None
