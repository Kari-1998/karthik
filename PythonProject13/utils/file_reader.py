def read_input_file(file_path):
    """
    Reads the content of the input file and returns it as a string.

    :param file_path: Path to the input file
    :return: Content of the file as a string
    :raises FileNotFoundError: If the file does not exist
    :raises IOError: If there's an issue reading the file
    """
    with open(file_path, 'r') as file:
        return file.read()
