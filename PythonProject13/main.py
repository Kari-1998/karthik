from utils.file_reader import read_input_file

def main():
    file_path = "input.txt"
    try:
        data = read_input_file(file_path)
        print("Contents of the file:")
        print(data)
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' does not exist.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
