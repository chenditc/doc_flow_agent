import pytest
from exceptions import TaskInputMissingError, TaskCreationError

class TestCustomExceptions:
    def test_task_input_missing_error(self):
        exc = TaskInputMissingError("field1", "Field is required")
        assert exc.field_name == "field1"
        assert exc.description == "Field is required"
        assert str(exc) == "Missing input for field 'field1': Field is required"

    def test_task_creation_error_basic(self):
        orig_err = ValueError("fail")
        exc = TaskCreationError("desc", orig_err)
        assert exc.task_description == "desc"
        assert exc.original_error == orig_err
        assert exc.recovery_tasks == []
        assert "Failed to create task 'desc': fail" in str(exc)

    def test_task_creation_error_with_recovery(self):
        orig_err = RuntimeError("fail2")
        exc = TaskCreationError("desc2", orig_err, ["Try again", "Check input"])
        assert "Suggested recovery tasks: ['Try again', 'Check input']" in str(exc)
