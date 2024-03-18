import ast
import subprocess
import sys
import nbformat
import glob
import re
import requests
import os
from tabulate import tabulate
import importlib
import importlib.metadata
from stdlib_list import stdlib_list
import csv

def init_local_cache(dir):
    """
    Checks to see if a local file called "license_cache.csv" exists.
    If not, creates the file with the headers: "Package, License, Copyleft"

    :param dir: A string with the directory containing the file.
    """
    try:
        with open(f"{dir}/license_cache.csv", "x") as csvfile:
            writer = csv.writer(csvfile, delimiter=",")
            writer.writerow(['Package', 'License', 'Copyleft', 'Git_Hash', 'Email', 'Filename', 'Line_no'])
        print(f"Cache successfully created at {dir}")
    except FileExistsError:
        print(f"Cache successfully found at {dir}")

def check_cache(imports, dir):
    """
    Accepts a list of modules from the extract_imports_from_code() function,
    checking them against the local cache.
    Also checks if there are modules the cache that are no longer in the codebase,
    updating the cache to reflect this.
    Returns only the imports that are not currently present in the cache.

    :param imports: A list of modules.
    :param dir: A string with the directory containing the file.
    :return: A filtered list of imports.
    """
    cache_modules = []

    with open(f'{dir}/license_cache.csv', 'r') as csvfile:
        file = csv.DictReader(csvfile)
        for col in file:
            cache_modules.append(col['Package'])

    # Extract just the module names from imports for comparison
    module_names_in_imports = [item[0] for item in imports]

    uncached_modules = [item for item in imports if item[0] not in cache_modules] # in codebase but not cache
    uncached_names = [item[0] for item in uncached_modules] # for printing
    extra_modules = [item for item in cache_modules if item not in module_names_in_imports] # in cache but not in codebase
    extra_modules = [item[0] for item in extra_modules] # Keep only the package names
    print(f"Found following modules not in cache: {uncached_names}")
    print(f"Found following modules in cache not in codebase: {extra_modules}")

    # If there are extra modules, update the cache to reflect that.
    if len(extra_modules) > 0:
        with open(f'{dir}/license_cache.csv', 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            # Keep rows where the package is not in the extra_modules list
            rows = [row for row in reader if row['Package'] not in extra_modules]

        # Write the modified data back to the CSV file
        with open(f'{dir}/license_cache.csv', 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=['Package', 'License', 'Copyleft', 'Git_Hash', 'Email', 'Filename', 'Line_no'])
            writer.writeheader()
            writer.writerows(rows)

    return uncached_modules

def update_cache(result, dir):
    """
    Writes results to the local cache. Should only be run after check_cache().

    :param result: The output of extract_licenses()
    :param dir: A string with the directory containing the file.
    """
    with open(f'{dir}/license_cache.csv', 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        for row in result:
            writer.writerow(list(row))

def read_cache(dir):
    """
    Extracts all information from cache. Should be run just before pretty printing.

    :param dir: A string with the directory containing the file.
    :return: The contents of the csv file.
    """
    result = []
    with open(f'{dir}/license_cache.csv', 'r') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            result.append(row)
    
    return result

def parse_git_blame_output(output):
    """
    Parse the output of git blame to extract the commit hash and author's name (if available).
    :param output: The output string from git blame.
    :return: A tuple of (commit_hash, author_name, author_email)
    """
    # Regex to find email address
    email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    email_match = email_pattern.search(output)
    author_email = email_match.group(0) if email_match else "N/A"

    # Split the output at the email match
    parts_before_email = output.split(author_email)[0] if author_email else output
    parts = parts_before_email.split()

    commit_hash = parts[0]

    return commit_hash, author_email

def git_blame_info(filename, line_number):
    """
    Get git blame info for a specific line in a file.
    :param filename: The file to check.
    :param line_number: The line number to check.
    :return: A tuple of (commit_hash, author_name, email)
    """
    # Normalize and convert to absolute path
    repo_path = os.path.abspath(".")
    full_file_path = os.path.normpath(os.path.join(repo_path, filename))

    command = ["git", "-C", repo_path, "blame", "--show-email", "-L", f"{line_number},{line_number}", full_file_path]
    print(f"Running command: {' '.join(command)}")

    result = subprocess.run(command, capture_output=True, text=True)
    output = result.stdout.strip()

    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return "Error", "Error", "Error"

    commit_hash, author_email = parse_git_blame_output(output)
    return commit_hash, author_email

def find_copyleft_and_git_blame(imports):
    """
    Take the final list of imports with license info and run git blame on them
    :param imports: a list of tuples containing license info
    :return: a list of tuples updated with git blame info
    """
    result = []

    # Get git blame info for copyleft packages
    for entry in imports:
        package, license, copyleft, filename, line_no = entry
        if copyleft == True:
            print("Found copyleft, running Git Blame")
            commit_hash, author_email = git_blame_info(filename, line_no)
            result.append((package, license, copyleft, commit_hash, author_email, filename, line_no))
        else:
            result.append((package, license, copyleft, "N/A", "N/A", filename, line_no))

    return result
        
def extract_imports_from_code(code_blocks):
    """
    Extracts all imports from the given code along with Git user and commit hash.
    :param code_blocks: Tuples of code blocks and their filenames
    :return: A list of imports with associated Git information.
    """
    imports = set()
    for code, filename in code_blocks:
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        import_name = (
                            alias.name.split(".")[0] if "." in alias.name else alias.name
                        )
                        line_number = node.lineno
                        #commit_hash, author_email = git_blame_info(filename, line_number)
                        imports.add((import_name, filename, line_number)) #Formerly also commit_hash, author_email in pos [1,2]
                elif isinstance(node, ast.ImportFrom):
                    module = node.module
                    for alias in node.names:
                        if alias.name != "*" and module: # and module
                            import_name = (
                                module.split(".")[0] if "." in module else module
                            )
                            line_number = node.lineno
                            #commit_hash, author_email = git_blame_info(filename, line_number)
                            imports.add((import_name, filename, line_number)) #Formerly also commit_hash, author_email in pos [1,2]

        except SyntaxError as e:
            # TODO: Print the File where the Error occurred (Optional)
            print(f"Invalid Python Code, found {type(e).__name__}")
    init_local_cache(directory_to_search_in)
    uncached_imports = check_cache(list(imports), directory_to_search_in)
    return uncached_imports

def is_standard_lib(module_name):
    """
    Takes a module name and checks if it is a standard Python module.
    Module names should be as they appear in import statements:
    e.g. "random" instead of "random2" (what appears on PyPi)

    :module_name: The name of the module in question (str)
    :return: boolean checking if the module is in the system list of python names
    """
    if module_name in sys.builtin_module_names:
        return True
    
    try:
        # Get list of standard library modules for the current Python major and minor version
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        std_lib_modules = stdlib_list(python_version)
    except ValueError:
        print(f"Standard library list not found for Python {python_version}.")
        return False
    
    # Check if the module is in the list of standard library modules
    return module_name in std_lib_modules

def beautify_license(license_name):
    """
    Turns the name of a license like "Python Software Foundation License" to "PSF License"
    Assumes that all names longer than 2 words are formatted as above.

    :license_name: A string containing the full name of PyPi collections info.
    :returns: The formatted license name (str)
    """
    tokens = license_name.split(" ")
    if len(tokens) > 2:
        new = tokens[-1]
        tokens.pop()
        abbreviation = ''.join([word[0] for word in tokens])
        license_name = abbreviation + " " + new
    return license_name



def get_license_locally(package_name, copyleft_licenses):
    """
    Attempts to dynamically import a module from a string and obtain its licensing information from local metadata.
    :package_name: The name of an installed library (str)
    :copyleft_licenses: A list of copyleft licenses
    :returns: A tuple of package name, license, and true or false if the license is in the list of licenses (none if no license)
    """
    
    # Dynamically import the module
    try:
        importlib.import_module(package_name)
    except Exception as e:
        print(f"Could not dynamically import module '{package_name}'. Error: {e}")
        return (package_name, "Package information not available", "N/A")

    try:
        # Use importlib.metadata to get distribution info
        dist = importlib.metadata.distribution(package_name)
    except importlib.metadata.PackageNotFoundError:
        print(f"Could not get distribution of package '{package_name}' from local metadata.")
        return (package_name, "Package information not available", "N/A")
    except Exception as e:
        print(f"An error occurred while fetching distribution information for '{package_name}'. Error: {e}")
        return (package_name, "Package information not available", "N/A")

    # Extract license info from the metadata (if available)
    license = dist.metadata.get('License', 'License not found').strip()
    license = beautify_license(license)  # Assuming beautify_license is a function you've defined elsewhere

    is_copyleft = any(cpl_license in license for cpl_license in copyleft_licenses)

    return (package_name, license, is_copyleft)



def extract_code_blocks(directory):
    """
    Extracts all code blocks in the given directory.
    :param directory: The directory containing the notebooks and python files
    :return: A list of tuples (code block, filename)
    """
    blocks = []
    ipynb_glob_pattern = os.path.join(directory, "**", "*.ipynb")
    py_glob_pattern = os.path.join(directory, "**", "*.py")
    files = glob.glob(ipynb_glob_pattern, recursive=True) + glob.glob(
        py_glob_pattern, recursive=True
    )

    for file in files:
        with open(file, "r", encoding="utf-8") as code_file:
            code = code_file.read()
            if file.endswith(".ipynb"):
                notebook = nbformat.reads(code, as_version=4)
                for cell in notebook.cells:
                    if cell.cell_type == "code":
                        blocks.append((cell.source, file))
            elif file.endswith(".py"):
                blocks.append((code, file))

    return blocks

def extract_licenses(extracted_imports):
    """
    Extracts the license information for the given package names from the PyPI API
    :param package_names: A list of tuples containing package name and associated user info of each import
    :return: A list of tuples containing the package name, the license information, and a boolean indicating whether the
    """
    # This is probably not an exhaustive list of licenses and their abbreviations, but should cover all the common ones.
    copyleft_licenses = ["GPL", "AGPL", "LGPL", "MPL", "CDDL", "EPL", "FPL", "CPL", 
                         "APL", "CC", "EUPL", "FAL","D-FSL", "GMGPL", "FDL",
                         "IPL", "OSL", "RPSL", "RPL", "SSPL", "SPL"]
    unique_packages = set()
    package_info = {}
    result = []
    for entry in extracted_imports:
        package_name, *row_end = entry # Unpack import info
        if package_name not in unique_packages:
            unique_packages.add(package_name)
            try:
                if is_standard_lib(package_name):
                    package_info[package_name] = ("PSF License", False)
                else:
                    # NOTE: https://pypi.org returns sometimes a different License then a pip3 command, why?
                    response = requests.get(f"https://pypi.org/pypi/{package_name}/json")
                    response.raise_for_status()
                    data = response.json()
                    license_info = next((match for match in data['info']['classifiers'] if "license" in match.lower()), None)
                    if license_info is not None:
                        # TODO this occasionally fails when it shouldn't for some reason.
                        license = license_info.split(":")[-1].strip()
                        license = beautify_license(license)

                        # Check if any copyleft license from list is inside the result string
                        is_copyleft = any(cpl_license in license for cpl_license in copyleft_licenses)
                        package_info[package_name] = (license, is_copyleft)

                    else:
                        
                        print(f"Empty license info for <<{package_name}>> in PyPi")
                        try: 
                            local_result = get_license_locally(package_name, copyleft_licenses)
                            package_info[local_result[0]] = local_result[1:]
                        except:
                            package_info[package_name] = ("License not found", "N/A")
            except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError) as e: # 400 type error.
                print(f"Error finding <<{package_name}>> in PyPi (connection error). Attempting to import the module")
                try: 
                    local_result = get_license_locally(package_name, copyleft_licenses)
                    package_info[local_result[0]] = local_result[1:]

                except:
                    continue
            except requests.exceptions.RequestException as e:
                print(e)
                package_info[package_name] = ("Package information not available", "N/A")
            except KeyError:
                package_info[package_name] = ("License not found", "N/A")


        result.append((package_name,) + tuple(package_info[package_name]) + tuple(row_end))

    return result


def pretty_print(content, tablefmt="grid"):
    print(tabulate(content, tablefmt=tablefmt))


if __name__ == "__main__":
    directory_to_search_in = sys.argv[1] if len(sys.argv) > 1 else "./"
    code_blocks = extract_code_blocks(directory_to_search_in)
    extracted_imports = extract_imports_from_code(code_blocks)
    license_info = extract_licenses(extracted_imports)
    license_info = find_copyleft_and_git_blame(license_info)
    update_cache(license_info, directory_to_search_in)
    pretty_print(read_cache(directory_to_search_in))
    
