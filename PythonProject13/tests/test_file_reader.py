import os
import pytest
from utils.file_reader import read_input_file


def test_read_input_file():
    # Setup: Create a temporary file for testing
    test_file = "test_input.txt"
    test_content = "This is test data for unit testing."
    with open(test_file, 'w') as file:
        file.write(test_content)

    # Test: Verify the function reads the file correctly
    assert read_input_file(test_file) == test_content

    # Cleanup: Remove the temporary test file
    os.remove(test_file)


def test_read_input_file_nonexistent():
    # Test: Verify that FileNotFoundError is raised for a nonexistent file
    with pytest.raises(FileNotFoundError):
        read_input_file("nonexistent_file.txt")
